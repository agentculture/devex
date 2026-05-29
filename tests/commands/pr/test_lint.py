import devex.cli as cli
from devex.commands.pr.scripts import lint as lint_script


def _stub_git_changes(monkeypatch, files: list[tuple[str, str]]):
    """Stub `_collect_diff` to return the provided (path, content) tuples."""
    monkeypatch.setattr(lint_script, "_collect_diff", lambda: files)


def test_pr_lint_clean_emits_clean_message_and_open_hint(monkeypatch, capsys):
    _stub_git_changes(monkeypatch, [("src/foo.py", "print('hi')\n")])
    code = cli.main(["pr", "lint", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "no violations" in captured.out.lower()
    assert "devex pr open" in captured.out


def test_pr_lint_reports_violations(monkeypatch, capsys):
    _stub_git_changes(
        monkeypatch,
        [("docs/x.md", "see /home/spark/.claude/foo for details\n")],
    )
    code = cli.main(["pr", "lint", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "absolute-home-path" in captured.out
    assert "Fix the" in captured.out and "violation" in captured.out


def test_pr_lint_exit_on_violation_returns_nonzero(monkeypatch, capsys):
    _stub_git_changes(monkeypatch, [("docs/x.md", "/home/spark/x\n")])
    code = cli.main(["pr", "lint", "--agent", "claude-code", "--exit-on-violation"])
    capsys.readouterr()
    assert code == 1


def test_pr_lint_alignment_trigger_message(monkeypatch, capsys):
    _stub_git_changes(monkeypatch, [("CLAUDE.md", "fine content\n")])
    code = cli.main(["pr", "lint", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "alignment" in captured.out.lower()
    assert "devex pr delta" in captured.out
