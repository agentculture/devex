from pathlib import Path

import agent_experience
import agent_experience.cli as cli
from agent_experience.commands.pr.scripts import _journal, review
from agent_experience.core import github


def test_package_never_emits_deprecated_improve_command():
    """Acceptance criterion: no code path posts the deprecated `/improve`.

    Scans shipped Python and template/asset files for `/improve` as a *posted*
    command — i.e. a quoted string literal or a Jinja/YAML value — guarding
    against a regression that reintroduces it. Prose that *names* `/improve`
    only to say it's deprecated (e.g. SKILL.md, the review.py docstring) is
    allowed; what's forbidden is emitting it as a value.
    """
    pkg_root = Path(agent_experience.__file__).parent
    forbidden = ('"/improve"', "'/improve'")
    offenders = []
    for p in pkg_root.rglob("*"):
        if not (p.is_file() and p.suffix in {".py", ".j2", ".yaml", ".yml"}):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if any(token in text for token in forbidden):
            offenders.append(p.relative_to(pkg_root))
    assert offenders == [], f"deprecated Qodo command `/improve` emitted in: {offenders}"


def _patch_post(monkeypatch, captured):
    def fake_post(pr, body, in_reply_to):
        captured.append({"pr": pr, "body": body, "in_reply_to": in_reply_to})
        return 1234

    monkeypatch.setattr(github, "pr_post_comment", fake_post)


def test_trigger_constant_is_agentic_review():
    # Single source of truth — the non-deprecated Qodo command.
    assert review.QODO_REVIEW_TRIGGER == "/agentic_review"


def test_pr_review_posts_agentic_review_on_explicit_pr(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    posts: list = []
    _patch_post(monkeypatch, posts)

    code = cli.main(["pr", "review", "42", "--agent", "claude-code"])
    out = capsys.readouterr()

    assert code == 0
    assert posts == [{"pr": 42, "body": "/agentic_review", "in_reply_to": None}]
    assert "/agentic_review" in out.out
    assert "/improve" not in out.out
    # Next-step footer present.
    assert "Next step:" in out.out
    assert "pr read 42" in out.out


def test_pr_review_resolves_current_branch_pr(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    posts: list = []
    _patch_post(monkeypatch, posts)
    monkeypatch.setattr(github, "pr_view", lambda branch=None: {"number": 7, "state": "OPEN"})

    code = cli.main(["pr", "review", "--agent", "claude-code"])
    capsys.readouterr()

    assert code == 0
    assert posts == [{"pr": 7, "body": "/agentic_review", "in_reply_to": None}]


def test_pr_review_errors_when_no_pr_for_branch(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    posts: list = []
    _patch_post(monkeypatch, posts)
    monkeypatch.setattr(github, "pr_view", lambda branch=None: None)

    code = cli.main(["pr", "review", "--agent", "claude-code"])
    err = capsys.readouterr().err

    assert code == 2
    assert "no PR found for current branch" in err
    assert posts == []


def test_pr_review_writes_journal_event(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _patch_post(monkeypatch, [])

    cli.main(["pr", "review", "99", "--agent", "claude-code"])
    capsys.readouterr()

    events = _journal.load()
    triggered = next(e for e in events if e["type"] == "pr_review_triggered")
    assert triggered["pr"] == 99
    assert triggered["command"] == "/agentic_review"
