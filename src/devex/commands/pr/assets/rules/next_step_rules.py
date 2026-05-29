"""Prioritized 'Next step:' rule keys for `devex pr` commands.

Each function takes the data the command already gathered and returns the
footer rule key + a context dict for variable substitution.  First match
wins.  Per-backend phrasing lives in `assets/backends/*.yaml`.
"""

from __future__ import annotations

from typing import Any


def lint_next_step(violations: list[Any], alignment_triggered: bool) -> tuple[str, dict[str, Any]]:
    if violations:
        return "lint_violations", {"violation_count": len(violations)}
    if alignment_triggered:
        return "lint_clean_with_alignment", {}
    return "lint_clean", {}


def open_next_step(pr: int, was_already_open: bool) -> tuple[str, dict[str, Any]]:
    key = "open_already_exists" if was_already_open else "open_recommend_read"
    return key, {"pr": pr}


def read_next_step(
    pr: int,
    threads_unresolved: int,
    has_recent_local_commits: bool,
    ci_red: bool,
) -> tuple[str, dict[str, Any]]:
    if ci_red:
        return "read_ci_red", {"pr": pr}
    if threads_unresolved > 0:
        if has_recent_local_commits:
            return "read_unresolved_after_commits", {"pr": pr}
        return "read_unresolved_no_commits", {"pr": pr}
    return "read_clean", {"pr": pr}


def read_wait_timeout_step(pr: int, reviewers: list[str]) -> tuple[str, dict[str, Any]]:
    return "read_wait_timeout", {"pr": pr, "reviewers": ", ".join(reviewers)}


def await_next_step(
    pr: int,
    gate_error: bool,
    threads_unresolved: int,
    ci_red: bool,
    gate_unknown: bool = False,
) -> tuple[str, dict[str, Any]]:
    if gate_error:
        return "await_gate_error", {"pr": pr}
    if gate_unknown:
        return "await_gate_unknown", {"pr": pr}
    if threads_unresolved > 0:
        return "await_unresolved_threads", {"pr": pr}
    if ci_red:
        return "await_ci_red", {"pr": pr}
    return "await_clean", {"pr": pr}


def await_wait_timeout_step(pr: int, reviewers: list[str]) -> tuple[str, dict[str, Any]]:
    return "await_wait_timeout", {"pr": pr, "reviewers": ", ".join(reviewers)}


def await_detach_step(pr: int) -> tuple[str, dict[str, Any]]:
    return "await_detached", {"pr": pr}


def await_check_step(state: str, pr: int, elapsed: int | None = None) -> tuple[str, dict[str, Any]]:
    """Footer for `pr await --check`, keyed by marker ``state``."""
    if state == "missing":
        return "await_check_missing", {"pr": pr}
    if state == "incompatible":
        return "await_check_incompatible", {"pr": pr}
    # Still polling.
    return "await_check_pending", {"pr": pr, "elapsed": "?" if elapsed is None else elapsed}


def reply_next_step(pr: int, failure_count: int) -> tuple[str, dict[str, Any]]:
    if failure_count > 0:
        return "reply_with_failures", {"pr": pr}
    return "reply_clean", {"pr": pr}


def review_next_step(pr: int) -> tuple[str, dict[str, Any]]:
    return "review_posted", {"pr": pr}


def delta_next_step() -> tuple[str, dict[str, Any]]:
    return "delta_done", {}
