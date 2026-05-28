"""`agex pr await <PR>` — readiness + CI + Sonar gate combo verb.

Composes the same primitives as `pr read --wait` but adds gate semantics:
exits non-zero when the SonarCloud quality gate is ERROR or any inline
review thread is unresolved.  This is the "wake me when this is
triage-able" command — it's safe to chain after a push and rely on the
exit code to know whether the PR is ready for human merge.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any

from agent_experience.commands.pr.assets.rules.next_step_rules import (
    await_next_step,
    await_wait_timeout_step,
)
from agent_experience.commands.pr.scripts import _journal, _qodo, _readiness, _sonar
from agent_experience.commands.pr.scripts._footer import render_footer
from agent_experience.core import github
from agent_experience.core.backend import resolve_backend
from agent_experience.core.render import render_string

_TEMPLATES_PKG = "agent_experience.commands.pr.assets.templates"


def _gate_status(gate: Mapping[str, Any] | None) -> str | None:
    """Normalized SonarCloud quality-gate status, or None when there's no gate.

    ``None`` covers both an absent gate dict and an unregistered project (the
    github helper returns ``None`` on 404).  ``SKIPPED`` is the synthetic
    transient-failure sentinel and is treated as non-blocking by the caller.
    """
    if not gate:
        return None
    return gate.get("projectStatus", {}).get("status")


def run(
    agent: str | None,
    project_dir: Path,
    pr: int | None,
    max_wait: int,
) -> tuple[str, int, str]:
    backend = resolve_backend(agent, project_dir)
    pr_number = github.resolve_pr_number(pr)

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
                "waiting_for": waiting_for,
                "footer": footer,
            },
        )
        _journal.append(
            {
                "type": "pr_await",
                "pr": pr_number,
                "outcome": "timeout",
                "waited_secs": waited_secs,
            }
        )
        return stdout, 0, ""

    # Ready (or max_wait=0): run the full gate.
    project_key = _sonar.project_key()
    sonar_gate = github.sonar_quality_gate(project_key, pr_number)
    sonar_issues = github.sonar_new_issues(project_key, pr_number)

    threads_unresolved = _readiness.threads_unresolved(pr_number)
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
            "waiting_for": [],
            "footer": footer,
        },
    )

    exit_code = 1 if (gate_error or gate_unknown or threads_unresolved > 0 or ci_red) else 0
    _journal.append(
        {
            "type": "pr_await",
            "pr": pr_number,
            "outcome": "blocked" if exit_code else "clean",
            "gate_status": gate_status,
            "gate_error": gate_error,
            "threads_unresolved": threads_unresolved,
            "ci_state": "failure" if ci_red else "ok",
        }
    )
    return stdout, exit_code, ""
