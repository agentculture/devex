"""`devex pr await <PR>` — readiness + CI + Sonar gate combo verb.

Composes the same primitives as `pr read --wait` but adds gate semantics:
exits non-zero when the SonarCloud quality gate is ERROR or any inline
review thread is unresolved.  This is the "wake me when this is
triage-able" command — it's safe to chain after a push and rely on the
exit code to know whether the PR is ready for human merge.

``--detach`` / ``--check`` (issue #64) move the bounded poll out of the agent's
session: ``detach`` spawns a background worker that pays the wait and writes the
verdict to a marker; ``check`` reads that marker back without sleeping.  The
shared poll+gather+render core (`_poll_readiness` + `_gather_and_render`) is
called by the blocking `run`, by `check`'s nothing, and by the detached worker.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any

from devex.commands.pr.assets.rules.next_step_rules import (
    await_check_step,
    await_detach_step,
    await_next_step,
    await_wait_timeout_step,
)
from devex.commands.pr.scripts import _deploy, _detach, _journal, _qodo, _readiness, _sonar
from devex.commands.pr.scripts._footer import render_footer
from devex.core import github
from devex.core.backend import resolve_backend
from devex.core.prog import prog_name
from devex.core.render import render_string

_TEMPLATES_PKG = "devex.commands.pr.assets.templates"


@dataclass
class AwaitOutcome:
    """The result of one poll+gather+render pass, shared by every entrypoint."""

    stdout: str
    exit_code: int
    outcome: str  # "clean" | "blocked" | "timeout"
    gate_status: str | None
    gate_error: bool
    threads_unresolved: int
    ci_state: str  # "ok" | "failure"


def _gate_status(gate: Mapping[str, Any] | None) -> str | None:
    """Normalized SonarCloud quality-gate status, or None when there's no gate.

    ``None`` covers both an absent gate dict and an unregistered project (the
    github helper returns ``None`` on 404).  ``SKIPPED`` is the synthetic
    transient-failure sentinel and is treated as non-blocking by the caller.
    """
    if not gate:
        return None
    return gate.get("projectStatus", {}).get("status")


def _poll_readiness(pr_number: int, max_wait: int) -> tuple[bool, int, list[str]]:
    """Block up to ``max_wait`` seconds for required-reviewer readiness.

    Returns ``(ready, waited_secs, waiting_for)``.  Emits a heartbeat to stderr
    each poll and journals ``readiness_arrived`` the moment it flips ready.
    """
    waited_secs = 0
    waiting_for: list[str] = []
    ready = False
    if max_wait > 0:
        required = _readiness.required_reviewers()
        while waited_secs < max_wait:
            comments = github.pr_comments(pr_number)
            ready, waiting_for = _readiness.is_ready(comments, required)
            sys.stderr.write(
                _readiness.heartbeat("pr_await", pr_number, waited_secs, ready, waiting_for)
            )
            sys.stderr.flush()
            if ready:
                _journal.append(
                    {"type": "readiness_arrived", "pr": pr_number, "waited_secs": waited_secs}
                )
                break
            interval = min(_readiness.POLL_INTERVAL_SEC, max(1, max_wait - waited_secs))
            time.sleep(interval)
            waited_secs += interval
    return ready, waited_secs, waiting_for


def _gather_and_render(
    backend: Any,
    pr_number: int,
    ready: bool,
    waiting_for: list[str],
    max_wait: int,
) -> AwaitOutcome:
    """Fetch CI/comments/Sonar/threads, render the briefing, compute the verdict.

    Pure of journaling — each entrypoint (`run`, the detached worker) records
    its own story.  Footer phrasing follows ``prog_name()`` like every other
    `pr` command, so a detached worker that set ``sys.argv[0]`` renders the
    right invoked name.
    """
    template = files(_TEMPLATES_PKG).joinpath("pr_briefing.md.j2").read_text(encoding="utf-8")

    pr_meta = github.pr_view(str(pr_number))
    checks = github.pr_checks(pr_number)
    comments = github.pr_comments(pr_number)
    qodo = _qodo.parse(comments)

    if max_wait > 0 and not ready:
        # Timeout — render still-waiting briefing, exit 0 so the caller can rerun.
        footer_key, footer_ctx = await_wait_timeout_step(pr_number, waiting_for)
        footer = render_footer(footer_key, backend, footer_ctx)
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
        return AwaitOutcome(stdout, 0, "timeout", None, False, 0, "ok")

    # Ready (or max_wait=0): run the full gate.
    project_key = _sonar.project_key()
    sonar_gate = github.sonar_quality_gate(project_key, pr_number)
    sonar_issues = github.sonar_new_issues(project_key, pr_number)
    sonar_hotspots = github.sonar_hotspots(project_key, pr_number)
    deploy_preview = _deploy.preview_url(comments)

    threads_total, threads_resolved, threads_unresolved = _readiness.thread_tally(pr_number)
    ci_red = any(c.get("conclusion") == "failure" for c in checks)
    gate_status = _gate_status(sonar_gate)
    gate_error = gate_status == "ERROR"
    gate_unknown = gate_status == "UNKNOWN"

    footer_key, footer_ctx = await_next_step(
        pr=pr_number,
        gate_error=gate_error,
        gate_unknown=gate_unknown,
        threads_unresolved=threads_unresolved,
        ci_red=ci_red,
    )
    footer = render_footer(footer_key, backend, footer_ctx)

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

    exit_code = 1 if (gate_error or gate_unknown or threads_unresolved > 0 or ci_red) else 0
    return AwaitOutcome(
        stdout=stdout,
        exit_code=exit_code,
        outcome="blocked" if exit_code else "clean",
        gate_status=gate_status,
        gate_error=gate_error,
        threads_unresolved=threads_unresolved,
        ci_state="failure" if ci_red else "ok",
    )


def _journal_outcome(pr_number: int, result: AwaitOutcome, waited_secs: int) -> None:
    """Record the foreground `pr_await` journal event for a completed pass."""
    if result.outcome == "timeout":
        _journal.append(
            {
                "type": "pr_await",
                "pr": pr_number,
                "outcome": "timeout",
                "waited_secs": waited_secs,
            }
        )
        return
    _journal.append(
        {
            "type": "pr_await",
            "pr": pr_number,
            "outcome": result.outcome,
            "gate_status": result.gate_status,
            "gate_error": result.gate_error,
            "threads_unresolved": result.threads_unresolved,
            "ci_state": result.ci_state,
        }
    )


def run(
    agent: str | None,
    project_dir: Path,
    pr: int | None,
    max_wait: int,
) -> tuple[str, int, str]:
    backend = resolve_backend(agent, project_dir)
    pr_number = github.resolve_pr_number(pr)

    ready, waited_secs, waiting_for = _poll_readiness(pr_number, max_wait)
    result = _gather_and_render(backend, pr_number, ready, waiting_for, max_wait)
    _journal_outcome(pr_number, result, waited_secs)
    return result.stdout, result.exit_code, ""


def detach(
    agent: str | None,
    project_dir: Path,
    pr: int | None,
    max_wait: int,
) -> tuple[str, int, str]:
    """Spawn a detached poller and return immediately with the marker path.

    Writes a ``polling`` marker *before* spawning (so the marker is never
    clobbered by a fast-finishing worker), forks the worker, then renders the
    "detached" briefing.  No in-session sleep — exit 0 right away.
    """
    backend = resolve_backend(agent, project_dir)
    pr_number = github.resolve_pr_number(pr)  # fail fast (→ exit 2) before spawning

    started_at = datetime.now(timezone.utc).isoformat()
    _detach.write_marker(
        pr_number,
        {
            "schema": _detach.MARKER_SCHEMA,
            "state": "polling",
            "pr": pr_number,
            "started_at": started_at,
            "max_wait": max_wait,
            "backend": backend.value,
        },
    )
    _detach.spawn_worker(pr_number, max_wait, backend.value, prog_name(), project_dir)
    _journal.append({"type": "pr_await_detach_spawned", "pr": pr_number, "max_wait": max_wait})

    marker = _detach.marker_path(pr_number)
    footer_key, footer_ctx = await_detach_step(pr_number)
    footer = render_footer(footer_key, backend, footer_ctx)
    template = files(_TEMPLATES_PKG).joinpath("pr_await_detached.md.j2").read_text(encoding="utf-8")
    stdout = render_string(
        template,
        {
            "state": "started",
            "pr": pr_number,
            "marker": str(marker),
            "max_wait": max_wait,
            "elapsed": 0,
            "footer": footer,
        },
    )
    return stdout, 0, ""


def _elapsed_seconds(started_at: str | None) -> int | None:
    if not started_at:
        return None
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return None
    now = datetime.now(timezone.utc)
    return max(0, int((now - started).total_seconds()))


def check(
    agent: str | None,
    project_dir: Path,
    pr: int | None,
) -> tuple[str, int, str]:
    """Read the detached-await marker — no sleep, no re-poll.

    ``done`` → print the stored briefing + its stored exit code.  ``polling`` →
    a "still polling" notice (exit 0).  Missing / incompatible-schema → a clear
    notice (exit 0), never a crash or a false "clean".
    """
    backend = resolve_backend(agent, project_dir)
    pr_number = github.resolve_pr_number(pr)
    marker = _detach.read_marker(pr_number)

    template = files(_TEMPLATES_PKG).joinpath("pr_await_detached.md.j2").read_text(encoding="utf-8")

    if marker is None:
        footer_key, footer_ctx = await_check_step("missing", pr_number)
        footer = render_footer(footer_key, backend, footer_ctx)
        stdout = render_string(
            template,
            {
                "state": "missing",
                "pr": pr_number,
                "marker": str(_detach.marker_path(pr_number)),
                "max_wait": 0,
                "elapsed": 0,
                "footer": footer,
            },
        )
        return stdout, 0, ""

    if marker.get("schema") != _detach.MARKER_SCHEMA:
        footer_key, footer_ctx = await_check_step("incompatible", pr_number)
        footer = render_footer(footer_key, backend, footer_ctx)
        stdout = render_string(
            template,
            {
                "state": "incompatible",
                "pr": pr_number,
                "marker": str(_detach.marker_path(pr_number)),
                "max_wait": 0,
                "elapsed": 0,
                "footer": footer,
            },
        )
        return stdout, 0, ""

    if marker.get("state") == "done":
        # The stored briefing already carries its own rendered "Next step:".
        return marker.get("briefing", ""), int(marker.get("exit_code", 0)), ""

    # Still polling.
    elapsed = _elapsed_seconds(marker.get("started_at"))
    footer_key, footer_ctx = await_check_step("polling", pr_number, elapsed=elapsed)
    footer = render_footer(footer_key, backend, footer_ctx)
    stdout = render_string(
        template,
        {
            "state": "polling",
            "pr": pr_number,
            "marker": str(_detach.marker_path(pr_number)),
            "max_wait": marker.get("max_wait", 0),
            "elapsed": elapsed if elapsed is not None else "?",
            "footer": footer,
        },
    )
    return stdout, 0, ""
