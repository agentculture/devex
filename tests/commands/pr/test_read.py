from pathlib import Path

from typer.testing import CliRunner

from agent_experience.cli import app
from agent_experience.commands.pr.scripts import _journal
from agent_experience.core import github

runner = CliRunner()

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


def test_pr_read_one_shot_renders_briefing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _setup_clean(monkeypatch)
    result = runner.invoke(app, ["pr", "read", "42", "--agent", "claude-code"])
    assert result.exit_code == 0
    assert "PR #42" in result.stdout
    assert "Wait for human merge" in result.stdout


def test_pr_read_with_failing_check(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _setup_clean(
        monkeypatch,
        checks=[{"name": "test", "status": "completed", "conclusion": "failure"}],
    )
    result = runner.invoke(app, ["pr", "read", "42", "--agent", "claude-code"])
    assert "Fix CI" in result.stdout


def test_pr_read_with_comments_emits_table(monkeypatch, tmp_path):
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
    result = runner.invoke(app, ["pr", "read", "42", "--agent", "claude-code"])
    assert "src/foo.py:12" in result.stdout
    assert "qodo" in result.stdout


def test_pr_read_surfaces_qodo_findings(monkeypatch, tmp_path):
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
    result = runner.invoke(app, ["pr", "read", "42", "--agent", "claude-code"])
    assert result.exit_code == 0
    assert "## Qodo review" in result.stdout
    assert "Orphan honesty" in result.stdout
    assert "src/agent_experience/core/render.py:42-55" in result.stdout


def test_pr_read_flags_collapsed_qodo_when_no_findings(monkeypatch, tmp_path):
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
    result = runner.invoke(app, ["pr", "read", "42", "--agent", "claude-code"])
    assert result.exit_code == 0
    assert "⚠️" in result.stdout
    assert "3 finding(s) in collapsed Qodo review block" in result.stdout
    assert "expand on GitHub" in result.stdout


def test_pr_read_writes_journal_event(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _setup_clean(monkeypatch)
    runner.invoke(app, ["pr", "read", "42", "--agent", "claude-code"])
    events = _journal.load()
    assert any(e["type"] == "pr_read" and e["pr"] == 42 for e in events)


def test_pr_read_wait_returns_when_ready(monkeypatch, tmp_path):
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

    result = runner.invoke(app, ["pr", "read", "42", "--wait", "180", "--agent", "claude-code"])
    assert result.exit_code == 0
    assert "qodo" in result.stdout
    events = _journal.load()
    assert any(e["type"] == "readiness_arrived" for e in events)


def test_pr_read_wait_timeout_renders_still_waiting(monkeypatch, tmp_path):
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
    result = runner.invoke(app, ["pr", "read", "42", "--wait", "1", "--agent", "claude-code"])
    assert result.exit_code == 0
    assert "Still waiting" in result.stdout
    assert "Rerun `agex pr read 42 --wait 180`" in result.stdout


def test_sonar_project_key_env_override(monkeypatch, tmp_path):
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

    result = runner.invoke(app, ["pr", "read", "42", "--agent", "claude-code"])
    assert result.exit_code == 0
    assert seen["gate_key"] == "custom_override"
    assert seen["issues_key"] == "custom_override"


def test_pr_read_handles_gh_runtime_error(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def _raise_not_authenticated(x):
        raise RuntimeError("gh failed: not authenticated")

    monkeypatch.setattr(github, "pr_view", _raise_not_authenticated)
    result = runner.invoke(app, ["pr", "read", "42", "--agent", "claude-code"])
    assert result.exit_code == 1
    assert "not authenticated" in result.stderr
    assert "rerun" in result.stderr.lower()
