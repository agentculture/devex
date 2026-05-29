"""Detached `devex pr await` worker (issue #64).

Run by `devex pr await <PR> --detach` as a background process:

    python -m devex.commands.pr.scripts._await_worker <pr> <max_wait> <backend> <prog>

It runs the same poll→gather→render→verdict logic as the foreground command,
then **atomically** writes the verdict to the await marker and exits.  It always
writes a marker — including on failure (e.g. `gh` unreachable) — so a later
`--check` reports the error instead of polling forever.

Operates in the current working directory (the spawner sets ``cwd`` to the
project dir; tests `monkeypatch.chdir` before calling `_run_worker`).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from devex.commands.pr.scripts import _detach, _journal, await_
from devex.core.backend import parse_backend


def _started_at_from_polling_marker(pr: int) -> str | None:
    marker = _detach.read_marker(pr)
    if marker and marker.get("state") == "polling":
        return marker.get("started_at")
    return None


def _run_worker(pr: int, max_wait: int, backend_value: str, prog: str) -> int:
    """Poll, gather, render, and write the done marker.  Returns the exit code.

    Never raises out: any failure is captured into an ``outcome:"error"`` marker
    (exit 1) so `--check` always has something deterministic to report.
    """
    # Make rendered footers follow the invoked name (`devex`/`agex`) rather than
    # the `python -m` argv this worker was spawned with.
    sys.argv[0] = prog
    started_at = _started_at_from_polling_marker(pr)
    backend = parse_backend(backend_value)

    try:
        ready, _waited, waiting_for = await_._poll_readiness(pr, max_wait)
        result = await_._gather_and_render(backend, pr, ready, waiting_for, max_wait)
        _detach.write_marker(
            pr,
            {
                "schema": _detach.MARKER_SCHEMA,
                "state": "done",
                "pr": pr,
                "exit_code": result.exit_code,
                "outcome": result.outcome,
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "briefing": result.stdout,
                "gate_status": result.gate_status,
                "threads_unresolved": result.threads_unresolved,
                "ci_state": result.ci_state,
            },
        )
        _journal.append(
            {
                "type": "pr_await_detach_done",
                "pr": pr,
                "outcome": result.outcome,
                "exit_code": result.exit_code,
            }
        )
        return result.exit_code
    except Exception as exc:  # noqa: BLE001 — must always leave a marker
        briefing = (
            f"# PR #{pr} — detached await failed\n\n"
            f"The background poller hit an error: `{exc}`\n\n"
            f"---\n**Next step:** rerun `{prog} pr await {pr} --detach` "
            "once the cause is resolved (e.g. network / `gh` reachable).\n"
        )
        _detach.write_marker(
            pr,
            {
                "schema": _detach.MARKER_SCHEMA,
                "state": "done",
                "pr": pr,
                "exit_code": 1,
                "outcome": "error",
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "briefing": briefing,
                "gate_status": None,
                "threads_unresolved": 0,
                "ci_state": "unknown",
            },
        )
        _journal.append({"type": "pr_await_detach_error", "pr": pr, "error": str(exc)})
        return 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    pr = int(args[0])
    max_wait = int(args[1])
    backend_value = args[2]
    prog = args[3]
    return _run_worker(pr, max_wait, backend_value, prog)


if __name__ == "__main__":
    sys.exit(main())
