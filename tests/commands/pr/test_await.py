import agent_experience.cli as cli
from agent_experience.commands.pr.scripts import _journal
from agent_experience.core import github


def _setup(
    monkeypatch,
    *,
    comments=None,
    checks=None,
    sonar_gate=None,
    sonar_issues=None,
    review_threads=None,
):
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
    monkeypatch.setattr(github, "sonar_new_issues", lambda *a, **k: sonar_issues or [])
    monkeypatch.setattr(github, "pr_review_threads", lambda pr: review_threads or [])
    monkeypatch.setattr(github, "_repo_slug", lambda: "owner/repo")
    # Speed up the polling loop.
    from agent_experience.commands.pr.scripts import await_ as await_script

    monkeypatch.setattr(await_script.time, "sleep", lambda s: None)


def _ready_comment(author="qodo[bot]", body="lgtm", **overrides):
    base = {
        "type": "review",
        "id": 1,
        "body": body,
        "author": author,
    }
    base.update(overrides)
    return base


def test_await_exit_0_when_ready_and_clean(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup(
        monkeypatch,
        comments=[_ready_comment()],
        sonar_gate={"projectStatus": {"status": "OK"}},
    )
    code = cli.main(["pr", "await", "42", "--max-wait", "1", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0, captured.out + captured.err
    assert "ready" in captured.out.lower() or "wait for human merge" in captured.out.lower()
    events = _journal.load()
    assert any(e["type"] == "pr_await" and e.get("outcome") == "clean" for e in events)


def test_await_heartbeat_notes_satisfied_on_entry(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup(
        monkeypatch,
        comments=[_ready_comment()],  # ready on the very first poll
        sonar_gate={"projectStatus": {"status": "OK"}},
    )
    code = cli.main(["pr", "await", "42", "--max-wait", "240", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0, captured.out + captured.err
    assert "waited=0s" in captured.err
    assert "readiness already satisfied on entry" in captured.err


def test_await_exit_1_on_gate_error(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup(
        monkeypatch,
        comments=[_ready_comment()],
        sonar_gate={"projectStatus": {"status": "ERROR"}},
        sonar_issues=[
            {"severity": "MAJOR", "message": "Cognitive complexity", "component": "x.py", "line": 1}
        ],
    )
    code = cli.main(["pr", "await", "42", "--max-wait", "1", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 1
    assert "ERROR" in captured.out
    assert "SonarCloud quality gate" in captured.out
    events = _journal.load()
    assert any(
        e["type"] == "pr_await" and e.get("outcome") == "blocked" and e.get("gate_error") is True
        for e in events
    )


def test_await_exit_1_on_gate_unknown(monkeypatch, tmp_path, capsys):
    """A registered project reporting UNKNOWN must not be a false 'clean'.

    Regression for steward#33 bug 2: the gate matched only ERROR, so an
    UNKNOWN (analysis pending) gate passed and printed a clean readiness
    signal.  UNKNOWN now blocks with its own footer.
    """
    monkeypatch.chdir(tmp_path)
    _setup(
        monkeypatch,
        comments=[_ready_comment()],
        sonar_gate={"projectStatus": {"status": "UNKNOWN"}},
    )
    code = cli.main(["pr", "await", "42", "--max-wait", "1", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 1, captured.out + captured.err
    assert "UNKNOWN" in captured.out
    assert "analysis is pending" in captured.out
    events = _journal.load()
    assert any(
        e["type"] == "pr_await"
        and e.get("outcome") == "blocked"
        and e.get("gate_status") == "UNKNOWN"
        and e.get("gate_error") is False
        for e in events
    )


def test_await_skipped_gate_does_not_block(monkeypatch, tmp_path, capsys):
    """A transient SonarCloud failure (SKIPPED sentinel) must not flunk await.

    Regression for steward#31: a Sonar blip degrades to ``SONAR_GATE_SKIPPED``
    in core.github; the gate treats SKIPPED as non-blocking so await exits 0
    and still gates on threads/CI independently.
    """
    monkeypatch.chdir(tmp_path)
    _setup(
        monkeypatch,
        comments=[_ready_comment()],
        sonar_gate=github.SONAR_GATE_SKIPPED,
    )
    code = cli.main(["pr", "await", "42", "--max-wait", "1", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0, captured.out + captured.err
    events = _journal.load()
    assert any(
        e["type"] == "pr_await"
        and e.get("outcome") == "clean"
        and e.get("gate_status") == "SKIPPED"
        for e in events
    )


def test_await_exit_1_on_unresolved_threads(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup(
        monkeypatch,
        comments=[_ready_comment()],
        sonar_gate={"projectStatus": {"status": "OK"}},
        review_threads=[
            {"id": "T1", "isResolved": False},
            {"id": "T2", "isResolved": False},
            {"id": "T3", "isResolved": True},
        ],
    )
    code = cli.main(["pr", "await", "42", "--max-wait", "1", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 1
    assert "replies.jsonl" in captured.out


def test_await_resolved_threads_do_not_block(monkeypatch, tmp_path, capsys):
    """All review threads resolved → exit 0 even when raw inline comments remain.

    Regression for v0.1 heuristic that counted top-level inline comments
    instead of GraphQL ``isResolved`` state.
    """
    monkeypatch.chdir(tmp_path)
    _setup(
        monkeypatch,
        comments=[
            _ready_comment(),
            {
                "type": "inline",
                "id": 10,
                "body": "nit: rename foo",
                "author": "reviewer1",
                "path": "src/foo.py",
                "line": 12,
                "in_reply_to": None,
            },
        ],
        sonar_gate={"projectStatus": {"status": "OK"}},
        review_threads=[{"id": "T1", "isResolved": True}],
    )
    code = cli.main(["pr", "await", "42", "--max-wait", "1", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0, captured.out


def test_await_exit_1_on_ci_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup(
        monkeypatch,
        comments=[_ready_comment()],
        checks=[{"name": "test", "status": "completed", "conclusion": "failure"}],
        sonar_gate={"projectStatus": {"status": "OK"}},
    )
    code = cli.main(["pr", "await", "42", "--max-wait", "1", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 1
    assert "Fix CI" in captured.out
    events = _journal.load()
    assert any(
        e["type"] == "pr_await" and e.get("outcome") == "blocked" and e.get("ci_state") == "failure"
        for e in events
    )


def test_await_timeout_exits_0_with_still_waiting(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup(monkeypatch, comments=[])  # never ready
    code = cli.main(["pr", "await", "42", "--max-wait", "1", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Still waiting" in captured.out
    assert "Rerun `agex pr await 42`" in captured.out
    events = _journal.load()
    assert any(e["type"] == "pr_await" and e.get("outcome") == "timeout" for e in events)


def test_await_handles_gh_runtime_error(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    def _raise(x):
        raise RuntimeError("gh failed: not authenticated")

    monkeypatch.setattr(github, "pr_view", _raise)
    code = cli.main(["pr", "await", "42", "--max-wait", "0", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 1
    assert "not authenticated" in captured.err
