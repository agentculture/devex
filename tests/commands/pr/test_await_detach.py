"""Tests for `devex pr await --detach` / `--check` (issue #64).

All in-process — the detached subprocess is never actually forked (the spawn
seam `_detach._spawn_detached` is monkeypatched; the worker body is exercised by
calling `_await_worker._run_worker` directly). Keeps the suite deterministic and
coverable on every OS, including Windows.
"""

import sys
from datetime import datetime, timezone

import pytest

import devex.cli as cli
from devex.commands.pr.scripts import _await_worker, _detach, _journal
from devex.commands.pr.scripts import await_ as await_script
from devex.core import github


def _setup(
    monkeypatch,
    *,
    comments=None,
    checks=None,
    sonar_gate=None,
    review_threads=None,
):
    """Stub every `gh`/Sonar read and neutralize the poll sleep."""
    monkeypatch.setattr(
        github,
        "pr_view",
        lambda x: {
            "number": 42,
            "state": "OPEN",
            "title": "t",
            "url": "u",
            "headRefName": "h",
            "baseRefName": "main",
        },
    )
    monkeypatch.setattr(github, "pr_checks", lambda pr: checks or [])
    monkeypatch.setattr(github, "pr_comments", lambda pr: comments or [])
    monkeypatch.setattr(github, "sonar_quality_gate", lambda *a, **k: sonar_gate)
    monkeypatch.setattr(github, "sonar_new_issues", lambda *a, **k: [])
    monkeypatch.setattr(github, "sonar_hotspots", lambda *a, **k: [])
    monkeypatch.setattr(github, "pr_review_threads", lambda pr: review_threads or [])
    monkeypatch.setattr(github, "_repo_slug", lambda: "owner/repo")
    monkeypatch.setattr(await_script.time, "sleep", lambda s: None)


def _ready_comment(author="qodo[bot]", body="lgtm"):
    return {"type": "review", "id": 1, "body": body, "author": author}


# --- --detach (foreground) -------------------------------------------------


def test_detach_spawns_worker_writes_polling_marker_and_returns_immediately(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)
    captured_spawn = {}

    def fake_spawn(argv, cwd, *, log_path):
        captured_spawn["argv"] = argv
        captured_spawn["cwd"] = cwd
        return 12345

    monkeypatch.setattr(_detach, "_spawn_detached", fake_spawn)
    # Prove the foreground never polls: any sleep is a bug.
    slept = []
    monkeypatch.setattr(await_script.time, "sleep", lambda s: slept.append(s))

    code = cli.main(["pr", "await", "42", "--detach", "--agent", "claude-code"])
    out = capsys.readouterr().out
    assert code == 0, out
    assert slept == [], "detach must not sleep in the foreground"

    # Polling marker written before returning.
    marker = _detach.read_marker(42)
    assert marker is not None
    assert marker["state"] == "polling"
    assert marker["pr"] == 42
    assert marker["max_wait"] == 1800
    assert marker["backend"] == "claude-code"
    assert marker["schema"] == _detach.MARKER_SCHEMA

    # Worker spawned via `python -m <worker>` with the resolved args.
    assert captured_spawn["argv"] == [
        sys.executable,
        "-m",
        "devex.commands.pr.scripts._await_worker",
        "42",
        "1800",
        "claude-code",
        "devex",
    ]
    assert captured_spawn["cwd"] == tmp_path

    # Footer points at --check; briefing surfaces the marker path.
    assert "--check" in out
    assert str(_detach.marker_path(42)) in out


def test_detach_spawn_failure_finalizes_marker_as_error(monkeypatch, tmp_path, capsys):
    """If the spawn raises, the polling marker must be finalized as error —
    never left stranded in 'polling' (Qodo #65 reliability finding)."""
    monkeypatch.chdir(tmp_path)

    def _boom(*a, **k):
        raise OSError("cannot fork")

    monkeypatch.setattr(_detach, "_spawn_detached", _boom)
    code = cli.main(["pr", "await", "42", "--detach", "--agent", "claude-code"])
    out = capsys.readouterr().out
    assert code == 1
    marker = _detach.read_marker(42)
    assert marker["state"] == "done"
    assert marker["outcome"] == "error"
    assert marker["exit_code"] == 1
    assert "cannot fork" in out
    assert any(e["type"] == "pr_await_detach_spawn_error" for e in _journal.load())

    # A follow-up --check now surfaces the error, not an eternal "still polling".
    code2 = cli.main(["pr", "await", "42", "--check", "--agent", "claude-code"])
    assert code2 == 1


def test_detach_resolves_pr_before_spawning(monkeypatch, tmp_path):
    """No PR (and none on the branch) → exit 2 before any spawn."""
    monkeypatch.chdir(tmp_path)

    def _boom(pr):
        raise ValueError("no PR found")

    monkeypatch.setattr(github, "resolve_pr_number", _boom)
    spawned = []
    monkeypatch.setattr(_detach, "_spawn_detached", lambda *a, **k: spawned.append(a))

    code = cli.main(["pr", "await", "--detach", "--agent", "claude-code"])
    assert code == 2
    assert spawned == []
    assert _detach.read_marker(42) is None


# --- worker ----------------------------------------------------------------


def test_worker_writes_done_marker_when_clean(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["devex"])  # restored after test
    _setup(
        monkeypatch,
        comments=[_ready_comment()],
        sonar_gate={"projectStatus": {"status": "OK"}},
    )
    code = _await_worker._run_worker(42, 0, "claude-code", "devex")
    assert code == 0
    marker = _detach.read_marker(42)
    assert marker["state"] == "done"
    assert marker["outcome"] == "clean"
    assert marker["exit_code"] == 0
    assert "PR #42" in marker["briefing"]
    assert any(e["type"] == "pr_await_detach_done" for e in _journal.load())


def test_worker_writes_done_marker_when_blocked(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["devex"])
    _setup(
        monkeypatch,
        comments=[_ready_comment()],
        sonar_gate={"projectStatus": {"status": "ERROR"}},
    )
    code = _await_worker._run_worker(42, 0, "claude-code", "devex")
    assert code == 1
    marker = _detach.read_marker(42)
    assert marker["state"] == "done"
    assert marker["outcome"] == "blocked"
    assert marker["exit_code"] == 1
    assert marker["gate_status"] == "ERROR"


def test_worker_writes_error_marker_on_gh_failure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["devex"])

    def _boom(*a, **k):
        raise RuntimeError("gh failed: boom")

    monkeypatch.setattr(github, "pr_view", _boom)
    code = _await_worker._run_worker(42, 0, "claude-code", "devex")
    assert code == 1
    marker = _detach.read_marker(42)
    assert marker["state"] == "done"
    assert marker["outcome"] == "error"
    assert marker["exit_code"] == 1
    assert "boom" in marker["briefing"]
    assert any(e["type"] == "pr_await_detach_error" for e in _journal.load())


# --- --check ---------------------------------------------------------------


def _write_done(pr, *, exit_code, briefing="BRIEFING-BODY", outcome="clean"):
    _detach.write_marker(
        pr,
        {
            "schema": _detach.MARKER_SCHEMA,
            "state": "done",
            "pr": pr,
            "exit_code": exit_code,
            "outcome": outcome,
            "briefing": briefing,
        },
    )


def test_check_done_clean_prints_briefing_exit_0(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _write_done(42, exit_code=0, briefing="STORED-CLEAN-BRIEFING")
    code = cli.main(["pr", "await", "42", "--check", "--agent", "claude-code"])
    out = capsys.readouterr().out
    assert code == 0
    assert "STORED-CLEAN-BRIEFING" in out


def test_check_done_blocked_exit_1(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _write_done(42, exit_code=1, briefing="STORED-BLOCKED", outcome="blocked")
    code = cli.main(["pr", "await", "42", "--check", "--agent", "claude-code"])
    out = capsys.readouterr().out
    assert code == 1
    assert "STORED-BLOCKED" in out


def test_check_polling_reports_still_polling_exit_0(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _detach.write_marker(
        42,
        {
            "schema": _detach.MARKER_SCHEMA,
            "state": "polling",
            "pr": 42,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "max_wait": 1800,
            "backend": "claude-code",
        },
    )
    code = cli.main(["pr", "await", "42", "--check", "--agent", "claude-code"])
    out = capsys.readouterr().out
    assert code == 0
    assert "still polling" in out.lower()


def test_check_missing_marker_exit_0(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["pr", "await", "42", "--check", "--agent", "claude-code"])
    out = capsys.readouterr().out
    assert code == 0
    assert "no detached await" in out.lower()


def test_check_incompatible_schema_exit_0(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _detach.write_marker(42, {"schema": 999, "state": "done", "pr": 42, "exit_code": 0})
    code = cli.main(["pr", "await", "42", "--check", "--agent", "claude-code"])
    out = capsys.readouterr().out
    assert code == 0
    assert "incompatible" in out.lower()


# --- marker I/O + flag parsing --------------------------------------------


def test_write_marker_is_atomic_and_roundtrips(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    payload = {"schema": _detach.MARKER_SCHEMA, "state": "done", "pr": 7, "exit_code": 0}
    _detach.write_marker(7, payload)
    assert _detach.read_marker(7) == payload
    # No temp file left behind.
    path = _detach.marker_path(7)
    assert not path.with_name(path.name + ".tmp").exists()


def test_read_marker_returns_none_on_corrupt(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    path = _detach.marker_path(7)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    assert _detach.read_marker(7) is None


def test_detach_and_check_are_mutually_exclusive(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        cli.main(["pr", "await", "42", "--detach", "--check", "--agent", "claude-code"])
    assert exc.value.code == 2
