import devex.cli as cli
from devex.commands.pr.scripts import _journal
from devex.core import github


def _patch(monkeypatch, *, view_returns, create_returns_pr=42, captured=None):
    if captured is None:
        captured = {}
    captured.setdefault("posts", [])
    monkeypatch.setattr(github, "pr_view", lambda branch=None: view_returns)
    monkeypatch.setattr(github, "resolve_nick", lambda d: "devex-cli")

    def fake_create(title, body, draft):
        captured["title"] = title
        captured["body"] = body
        captured["draft"] = draft
        return create_returns_pr

    def fake_post(pr, body, in_reply_to):
        captured["posts"].append({"pr": pr, "body": body, "in_reply_to": in_reply_to})
        return 1000 + len(captured["posts"])

    monkeypatch.setattr(github, "pr_create", fake_create)
    monkeypatch.setattr(github, "pr_post_comment", fake_post)
    return captured


def test_pr_open_creates_pr_and_signs_body(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    captured = _patch(monkeypatch, view_returns=None)
    body_file = tmp_path / "body.md"
    body_file.write_text("Some PR body without signature.\n", encoding="utf-8")

    code = cli.main(
        [
            "pr",
            "open",
            "--agent",
            "claude-code",
            "--title",
            "feat: x",
            "--body-file",
            str(body_file),
        ]
    )
    out = capsys.readouterr()
    assert code == 0
    assert captured["title"] == "feat: x"
    assert "- devex-cli (Claude)" in captured["body"]
    assert captured["draft"] is False
    assert "PR opened" in out.out
    assert "#42" in out.out
    assert "devex pr read 42 --wait 180" in out.out


def test_pr_open_does_not_double_sign(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    captured = _patch(monkeypatch, view_returns=None)
    body_file = tmp_path / "body.md"
    body_file.write_text("Body.\n\n- devex-cli (Claude)\n", encoding="utf-8")

    cli.main(
        ["pr", "open", "--agent", "claude-code", "--title", "t", "--body-file", str(body_file)]
    )
    capsys.readouterr()
    assert captured["body"].count("- devex-cli (Claude)") == 1


def test_pr_open_idempotent_when_pr_already_exists(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    create_called = {"n": 0}
    monkeypatch.setattr(github, "pr_view", lambda branch=None: {"number": 7, "state": "OPEN"})
    monkeypatch.setattr(github, "resolve_nick", lambda d: "devex-cli")

    def fake_create(*args, **kwargs):
        create_called["n"] += 1
        return 999

    monkeypatch.setattr(github, "pr_create", fake_create)

    body_file = tmp_path / "body.md"
    body_file.write_text("body\n", encoding="utf-8")
    code = cli.main(
        ["pr", "open", "--agent", "claude-code", "--title", "t", "--body-file", str(body_file)]
    )
    out = capsys.readouterr()
    assert code == 0
    assert create_called["n"] == 0
    assert "already open" in out.out.lower()
    assert "devex pr read 7" in out.out


def test_pr_open_writes_journal_event(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _patch(monkeypatch, view_returns=None)
    body_file = tmp_path / "body.md"
    body_file.write_text("b\n", encoding="utf-8")
    cli.main(
        ["pr", "open", "--agent", "claude-code", "--title", "t", "--body-file", str(body_file)]
    )
    capsys.readouterr()
    events = _journal.load()
    types = [e["type"] for e in events]
    assert "pr_opened" in types
    opened = next(e for e in events if e["type"] == "pr_opened")
    assert opened["pr"] == 42
    assert opened["title"] == "t"


def test_pr_open_draft_flag(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    captured = _patch(monkeypatch, view_returns=None)
    body_file = tmp_path / "body.md"
    body_file.write_text("b\n", encoding="utf-8")
    cli.main(
        [
            "pr",
            "open",
            "--agent",
            "claude-code",
            "--title",
            "t",
            "--body-file",
            str(body_file),
            "--draft",
        ]
    )
    capsys.readouterr()
    assert captured["draft"] is True


def test_pr_open_auto_posts_agentic_review(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    captured = _patch(monkeypatch, view_returns=None)
    body_file = tmp_path / "body.md"
    body_file.write_text("b\n", encoding="utf-8")
    code = cli.main(
        ["pr", "open", "--agent", "claude-code", "--title", "t", "--body-file", str(body_file)]
    )
    out = capsys.readouterr()
    assert code == 0
    # Exactly one auto-posted trigger, top-level, with the non-deprecated command.
    assert captured["posts"] == [{"pr": 42, "body": "/agentic_review", "in_reply_to": None}]
    assert "/agentic_review" in out.out
    assert "/improve" not in out.out
    # Journal records the trigger alongside pr_opened.
    events = _journal.load()
    assert "pr_review_triggered" in [e["type"] for e in events]


def test_pr_open_draft_does_not_post_trigger(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    captured = _patch(monkeypatch, view_returns=None)
    body_file = tmp_path / "body.md"
    body_file.write_text("b\n", encoding="utf-8")
    cli.main(
        [
            "pr",
            "open",
            "--agent",
            "claude-code",
            "--title",
            "t",
            "--body-file",
            str(body_file),
            "--draft",
        ]
    )
    capsys.readouterr()
    assert captured["posts"] == []


def test_pr_open_already_open_does_not_post_trigger(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    posts: list = []
    monkeypatch.setattr(github, "pr_view", lambda branch=None: {"number": 7, "state": "OPEN"})
    monkeypatch.setattr(github, "resolve_nick", lambda d: "devex-cli")
    monkeypatch.setattr(github, "pr_create", lambda **kw: 999)
    monkeypatch.setattr(
        github, "pr_post_comment", lambda pr, body, in_reply_to: posts.append(body) or 1
    )
    body_file = tmp_path / "body.md"
    body_file.write_text("b\n", encoding="utf-8")
    cli.main(
        ["pr", "open", "--agent", "claude-code", "--title", "t", "--body-file", str(body_file)]
    )
    capsys.readouterr()
    assert posts == []


def test_pr_open_survives_trigger_post_failure(monkeypatch, tmp_path, capsys):
    # PR creation is the primary side effect; a failed trigger post must not
    # abort the command (which would tell the user to rerun `pr open` and skip
    # the trigger forever). Exit 0, PR reported open, and point at `pr review`.
    monkeypatch.chdir(tmp_path)
    _patch(monkeypatch, view_returns=None)

    def boom(pr, body, in_reply_to):
        raise RuntimeError("gh failed: network unreachable")

    monkeypatch.setattr(github, "pr_post_comment", boom)
    body_file = tmp_path / "body.md"
    body_file.write_text("b\n", encoding="utf-8")
    code = cli.main(
        ["pr", "open", "--agent", "claude-code", "--title", "t", "--body-file", str(body_file)]
    )
    out = capsys.readouterr()
    assert code == 0
    assert "PR opened" in out.out
    assert "#42" in out.out
    # Surfaces the recovery path without claiming the trigger was posted.
    assert "pr review 42" in out.out
    assert "Posted `/agentic_review`" not in out.out


def test_pr_open_with_delayed_read_chains(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _patch(monkeypatch, view_returns=None)
    # Stub the read path so it just returns a sentinel briefing.
    from devex.commands.pr.scripts import read as read_script

    monkeypatch.setattr(
        read_script,
        "run",
        lambda agent, project_dir, pr, wait: ("\n## Briefing-stub\n", 0, ""),
    )
    body_file = tmp_path / "body.md"
    body_file.write_text("b\n", encoding="utf-8")
    code = cli.main(
        [
            "pr",
            "open",
            "--agent",
            "claude-code",
            "--title",
            "t",
            "--body-file",
            str(body_file),
            "--delayed-read",
        ]
    )
    out = capsys.readouterr()
    assert code == 0
    assert "PR opened" in out.out
    assert "#42" in out.out
    assert "Briefing-stub" in out.out
