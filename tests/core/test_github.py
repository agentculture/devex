import json
import subprocess
from pathlib import Path

import pytest
import yaml

from agent_experience.core import github


class _FakeCompleted:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_run_gh_returns_stdout(monkeypatch):
    captured = {}

    def fake_run(cmd, capture_output, text, check, env=None):
        captured["cmd"] = cmd
        return _FakeCompleted(stdout='{"foo":1}', returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = github._run_gh(["api", "/foo"])
    assert out == '{"foo":1}'
    assert captured["cmd"][:2] == ["gh", "api"]


def test_run_gh_raises_runtimeerror_on_failure(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(stderr="boom\nextra", returncode=1),
    )
    with pytest.raises(RuntimeError, match="gh failed: boom"):
        github._run_gh(["api", "/foo"])


def test_resolve_nick_from_culture_yaml(tmp_path):
    (tmp_path / "culture.yaml").write_text(
        yaml.safe_dump({"agents": [{"name": "a", "suffix": "my-nick"}]}), encoding="utf-8"
    )
    assert github.resolve_nick(tmp_path) == "my-nick"


def test_resolve_nick_falls_back_to_repo_basename(tmp_path):
    project = tmp_path / "agex-cli"
    project.mkdir()
    assert github.resolve_nick(project) == "agex-cli"


def test_resolve_nick_culture_yaml_without_suffix(tmp_path):
    project = tmp_path / "agex-cli"
    project.mkdir()
    (project / "culture.yaml").write_text(
        yaml.safe_dump({"agents": [{"name": "a"}]}), encoding="utf-8"
    )
    assert github.resolve_nick(project) == "agex-cli"


def test_pr_create_returns_number(monkeypatch):
    def fake_run(cmd, capture_output, text, check, env=None):
        return _FakeCompleted(stdout="https://github.com/owner/repo/pull/42\n", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert github.pr_create("title", "body", draft=False) == 42


def test_pr_create_with_draft_passes_flag(monkeypatch):
    captured = {}

    def fake_run(cmd, capture_output, text, check, env=None):
        captured["cmd"] = cmd
        return _FakeCompleted(stdout="https://github.com/o/r/pull/7\n", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    github.pr_create("t", "b", draft=True)
    assert "--draft" in captured["cmd"]


def test_pr_view_returns_dict(monkeypatch):
    import json

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(
            stdout=json.dumps({"number": 42, "state": "OPEN", "title": "foo"}),
            returncode=0,
        ),
    )
    out = github.pr_view("feat/branch")
    assert out["number"] == 42
    assert out["state"] == "OPEN"


def test_pr_view_returns_none_when_no_pr_for_branch(monkeypatch):
    def fake_run(cmd, capture_output, text, check, env=None):
        return _FakeCompleted(
            stderr='no pull requests found for branch "feat/x"\n',
            returncode=1,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert github.pr_view("feat/x") is None


def test_pr_checks_parses_json(monkeypatch):
    fixture = (
        Path(__file__).parent.parent / "commands" / "pr" / "fixtures" / "gh" / "pr_checks_42.json"
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(stdout=fixture.read_text(encoding="utf-8"), returncode=0),
    )
    checks = github.pr_checks(42)
    # Now: 2 CheckRun + 1 StatusContext = 3 normalized rows
    assert len(checks) == 3
    # Find the lint CheckRun
    lint = next(c for c in checks if c["name"] == "lint")
    assert lint["conclusion"] == "failure"
    # Find the StatusContext (SonarCloud)
    sonar = next(c for c in checks if c["name"] == "SonarCloud")
    assert sonar["conclusion"] == "failure"
    assert sonar["status"] == "completed"


def test_pr_comments_combines_three_sources(monkeypatch):
    fixture = json.loads(
        (
            Path(__file__).parent.parent
            / "commands"
            / "pr"
            / "fixtures"
            / "gh"
            / "pr_comments_42.json"
        ).read_text(encoding="utf-8")
    )

    def fake_run(cmd, capture_output, text, check, env=None):
        joined = " ".join(cmd)
        if "/pulls/42/comments" in joined:
            return _FakeCompleted(stdout=json.dumps(fixture["inline"]), returncode=0)
        if "/issues/42/comments" in joined:
            return _FakeCompleted(stdout=json.dumps(fixture["issue"]), returncode=0)
        if "/pulls/42/reviews" in joined:
            return _FakeCompleted(stdout=json.dumps(fixture["reviews"]), returncode=0)
        raise AssertionError(f"unexpected gh call: {cmd}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(github, "_repo_slug", lambda: "owner/repo")

    comments = github.pr_comments(42)
    types = {c["type"] for c in comments}
    assert types == {"inline", "top-level", "review"}
    assert len(comments) == 3


def test_pr_post_comment_top_level(monkeypatch):
    captured = {}

    def fake_run(cmd, capture_output, text, check, env=None):
        captured["cmd"] = cmd
        return _FakeCompleted(stdout=json.dumps({"id": 999}), returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(github, "_repo_slug", lambda: "owner/repo")

    new_id = github.pr_post_comment(pr=42, body="hi", in_reply_to=None)
    assert new_id == 999
    assert "issues/42/comments" in " ".join(captured["cmd"])


def test_pr_post_comment_reply_to_inline(monkeypatch):
    captured = {}

    def fake_run(cmd, capture_output, text, check, env=None):
        captured["cmd"] = cmd
        return _FakeCompleted(stdout=json.dumps({"id": 1000}), returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(github, "_repo_slug", lambda: "owner/repo")

    new_id = github.pr_post_comment(pr=42, body="reply", in_reply_to=100)
    assert new_id == 1000
    joined = " ".join(captured["cmd"])
    assert "pulls/42/comments" in joined
    assert "in_reply_to=100" in joined


def test_pr_resolve_thread_calls_graphql(monkeypatch):
    captured = {}

    def fake_run(cmd, capture_output, text, check, env=None):
        captured["cmd"] = cmd
        return _FakeCompleted(stdout="{}", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    github.pr_resolve_thread("THREAD_ID_123")
    joined = " ".join(captured["cmd"])
    assert "graphql" in joined
    assert "THREAD_ID_123" in joined
    assert "resolveReviewThread" in joined


def test_sonar_quality_gate_returns_dict(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(
            stdout=json.dumps({"projectStatus": {"status": "OK"}}),
            returncode=0,
        ),
    )
    out = github.sonar_quality_gate("owner_repo", pr=42)
    assert out == {"projectStatus": {"status": "OK"}}


def test_sonar_quality_gate_returns_none_on_404(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(stderr="HTTP 404\n", returncode=1),
    )
    assert github.sonar_quality_gate("missing_project", pr=42) is None


def test_sonar_new_issues_returns_list(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(
            stdout=json.dumps({"issues": [{"key": "i1"}, {"key": "i2"}]}),
            returncode=0,
        ),
    )
    out = github.sonar_new_issues("owner_repo", pr=42)
    assert [i["key"] for i in out] == ["i1", "i2"]


def test_sonar_new_issues_returns_empty_on_404(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(stderr="HTTP 404\n", returncode=1),
    )
    assert github.sonar_new_issues("missing_project", pr=42) == []


def test_sonar_quality_gate_skipped_on_transient_error(monkeypatch):
    """A non-404 gh failure (5xx, timeout, rate-limit) degrades to SKIPPED.

    Regression for steward#31: only 404 was caught, so any transient
    SonarCloud failure propagated and aborted pr read / pr await.
    """
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(stderr="HTTP 503 Service Unavailable\n", returncode=1),
    )
    assert github.sonar_quality_gate("owner_repo", pr=42) == github.SONAR_GATE_SKIPPED


def test_sonar_quality_gate_skipped_on_non_json(monkeypatch):
    """A 200 with a non-JSON body (e.g. an HTML error page) degrades to SKIPPED."""
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(stdout="<html>502 Bad Gateway</html>", returncode=0),
    )
    assert github.sonar_quality_gate("owner_repo", pr=42) == github.SONAR_GATE_SKIPPED


def test_sonar_new_issues_empty_on_transient_error(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(stderr="HTTP 503 Service Unavailable\n", returncode=1),
    )
    assert github.sonar_new_issues("owner_repo", pr=42) == []


def test_sonar_new_issues_empty_on_non_json(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(stdout="<html>502 Bad Gateway</html>", returncode=0),
    )
    assert github.sonar_new_issues("owner_repo", pr=42) == []


def test_sonar_gate_skipped_sentinel_is_immutable():
    """The shared SKIPPED sentinel is handed out by reference, so it must be
    immutable at both nesting levels — a mutating caller can't corrupt later
    calls/tests."""
    with pytest.raises(TypeError):
        github.SONAR_GATE_SKIPPED["projectStatus"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        github.SONAR_GATE_SKIPPED["projectStatus"]["status"] = "OK"  # type: ignore[index]
