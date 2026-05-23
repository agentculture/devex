"""Thin wrapper around the `gh` CLI for the `agex pr` namespace.

Every call shells `gh ...` and parses JSON.  Hard failures raise
``RuntimeError`` with the gh stderr first line; soft failures
(missing SonarCloud project, missing PR for branch) return ``None``
or ``[]`` so renders still succeed.

The SonarCloud helpers go one step further: a *transient* failure
(timeout, 5xx, rate-limit, auth, or a non-JSON body) must not abort the
whole `pr read` / `pr await` — the gate fetch degrades to a ``SKIPPED``
sentinel (distinct from ``None`` "not registered") so the briefing can
say "couldn't evaluate" rather than crashing.

When the future zero-trust httpx swap lands, only this module changes.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml


def _run_gh(args: list[str]) -> str:
    """Shell out to `gh <args>` and return stdout.

    Raises RuntimeError(f"gh failed: {first_stderr_line}") on non-zero exit.
    """
    result = subprocess.run(  # nosec B603 - args are constructed from typed callers
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr_lines = (result.stderr or "").splitlines()
        first = stderr_lines[0] if stderr_lines else "no stderr"
        raise RuntimeError(f"gh failed: {first}")
    return result.stdout


_PR_URL_RE = re.compile(r"/pull/(\d+)")
_PR_VIEW_FIELDS = "number,state,title,url,headRefName,baseRefName,isDraft"


def resolve_nick(project_dir: Path) -> str:
    """Return the agent's nick: first agent's `suffix` in culture.yaml,
    or the project_dir basename if no usable nick is found.
    """
    culture = project_dir / "culture.yaml"
    if culture.exists():
        try:
            data = yaml.safe_load(culture.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
        agents = data.get("agents") or []
        if agents and isinstance(agents[0], dict):
            suffix = agents[0].get("suffix")
            if suffix:
                return str(suffix)
    return project_dir.name


def pr_create(title: str, body: str, draft: bool) -> int:
    """Create a PR via `gh pr create`; return the new PR number."""
    args = ["pr", "create", "--title", title, "--body", body]
    if draft:
        args.append("--draft")
    stdout = _run_gh(args)
    match = _PR_URL_RE.search(stdout)
    if not match:
        raise RuntimeError(f"gh pr create succeeded but URL not found in: {stdout!r}")
    return int(match.group(1))


def pr_view(pr_or_branch: str | None) -> dict[str, Any] | None:
    """Return the gh-pr-view dict, or None if no PR exists for the branch."""
    args = ["pr", "view", "--json", _PR_VIEW_FIELDS]
    if pr_or_branch is not None:
        args.insert(2, str(pr_or_branch))
    try:
        stdout = _run_gh(args)
    except RuntimeError as exc:
        if "no pull requests found" in str(exc):
            return None
        raise
    return json.loads(stdout)


def _repo_slug() -> str:
    """Return 'owner/repo' from `gh repo view --json owner,name`."""
    out = _run_gh(["repo", "view", "--json", "owner,name"])
    data = json.loads(out)
    return f"{data['owner']['login']}/{data['name']}"


def pr_checks(pr: int) -> list[dict[str, Any]]:
    """Return normalized [{name, status, conclusion, link}] for the PR.

    Uses `gh pr view --json statusCheckRollup` (works on gh >= 2.4) instead
    of `gh pr checks --json` (which requires gh >= 2.52).
    """
    out = _run_gh(["pr", "view", str(pr), "--json", "statusCheckRollup"])
    data = json.loads(out)
    rollup = data.get("statusCheckRollup") or []
    normalized: list[dict[str, Any]] = []
    for node in rollup:
        kind = node.get("__typename")
        if kind == "CheckRun":
            normalized.append(
                {
                    "name": node.get("name", ""),
                    "status": (node.get("status") or "").lower(),
                    "conclusion": (node.get("conclusion") or "").lower(),
                    "link": node.get("detailsUrl", ""),
                }
            )
        elif kind == "StatusContext":
            state = (node.get("state") or "").upper()
            conclusion = ""
            if state == "SUCCESS":
                conclusion = "success"
            elif state in ("FAILURE", "ERROR"):
                conclusion = "failure"
            normalized.append(
                {
                    "name": node.get("context", ""),
                    "status": "completed",
                    "conclusion": conclusion,
                    "link": node.get("targetUrl", ""),
                }
            )
    return normalized


def pr_comments(pr: int) -> list[dict[str, Any]]:
    """Aggregate inline review comments, top-level issue comments, and review
    summaries into a single list of normalised {type, body, author, ...} dicts.
    """
    slug = _repo_slug()
    inline_raw = json.loads(_run_gh(["api", f"repos/{slug}/pulls/{pr}/comments"]))
    issue_raw = json.loads(_run_gh(["api", f"repos/{slug}/issues/{pr}/comments"]))
    reviews_raw = json.loads(_run_gh(["api", f"repos/{slug}/pulls/{pr}/reviews"]))

    out: list[dict[str, Any]] = []
    for c in inline_raw:
        out.append(
            {
                "type": "inline",
                "id": c["id"],
                "body": c["body"],
                "author": c.get("user", {}).get("login", ""),
                "path": c.get("path"),
                "line": c.get("line"),
                "in_reply_to": c.get("in_reply_to_id"),
                "review_id": c.get("pull_request_review_id"),
                "created_at": c.get("created_at"),
            }
        )
    for c in issue_raw:
        out.append(
            {
                "type": "top-level",
                "id": c["id"],
                "body": c["body"],
                "author": c.get("user", {}).get("login", ""),
                "html_url": c.get("html_url"),
                "created_at": c.get("created_at"),
            }
        )
    for r in reviews_raw:
        if not r.get("body"):
            continue  # skip empty review summaries
        out.append(
            {
                "type": "review",
                "id": r["id"],
                "body": r["body"],
                "author": r.get("user", {}).get("login", ""),
                "state": r.get("state"),
                "created_at": r.get("submitted_at"),
            }
        )
    return out


_RESOLVE_THREAD_QUERY = (
    "mutation($threadId: ID!) { "
    "resolveReviewThread(input:{threadId:$threadId}) { thread { id } } "
    "}"
)


def pr_post_comment(pr: int, body: str, in_reply_to: int | None) -> int:
    """Post a comment on a PR; return the new comment ID.

    If in_reply_to is None, post a top-level issue comment.
    If in_reply_to is set, post an inline review comment replying to that comment ID.
    """
    slug = _repo_slug()
    if in_reply_to is None:
        args = ["api", f"repos/{slug}/issues/{pr}/comments", "-f", f"body={body}"]
    else:
        args = [
            "api",
            f"repos/{slug}/pulls/{pr}/comments",
            "-F",
            f"in_reply_to={in_reply_to}",
            "-f",
            f"body={body}",
        ]
    out = _run_gh(args)
    return int(json.loads(out)["id"])


def pr_resolve_thread(thread_id: str) -> None:
    """Resolve a review thread via GraphQL mutation."""
    _run_gh(
        [
            "api",
            "graphql",
            "-F",
            f"threadId={thread_id}",
            "-f",
            f"query={_RESOLVE_THREAD_QUERY}",
        ]
    )


_REVIEW_THREADS_QUERY = (
    "query($owner: String!, $repo: String!, $pr: Int!) { "
    "repository(owner:$owner, name:$repo) { "
    "pullRequest(number:$pr) { "
    "reviewThreads(first:100) { nodes { id isResolved } } "
    "} } }"
)


def pr_review_threads(pr: int) -> list[dict[str, Any]]:
    """Return all review threads on a PR with their resolution state.

    Each item: ``{"id": <node_id>, "isResolved": <bool>}``.  Empty list
    when the PR has no review threads.
    """
    owner, repo = _repo_slug().split("/", 1)
    out = _run_gh(
        [
            "api",
            "graphql",
            "-F",
            f"owner={owner}",
            "-F",
            f"repo={repo}",
            "-F",
            f"pr={pr}",
            "-f",
            f"query={_REVIEW_THREADS_QUERY}",
        ]
    )
    data = json.loads(out)
    nodes = (
        data.get("data", {})
        .get("repository", {})
        .get("pullRequest", {})
        .get("reviewThreads", {})
        .get("nodes", [])
    ) or []
    return [{"id": n["id"], "isResolved": bool(n.get("isResolved"))} for n in nodes]


_SONAR_HOST_ARGS = ["--hostname", "sonarcloud.io"]

# Synthetic gate returned when SonarCloud is reachable-but-unhappy (transient
# network/HTTP failure or a non-JSON body).  Distinct from ``None`` (404 / not
# registered) so the briefing and the `await` gate can tell "couldn't check"
# apart from "no project".  ``SKIPPED`` is treated as non-blocking by the gate.
# Immutable at both nesting levels: this single instance is handed out by
# reference, so a caller can never mutate the shared sentinel.
SONAR_GATE_SKIPPED: Mapping[str, Any] = MappingProxyType(
    {"projectStatus": MappingProxyType({"status": "SKIPPED"})}
)


def sonar_quality_gate(project_key: str, pr: int) -> Mapping[str, Any] | None:
    """Query SonarCloud for PR quality gate status.

    Returns ``None`` when the project is not registered (404).  On any other
    transient failure (timeout, 5xx, rate-limit, auth) or a non-JSON body,
    degrades to ``SONAR_GATE_SKIPPED`` instead of raising, so a SonarCloud blip
    never aborts `pr read` / `pr await`.
    """
    args = [
        "api",
        *_SONAR_HOST_ARGS,
        "-X",
        "GET",
        f"/api/qualitygates/project_status?projectKey={project_key}&pullRequest={pr}",
    ]
    try:
        out = _run_gh(args)
    except RuntimeError as exc:
        if "404" in str(exc):
            return None
        return SONAR_GATE_SKIPPED
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return SONAR_GATE_SKIPPED


def sonar_new_issues(project_key: str, pr: int) -> list[dict[str, Any]]:
    """Query SonarCloud for new issues in the PR.

    Returns ``[]`` when the project is not registered (404) and, defensively,
    on any other transient failure or non-JSON body — the issues list is
    enrichment, so an unreachable SonarCloud degrades to empty rather than
    aborting the briefing.
    """
    args = [
        "api",
        *_SONAR_HOST_ARGS,
        "-X",
        "GET",
        f"/api/issues/search?projects={project_key}&pullRequest={pr}&inNewCodePeriod=true",
    ]
    try:
        out = _run_gh(args)
    except RuntimeError:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    return list(data.get("issues", []))
