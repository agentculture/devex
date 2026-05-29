"""Tests for `devex push` — push + conditional PR-readiness wait (t3).

`devex push` turns a push into continuous PR management:

* Always `git push` the current branch first (push-only — never stage/commit).
* If the current branch has an open PR → enter the same readiness wait a fresh
  PR gets and render the CI/Sonar/threads delta in ONE invocation, passing
  through the gate-aware exit code (non-zero on gate ERROR / unresolved
  threads), exactly like `pr await`.
* If there is no open PR → print a deterministic notice and exit 0 with NO wait.

Routing is deterministic on ``(current branch, PR-exists)`` only — no backend
auto-detection (the backend arrives via ``agent``) and no branch auto-detection.

These tests call ``push.run(...)`` directly (task t4 wires argparse).  The
per-backend ``assets/backends/<agent>.yaml`` files do not exist yet (task t5
authors them), so every assertion below relies on the graceful fallback
phrasing.
"""

from __future__ import annotations

import pytest

from devex.commands.push.scripts import push
from devex.core import github


def _patch_push(monkeypatch):
    """Record that ``git_push`` ran; return the call counter."""
    calls = {"push": 0}

    def fake_push():
        calls["push"] += 1

    monkeypatch.setattr(github, "git_push", fake_push)
    return calls


def _patch_await(monkeypatch, *, stdout="## delta\nCI green\n", exit_code=0):
    """Stub the reused `pr await` run so no real wait/network happens.

    Records the kwargs it was called with so tests can assert the wait value
    and that it ran at most once (single invocation, no second command).
    """
    from devex.commands.push.scripts import push as push_mod

    recorded = {"calls": []}

    def fake_run(*, agent, project_dir, pr, max_wait):
        recorded["calls"].append(
            {"agent": agent, "project_dir": project_dir, "pr": pr, "max_wait": max_wait}
        )
        return stdout, exit_code, ""

    monkeypatch.setattr(push_mod._await_script, "run", fake_run)
    return recorded


# --- Criterion 1: open PR → push then single wait+delta invocation ----------


def test_open_pr_pushes_then_waits_and_renders_delta_in_one_call(monkeypatch, tmp_path):
    calls = _patch_push(monkeypatch)
    monkeypatch.setattr(github, "current_branch_pr", lambda: 42)
    recorded = _patch_await(monkeypatch, stdout="## PR #42 delta\nCI green\n", exit_code=0)

    stdout, code, stderr = push.run("claude-code", project_dir=tmp_path)

    assert calls["push"] == 1
    # Exactly one reused-wait call — no second command.
    assert len(recorded["calls"]) == 1
    # The delta/briefing appears on stdout.
    assert "PR #42 delta" in stdout
    assert code == 0
    assert stderr == ""


def test_open_pr_wait_defaults_to_180(monkeypatch, tmp_path):
    _patch_push(monkeypatch)
    monkeypatch.setattr(github, "current_branch_pr", lambda: 7)
    recorded = _patch_await(monkeypatch)

    push.run("claude-code", project_dir=tmp_path)

    assert recorded["calls"][0]["max_wait"] == 180
    assert recorded["calls"][0]["pr"] == 7


def test_open_pr_wait_honours_explicit_max_wait(monkeypatch, tmp_path):
    _patch_push(monkeypatch)
    monkeypatch.setattr(github, "current_branch_pr", lambda: 7)
    recorded = _patch_await(monkeypatch)

    push.run("claude-code", max_wait=600, project_dir=tmp_path)

    assert recorded["calls"][0]["max_wait"] == 600


def test_push_runs_before_wait(monkeypatch, tmp_path):
    """git_push must complete before the readiness wait begins."""
    order: list[str] = []

    def fake_push():
        order.append("push")

    monkeypatch.setattr(github, "git_push", fake_push)
    monkeypatch.setattr(github, "current_branch_pr", lambda: 42)

    from devex.commands.push.scripts import push as push_mod

    def fake_run(*, agent, project_dir, pr, max_wait):
        order.append("await")
        return "delta", 0, ""

    monkeypatch.setattr(push_mod._await_script, "run", fake_run)

    push.run("claude-code", project_dir=tmp_path)

    assert order == ["push", "await"]


# --- Criterion 2: no PR → push then notice, exit 0, NO wait -----------------


def test_no_pr_pushes_then_prints_notice_and_exits_0(monkeypatch, tmp_path):
    calls = _patch_push(monkeypatch)
    monkeypatch.setattr(github, "current_branch_pr", lambda: None)
    # If the wait is ever entered this test must fail loudly.
    recorded = _patch_await(monkeypatch)

    stdout, code, stderr = push.run("claude-code", project_dir=tmp_path)

    assert calls["push"] == 1
    assert code == 0
    assert stderr == ""
    # Deterministic notice text.
    assert "no PR on this branch" in stdout
    assert "devex pr open" in stdout
    # NO wait occurred.
    assert recorded["calls"] == []


def test_no_pr_notice_uses_prog_name(monkeypatch, tmp_path):
    """The notice phrases the invoked-name via prog_name() (devex/agex).

    The notice is rendered through the shared renderer, which injects ``prog``
    from ``devex.core.prog.prog_name`` — so patching that seam (the one the
    renderer reads) flips the invoked name in the rendered output.
    """
    _patch_push(monkeypatch)
    monkeypatch.setattr(github, "current_branch_pr", lambda: None)
    _patch_await(monkeypatch)

    import devex.core.render as render_mod

    monkeypatch.setattr(render_mod, "prog_name", lambda: "agex")
    stdout, code, _ = push.run("claude-code", project_dir=tmp_path)

    assert code == 0
    assert "agex pr open" in stdout
    assert "devex pr open" not in stdout


# --- Criterion 3: deterministic routing on (branch, PR-exists) --------------


def test_routing_is_deterministic_open_pr(monkeypatch, tmp_path):
    """Same inputs (open PR) always select the managed path."""
    _patch_push(monkeypatch)
    monkeypatch.setattr(github, "current_branch_pr", lambda: 99)
    recorded = _patch_await(monkeypatch, stdout="DELTA-99", exit_code=0)

    for _ in range(3):
        stdout, code, _ = push.run("claude-code", project_dir=tmp_path)
        assert "DELTA-99" in stdout
        assert code == 0
    # Three invocations → exactly three waits, no extra commands.
    assert len(recorded["calls"]) == 3


def test_routing_is_deterministic_no_pr(monkeypatch, tmp_path):
    """Same inputs (no PR) always select the notice path, never the wait."""
    _patch_push(monkeypatch)
    monkeypatch.setattr(github, "current_branch_pr", lambda: None)
    recorded = _patch_await(monkeypatch)

    for _ in range(3):
        stdout, code, _ = push.run("claude-code", project_dir=tmp_path)
        assert "no PR on this branch" in stdout
        assert code == 0
    assert recorded["calls"] == []


# --- Criterion 4: managed-path exit code reflects the post-wait gate --------


def test_managed_path_passes_through_gate_error_exit_code(monkeypatch, tmp_path):
    """A non-zero gate-aware exit code from the reused wait is passed through."""
    _patch_push(monkeypatch)
    monkeypatch.setattr(github, "current_branch_pr", lambda: 42)
    _patch_await(monkeypatch, stdout="## gate ERROR\n", exit_code=1)

    stdout, code, _ = push.run("claude-code", project_dir=tmp_path)

    assert code == 1
    assert "gate ERROR" in stdout


def test_managed_path_passes_through_clean_exit_code(monkeypatch, tmp_path):
    _patch_push(monkeypatch)
    monkeypatch.setattr(github, "current_branch_pr", lambda: 42)
    _patch_await(monkeypatch, stdout="clean", exit_code=0)

    _, code, _ = push.run("claude-code", project_dir=tmp_path)
    assert code == 0


# --- Push failure surfaces as a non-zero exit / RuntimeError ----------------


def test_push_failure_propagates(monkeypatch, tmp_path):
    """A failed `git push` aborts before any PR detection or wait."""

    def boom():
        raise RuntimeError("git push failed: rejected (non-fast-forward)")

    monkeypatch.setattr(github, "git_push", boom)
    pr_calls = {"n": 0}
    monkeypatch.setattr(
        github, "current_branch_pr", lambda: pr_calls.__setitem__("n", pr_calls["n"] + 1) or 1
    )
    recorded = _patch_await(monkeypatch)

    with pytest.raises(RuntimeError, match="git push failed"):
        push.run("claude-code", project_dir=tmp_path)

    # PR detection and the wait never ran.
    assert pr_calls["n"] == 0
    assert recorded["calls"] == []


# --- Default project_dir resolves to cwd ------------------------------------


def test_default_project_dir_is_cwd(monkeypatch, tmp_path):
    """Omitting project_dir uses the current working directory."""
    _patch_push(monkeypatch)
    monkeypatch.setattr(github, "current_branch_pr", lambda: None)
    captured = {}

    from devex.commands.push.scripts import push as push_mod

    def fake_run(*, agent, project_dir, pr, max_wait):
        captured["project_dir"] = project_dir
        return "x", 0, ""

    # No PR path doesn't call await, so just verify cwd is used for the call we
    # can observe: route through the managed path instead.
    monkeypatch.setattr(github, "current_branch_pr", lambda: 5)
    monkeypatch.setattr(push_mod._await_script, "run", fake_run)
    monkeypatch.chdir(tmp_path)

    push.run("claude-code")

    assert captured["project_dir"] == tmp_path
