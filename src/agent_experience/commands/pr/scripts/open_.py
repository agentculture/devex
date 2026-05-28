"""`agex pr open` — gh pr create with auto-signed body and idempotency."""

from __future__ import annotations

import sys
from importlib.resources import files
from pathlib import Path

from agent_experience.commands.pr.assets.rules.next_step_rules import open_next_step
from agent_experience.commands.pr.scripts import _journal, review
from agent_experience.commands.pr.scripts._footer import render_footer
from agent_experience.core import github
from agent_experience.core.backend import resolve_backend
from agent_experience.core.render import render_string

_TEMPLATES_PKG = "agent_experience.commands.pr.assets.templates"


def _read_body(body_file: Path | None) -> str:
    if body_file is None:
        return sys.stdin.read()
    return body_file.read_text(encoding="utf-8")


def _signed(body: str, nick: str) -> tuple[str, bool]:
    sig = f"- {nick} (Claude)"
    if sig in body:
        return body, True
    sep = "" if body.endswith("\n") else "\n"
    return f"{body}{sep}\n{sig}\n", True


def run(
    agent: str | None,
    project_dir: Path,
    title: str,
    body_file: Path | None,
    draft: bool,
    delayed_read: bool = False,
) -> tuple[str, int, str]:
    backend = resolve_backend(agent, project_dir)
    nick = github.resolve_nick(project_dir)

    existing = github.pr_view(None)
    if existing is not None and existing.get("state") == "OPEN":
        pr = int(existing["number"])
        url = existing.get("url", "")
        was_already_open = True
        signed = False
    else:
        body = _read_body(body_file)
        body, signed = _signed(body, nick)
        pr = github.pr_create(title=title, body=body, draft=draft)
        url = ""
        was_already_open = False
        _journal.append({"type": "pr_opened", "pr": pr, "title": title})

    # Auto-post the Qodo agentic-review trigger out of the box for a freshly
    # created, non-draft PR.  Skipped for drafts (not review-ready yet — use
    # `pr review` to trigger later) and for already-open PRs (idempotent
    # re-opens shouldn't spam the thread).
    #
    # The trigger post is best-effort: PR creation is the primary side effect
    # and has already succeeded, so a transient `gh` failure here must NOT abort
    # the command (which would tell the user to rerun `pr open`, only to skip
    # the trigger forever as an already-open PR).  On failure we keep exit 0 and
    # point the user at `pr review` to retry just the trigger.
    review_posted = False
    review_failed = False
    if not was_already_open and not draft:
        try:
            review.post_trigger(pr)
            review_posted = True
        except RuntimeError:
            review_failed = True

    footer_key, footer_ctx = open_next_step(pr, was_already_open)
    footer = render_footer(footer_key, backend, footer_ctx)

    template = files(_TEMPLATES_PKG).joinpath("pr_open_result.md.j2").read_text(encoding="utf-8")
    stdout = render_string(
        template,
        {
            "pr": pr,
            "url": url,
            "title": title,
            "signed": signed,
            "draft": draft,
            "was_already_open": was_already_open,
            "review_posted": review_posted,
            "review_failed": review_failed,
            "review_command": review.QODO_REVIEW_TRIGGER,
            "footer": footer,
        },
    )

    if delayed_read and not was_already_open:
        from agent_experience.commands.pr.scripts import read as read_script

        read_stdout, read_exit, _ = read_script.run(
            agent=agent, project_dir=project_dir, pr=pr, wait=180
        )
        return stdout + "\n" + read_stdout, read_exit, ""
    return stdout, 0, ""
