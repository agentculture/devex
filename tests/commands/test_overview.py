import shutil
from pathlib import Path

import pytest

import devex.cli as cli
from devex.commands.overview.scripts._footer import render_footer
from devex.commands.overview.scripts.next_step import overview_next_step
from devex.core.backend import Backend

FIXTURES = Path(__file__).parent.parent / "fixtures" / "claude-code"


def _copy_fixture(name: str, tmp_path: Path) -> Path:
    dest = tmp_path / "project"
    shutil.copytree(FIXTURES / name, dest)
    return dest


def test_overview_typical_project(tmp_path, monkeypatch, capsys):
    project = _copy_fixture("typical", tmp_path)
    monkeypatch.chdir(project)
    code = cli.main(["overview", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "# Overview — claude-code" in captured.out
    assert "example" in captured.out
    assert "CLAUDE.md" in captured.out
    assert "## Skills (1)" in captured.out


def test_overview_empty_project(tmp_path, monkeypatch, capsys):
    project = _copy_fixture("empty", tmp_path)
    monkeypatch.chdir(project)
    code = cli.main(["overview", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.count("_none_") == 3
    assert "no CLAUDE.md" in captured.out
    assert "## Skills (0)" in captured.out
    assert "## Hooks (0)" in captured.out
    assert "## MCP servers (0)" in captured.out


def test_overview_missing_agent_flag_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["overview"])
    captured = capsys.readouterr()
    assert excinfo.value.code != 0
    assert "agent" in (captured.err + captured.out).lower()


def test_overview_invalid_agent_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["overview", "--agent", "gemini"])
    captured = capsys.readouterr()
    assert code == 2
    assert "gemini" in captured.err


# --- Next step footer tests ---


def test_overview_next_step_returns_tuple():
    key, ctx = overview_next_step()
    assert isinstance(key, str)
    assert isinstance(ctx, dict)
    assert key == "overview_done"


def test_overview_footer_claude_code_contains_next_step():
    out = render_footer("overview_done", Backend.CLAUDE_CODE, {})
    assert "Next step" in out
    assert "devex" in out or "agex" in out


def test_overview_footer_includes_explain_or_learn():
    out = render_footer("overview_done", Backend.CLAUDE_CODE, {})
    # The hint should point to a concrete devex command
    assert "explain" in out or "learn" in out


def test_overview_footer_all_backends_define_hint():
    """Every backend must define the overview_done hint."""
    for backend in [Backend.CLAUDE_CODE, Backend.CODEX, Backend.COPILOT, Backend.ACP]:
        out = render_footer("overview_done", backend, {})
        assert "Next step" in out, f"backend {backend.value} missing Next step"


def test_overview_output_ends_with_footer(tmp_path, monkeypatch, capsys):
    project = _copy_fixture("typical", tmp_path)
    monkeypatch.chdir(project)
    code = cli.main(["overview", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "**Next step:**" in captured.out


def test_overview_footer_unknown_rule_raises():
    with pytest.raises(KeyError):
        render_footer("nonexistent_overview_rule", Backend.CLAUDE_CODE, {})
