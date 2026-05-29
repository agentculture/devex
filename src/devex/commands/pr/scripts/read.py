"""`devex pr read` — unified PR briefing.

v0.1: one-shot read.  Task 17 adds --wait + readiness loop.
"""

from __future__ import annotations

import subprocess
import sys
import time
from importlib.resources import files
from pathlib import Path
from typing import Any

from devex.commands.pr.assets.rules.next_step_rules import (
    read_next_step,
    read_wait_timeout_step,
)
from devex.commands.pr.scripts import _deploy, _journal, _qodo, _readiness, _sonar
from devex.commands.pr.scripts._footer import render_footer
from devex.core import github
from devex.core.backend import resolve_backend
from devex.core.render import render_string

_TEMPLATES_PKG = "devex.commands.pr.assets.templates"


def _has_recent_local_commits(journal_events: list[dict[str, Any]], pr: int) -> bool:
    """True if `git log` shows commits authored after the most recent
    `pr_read` event for this PR.  No event yet → False (first read)."""
    last_read = next(
        (e for e in reversed(journal_events) if e.get("type") == "pr_read" and e.get("pr") == pr),
        None,
    )
    if last_read is None:
        return False
    ts = last_read["ts"]
    out = subprocess.run(
        ["git", "log", f"--since={ts}", "--pretty=%H"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return bool(out)


def run(
    agent: str | None,
    project_dir: Path,
    pr: int | None,
    wait: int | None,
) -> tuple[str, int, str]:
    backend = resolve_backend(agent, project_dir)
    pr_number = github.resolve_pr_number(pr)

    waited_secs = 0
    waiting_for: list[str] = []
    if wait is not None and wait > 0:
        required = _readiness.required_reviewers()
        deadline = wait
        ready = False
        while waited_secs < deadline:
            comments = github.pr_comments(pr_number)
            ready, waiting_for = _readiness.is_ready(comments, required)
            sys.stderr.write(
                _readiness.heartbeat("pr_read --wait", pr_number, waited_secs, ready, waiting_for)
            )
            sys.stderr.flush()
            if ready:
                _journal.append(
                    {"type": "readiness_arrived", "pr": pr_number, "waited_secs": waited_secs}
                )
                break
            interval = min(_readiness.POLL_INTERVAL_SEC, max(1, deadline - waited_secs))
            time.sleep(interval)
            waited_secs += interval
        if not ready:
            # Timeout — render still-waiting briefing.
            pr_meta = github.pr_view(str(pr_number))
            checks = github.pr_checks(pr_number)
            comments = github.pr_comments(pr_number)
            qodo = _qodo.parse(comments)
            footer_key, footer_ctx = read_wait_timeout_step(pr_number, waiting_for)
            footer = render_footer(footer_key, backend, footer_ctx)
            template = (
                files(_TEMPLATES_PKG).joinpath("pr_briefing.md.j2").read_text(encoding="utf-8")
            )
            stdout = render_string(
                template,
                {
                    "pr": pr_number,
                    "pr_meta": pr_meta,
                    "checks": checks,
                    "comments": comments,
                    "qodo": qodo,
                    "sonar_gate": None,
                    "sonar_issues": [],
                    "sonar_hotspots": [],
                    "deploy_preview": _deploy.preview_url(comments),
                    "threads_total": 0,
                    "threads_resolved": 0,
                    "threads_unresolved": 0,
                    "waiting_for": waiting_for,
                    "footer": footer,
                },
            )
            return stdout, 0, ""

    # Either no --wait, or readiness arrived: full briefing path.
    pr_meta = github.pr_view(str(pr_number))
    checks = github.pr_checks(pr_number)
    comments = github.pr_comments(pr_number)
    qodo = _qodo.parse(comments)
    project_key = _sonar.project_key()
    sonar_gate = github.sonar_quality_gate(project_key, pr_number)
    sonar_issues = github.sonar_new_issues(project_key, pr_number)
    sonar_hotspots = github.sonar_hotspots(project_key, pr_number)
    deploy_preview = _deploy.preview_url(comments)

    threads_total, threads_resolved, threads_unresolved = _readiness.thread_tally(pr_number)
    journal_events = _journal.load()
    has_recent_commits = _has_recent_local_commits(journal_events, pr_number)
    ci_red = any(c.get("conclusion") == "failure" for c in checks)

    _journal.append(
        {
            "type": "pr_read",
            "pr": pr_number,
            "comment_count": len(comments),
            "threads_unresolved": threads_unresolved,
            "ci_state": "failure" if ci_red else "ok",
        }
    )

    footer_key, footer_ctx = read_next_step(
        pr=pr_number,
        threads_unresolved=threads_unresolved,
        has_recent_local_commits=has_recent_commits,
        ci_red=ci_red,
    )
    footer = render_footer(footer_key, backend, footer_ctx)

    template = files(_TEMPLATES_PKG).joinpath("pr_briefing.md.j2").read_text(encoding="utf-8")
    stdout = render_string(
        template,
        {
            "pr": pr_number,
            "pr_meta": pr_meta,
            "checks": checks,
            "comments": comments,
            "qodo": qodo,
            "sonar_gate": sonar_gate,
            "sonar_issues": sonar_issues,
            "sonar_hotspots": sonar_hotspots,
            "deploy_preview": deploy_preview,
            "threads_total": threads_total,
            "threads_resolved": threads_resolved,
            "threads_unresolved": threads_unresolved,
            "waiting_for": [],
            "footer": footer,
        },
    )
    return stdout, 0, ""
