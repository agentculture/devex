import shutil
from pathlib import Path

import pytest

import devex.cli as cli

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
