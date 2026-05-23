from pathlib import Path

import agent_experience.cli as cli
from agent_experience.commands.pr.scripts import _journal
from agent_experience.core import github

_QODO_FIXTURE = Path(__file__).parent / "fixtures" / "gh" / "qodo_summary_comment.html"


def _setup_clean(monkeypatch, *, comments=None, checks=None):
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
    monkeypatch.setattr(github, "sonar_quality_gate", lambda *a, **k: None)
    monkeypatch.setattr(github, "sonar_new_issues", lambda *a, **k: [])
    monkeypatch.setattr(github, "pr_review_threads", lambda pr: [])
    # Avoid network round-trip in _project_key derivation:
    monkeypatch.setattr(github, "_repo_slug", lambda: "owner/repo")


def test_pr_read_one_shot_renders_briefing(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup_clean(monkeypatch)
    code = cli.main(["pr", "read", "42", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "PR #42" in captured.out
    assert "Wait for human merge" in captured.out


def test_pr_read_renders_skipped_gate_on_transient_failure(monkeypatch, tmp_path, capsys):
    """A transient SonarCloud failure surfaces as SKIPPED, not a crash.

    Regression for steward#31: read shares the Sonar fetch with await, so the
    ``SONAR_GATE_SKIPPED`` sentinel must render a clear notice and read must
    still exit 0.
    """
    monkeypatch.chdir(tmp_path)
    _setup_clean(monkeypatch)
    monkeypatch.setattr(github, "sonar_quality_gate", lambda *a, **k: github.SONAR_GATE_SKIPPED)
    code = cli.main(["pr", "read", "42", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0, captured.out + captured.err
    assert "SKIPPED" in captured.out
    assert "SonarCloud unreachable" in captured.out


def test_pr_read_with_failing_check(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup_clean(
        monkeypatch,
        checks=[{"name": "test", "status": "completed", "conclusion": "failure"}],
    )
    cli.main(["pr", "read", "42", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert "Fix CI" in captured.out


def test_pr_read_with_comments_emits_table(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup_clean(
        monkeypatch,
        comments=[
            {
                "type": "inline",
                "id": 1,
                "body": "nit: rename",
                "author": "qodo[bot]",
                "path": "src/foo.py",
                "line": 12,
            }
        ],
    )
    cli.main(["pr", "read", "42", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert "src/foo.py:12" in captured.out
    assert "qodo" in captured.out


def test_pr_read_surfaces_qodo_findings(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup_clean(
        monkeypatch,
        comments=[
            {
                "type": "top-level",
                "id": 7,
                "author": "qodo-code-review[bot]",
                "html_url": "https://github.com/owner/repo/pull/42#issuecomment-7",
                "body": _QODO_FIXTURE.read_text(encoding="utf-8"),
            }
        ],
    )
    code = cli.main(["pr", "read", "42", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "## Qodo review" in captured.out
    assert "Orphan honesty" in captured.out
    assert "src/agent_experience/core/render.py:42-55" in captured.out


def test_pr_read_flags_collapsed_qodo_when_no_findings(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    body = (
        "<h3>Code Review by Qodo</h3>\n"
        "<code>🐞 Bugs (3)</code>  <code>📘 Rule violations (0)</code>  "
        "<code>📎 Requirement gaps (0)</code>\n"
    )
    _setup_clean(
        monkeypatch,
        comments=[
            {
                "type": "top-level",
                "id": 7,
                "author": "qodo-code-review[bot]",
                "html_url": "https://github.com/owner/repo/pull/42#issuecomment-7",
                "body": body,
            }
        ],
    )
    code = cli.main(["pr", "read", "42", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "⚠️" in captured.out
    assert "3 finding(s) in collapsed Qodo review block" in captured.out
    assert "expand on GitHub" in captured.out


def test_pr_read_writes_journal_event(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _setup_clean(monkeypatch)
    cli.main(["pr", "read", "42", "--agent", "claude-code"])
    capsys.readouterr()
    events = _journal.load()
    assert any(e["type"] == "pr_read" and e["pr"] == 42 for e in events)


def test_pr_read_wait_returns_when_ready(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    state = {"calls": 0}

    def comments_call(pr):
        state["calls"] += 1
        if state["calls"] >= 3:
            return [
                {
                    "type": "inline",
                    "id": 1,
                    "body": "nit",
                    "author": "qodo[bot]",
                    "path": "x.py",
                    "line": 1,
                }
            ]
        return []

    monkeypatch.setattr(
        github,
        "pr_view",
        lambda x: {
            "number": 42,
            "state": "OPEN",
            "title": "t",
            "url": "",
            "headRefName": "h",
            "baseRefName": "main",
        },
    )
    monkeypatch.setattr(github, "pr_checks", lambda pr: [])
    monkeypatch.setattr(github, "pr_comments", comments_call)
    monkeypatch.setattr(github, "sonar_quality_gate", lambda *a, **k: None)
    monkeypatch.setattr(github, "sonar_new_issues", lambda *a, **k: [])
    monkeypatch.setattr(github, "pr_review_threads", lambda pr: [])
    monkeypatch.setattr(github, "_repo_slug", lambda: "owner/repo")

    # Speed up the loop's sleep.
    from agent_experience.commands.pr.scripts import read as read_script

    monkeypatch.setattr(read_script.time, "sleep", lambda s: None)

    code = cli.main(["pr", "read", "42", "--wait", "180", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "qodo" in captured.out
    events = _journal.load()
    assert any(e["type"] == "readiness_arrived" for e in events)


def test_pr_read_wait_satisfied_on_entry(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        github,
        "pr_view",
        lambda x: {
            "number": 42,
            "state": "OPEN",
            "title": "t",
            "url": "",
            "headRefName": "h",
            "baseRefName": "main",
        },
    )
    monkeypatch.setattr(github, "pr_checks", lambda pr: [])
    # Required reviewer feedback is already present on the very first poll.
    monkeypatch.setattr(
        github,
        "pr_comments",
        lambda pr: [
            {
                "type": "inline",
                "id": 1,
                "body": "nit",
                "author": "qodo[bot]",
                "path": "x.py",
                "line": 1,
            }
        ],
    )
    monkeypatch.setattr(github, "sonar_quality_gate", lambda *a, **k: None)
    monkeypatch.setattr(github, "sonar_new_issues", lambda *a, **k: [])
    monkeypatch.setattr(github, "pr_review_threads", lambda pr: [])
    monkeypatch.setattr(github, "_repo_slug", lambda: "owner/repo")

    def _fail_sleep(s):  # never reached: short-circuits at waited=0s
        raise AssertionError("should not sleep when ready on entry")

    from agent_experience.commands.pr.scripts import read as read_script

    monkeypatch.setattr(read_script.time, "sleep", _fail_sleep)

    code = cli.main(["pr", "read", "42", "--wait", "240", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "waited=0s" in captured.err
    assert "readiness already satisfied on entry" in captured.err


def test_pr_read_wait_timeout_renders_still_waiting(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        github,
        "pr_view",
        lambda x: {
            "number": 42,
            "state": "OPEN",
            "title": "t",
            "url": "",
            "headRefName": "h",
            "baseRefName": "main",
        },
    )
    monkeypatch.setattr(github, "pr_checks", lambda pr: [])
    monkeypatch.setattr(github, "pr_comments", lambda pr: [])  # never ready
    monkeypatch.setattr(github, "sonar_quality_gate", lambda *a, **k: None)
    monkeypatch.setattr(github, "sonar_new_issues", lambda *a, **k: [])
    monkeypatch.setattr(github, "pr_review_threads", lambda pr: [])
    monkeypatch.setattr(github, "_repo_slug", lambda: "owner/repo")
    from agent_experience.commands.pr.scripts import read as read_script

    monkeypatch.setattr(read_script.time, "sleep", lambda s: None)

    # --wait 1 with a short interval: one tick, then timeout.
    code = cli.main(["pr", "read", "42", "--wait", "1", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Still waiting" in captured.out
    assert "Rerun `agex pr read 42 --wait 180`" in captured.out


def test_sonar_project_key_env_override(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    seen: dict[str, str] = {}

    def _gate(key, pr):
        seen["gate_key"] = key
        return None

    def _issues(key, pr):
        seen["issues_key"] = key
        return []

    monkeypatch.setattr(
        github,
        "pr_view",
        lambda x: {
            "number": 42,
            "state": "OPEN",
            "title": "t",
            "url": "",
            "headRefName": "h",
            "baseRefName": "main",
        },
    )
    monkeypatch.setattr(github, "pr_checks", lambda pr: [])
    monkeypatch.setattr(github, "pr_comments", lambda pr: [])
    monkeypatch.setattr(github, "sonar_quality_gate", _gate)
    monkeypatch.setattr(github, "sonar_new_issues", _issues)
    monkeypatch.setattr(github, "pr_review_threads", lambda pr: [])
    # _repo_slug must NOT win when the env override is present.
    monkeypatch.setattr(github, "_repo_slug", lambda: "owner/repo")
    monkeypatch.setenv("SONAR_PROJECT_KEY", "custom_override")

    code = cli.main(["pr", "read", "42", "--agent", "claude-code"])
    assert code == 0
    assert seen["gate_key"] == "custom_override"
    assert seen["issues_key"] == "custom_override"


def test_pr_read_handles_gh_runtime_error(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    def _raise_not_authenticated(x):
        raise RuntimeError("gh failed: not authenticated")

    monkeypatch.setattr(github, "pr_view", _raise_not_authenticated)
    code = cli.main(["pr", "read", "42", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 1
    assert "not authenticated" in captured.err
    assert "rerun" in captured.err.lower()
