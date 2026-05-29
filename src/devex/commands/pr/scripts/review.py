"""`devex pr review` — post the Qodo agentic-review trigger comment.

Qodo's current command to start an agentic PR review is ``/agentic_review``.
The legacy ``/improve`` command is deprecated (Qodo emits a deprecation banner
when it is used), so devex never posts ``/improve``.  ``QODO_REVIEW_TRIGGER`` is
the single source of truth for the command string — any future Qodo rename is a
one-line change here, picked up by both this verb and the auto-post on
``pr open``.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from devex.commands.pr.assets.rules.next_step_rules import review_next_step
from devex.commands.pr.scripts import _journal
from devex.commands.pr.scripts._footer import render_footer
from devex.core import github
from devex.core.backend import resolve_backend
from devex.core.render import render_string

_TEMPLATES_PKG = "devex.commands.pr.assets.templates"

# The non-deprecated Qodo command to start an agentic code review. Single
# source of truth — referenced here and by the `pr open` auto-post.
QODO_REVIEW_TRIGGER = "/agentic_review"


def post_trigger(pr: int) -> int:
    """Post the Qodo review-trigger comment on ``pr``; return the comment ID.

    Also appends a ``pr_review_triggered`` journal event.  Shared by the
    ``pr review`` verb and the ``pr open`` auto-post.
    """
    comment_id = github.pr_post_comment(pr, QODO_REVIEW_TRIGGER, None)
    _journal.append({"type": "pr_review_triggered", "pr": pr, "command": QODO_REVIEW_TRIGGER})
    return comment_id


def run(agent: str | None, project_dir: Path, pr: int | None) -> tuple[str, int, str]:
    backend = resolve_backend(agent, project_dir)
    pr_number = github.resolve_pr_number(pr)

    post_trigger(pr_number)

    footer_key, footer_ctx = review_next_step(pr_number)
    footer = render_footer(footer_key, backend, footer_ctx)

    template = files(_TEMPLATES_PKG).joinpath("pr_review_result.md.j2").read_text(encoding="utf-8")
    stdout = render_string(
        template,
        {
            "pr": pr_number,
            "command": QODO_REVIEW_TRIGGER,
            "footer": footer,
        },
    )
    return stdout, 0, ""
