"""`devex pr reply` — batch JSONL replies + thread resolution."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from devex.commands.pr.assets.rules.next_step_rules import reply_next_step
from devex.commands.pr.scripts import _journal
from devex.commands.pr.scripts._footer import render_footer
from devex.core import github
from devex.core.backend import resolve_backend
from devex.core.prog import prog_name
from devex.core.render import render_string

_TEMPLATES_PKG = "devex.commands.pr.assets.templates"


@dataclass
class _Failure:
    line: int
    reason: str
    entry: str


def _signed(body: str, nick: str) -> str:
    sig = f"- {nick} (Claude)"
    if sig in body:
        return body
    sep = "" if body.endswith("\n") else "\n"
    return f"{body}{sep}\n{sig}\n"


def _validate_entry(raw_line: str, lineno: int) -> tuple[dict | None, _Failure | None, bool]:
    """Parse and validate one JSONL line.

    Returns (entry, None, False) on success, or (None, failure, is_parse_error)
    on error.  The caller should break and record parse_error_line when
    is_parse_error is True.
    """
    try:
        entry = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        return None, _Failure(line=lineno, reason=f"JSONL parse error: {exc}", entry=raw_line), True
    if not isinstance(entry, dict) or not isinstance(entry.get("body"), str):
        return (
            None,
            _Failure(
                line=lineno,
                reason="missing or invalid 'body' field (must be string)",
                entry=raw_line,
            ),
            False,
        )
    return entry, None, False


def _post_entry(entry: dict, nick: str, pr: int) -> bool:
    """Post one reply + optional thread resolution; append journal events.

    Returns True if a thread was resolved (caller increments resolved count).
    Raises RuntimeError on gh failure — caller records the failure and stops.
    """
    body = _signed(entry["body"], nick)
    github.pr_post_comment(pr=pr, body=body, in_reply_to=entry.get("in_reply_to"))
    _journal.append(
        {
            "type": "pr_reply",
            "pr": pr,
            "thread_id": entry.get("thread_id"),
            "in_reply_to": entry.get("in_reply_to"),
        }
    )
    thread_id = entry.get("thread_id")
    if thread_id:
        github.pr_resolve_thread(thread_id)
        return True
    return False


def _process_line(
    raw_line: str, lineno: int, nick: str, pr: int
) -> tuple[int, int, _Failure | None, bool]:
    """Process one JSONL line. Returns (posted_delta, resolved_delta, failure, is_parse_error).

    Caller breaks the loop when failure is not None.
    """
    entry, failure, is_parse_error = _validate_entry(raw_line, lineno)
    if failure is not None:
        return 0, 0, failure, is_parse_error
    try:
        did_resolve = _post_entry(entry, nick, pr)  # type: ignore[arg-type]
    except RuntimeError as exc:
        return 0, 0, _Failure(line=lineno, reason=str(exc), entry=raw_line), False
    return 1, (1 if did_resolve else 0), None, False


def _stderr_for_failures(failures: list[_Failure], parse_error_line: int | None, pr: int) -> str:
    """Build the instructive stderr line for the failure case."""
    prog = prog_name()
    if parse_error_line is not None:
        return (
            f"{prog}: fix line {parse_error_line} (see stdout) and resubmit "
            f"lines {parse_error_line}..end to '{prog} pr reply {pr}'\n"
        )
    first_failed = failures[0].line
    return (
        f"{prog}: resubmit lines {first_failed}..end from the table above "
        f"to '{prog} pr reply {pr}'\n"
    )


def run(
    agent: str | None,
    project_dir: Path,
    pr: int,
) -> tuple[str, int, str]:
    backend = resolve_backend(agent, project_dir)
    nick = github.resolve_nick(project_dir)
    raw = sys.stdin.read()

    posted = 0
    resolved = 0
    failures: list[_Failure] = []
    parse_error_line: int | None = None

    for lineno, raw_line in enumerate(raw.splitlines(), start=1):
        if not raw_line.strip():
            continue
        dp, dr, failure, is_parse_error = _process_line(raw_line, lineno, nick, pr)
        posted += dp
        resolved += dr
        if failure is not None:
            if is_parse_error:
                parse_error_line = lineno
            failures.append(failure)
            break

    _journal.append({"type": "pr_batch_replied", "pr": pr, "count": posted, "resolved": resolved})

    footer_key, footer_ctx = reply_next_step(pr=pr, failure_count=len(failures))
    footer = render_footer(footer_key, backend, footer_ctx)

    template = files(_TEMPLATES_PKG).joinpath("pr_reply_result.md.j2").read_text(encoding="utf-8")
    stdout = render_string(
        template,
        {
            "pr": pr,
            "count": posted,
            "resolved": resolved,
            "failures": [f.__dict__ for f in failures],
            "footer": footer,
        },
    )
    if not failures:
        return stdout, 0, ""
    return stdout, 1, _stderr_for_failures(failures, parse_error_line, pr)
