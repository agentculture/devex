"""In-process coverage for the argparse dispatch behaviours added when the CLI
moved off Typer: the no-command help path, the bare sub-group help fallbacks,
and the CLI-level ValueError handling shared by every ``pr`` command.

These run through ``cli.main(argv)`` directly (not subprocess) so pytest-cov
observes the branches.
"""

import pytest

import agent_experience.cli as cli


def test_no_command_prints_usage_and_returns_2(capsys):
    """`agex` with no subcommand prints usage to stderr and returns 2."""
    code = cli.main([])
    captured = capsys.readouterr()
    assert code == 2
    assert "usage:" in captured.err.lower()


@pytest.mark.parametrize("group", ["pr", "hook"])
def test_bare_subgroup_prints_help_and_returns_2(group, capsys):
    """`agex pr` / `agex hook` with no subcommand falls back to group help (exit 2)."""
    code = cli.main([group])
    captured = capsys.readouterr()
    assert code == 2
    assert "usage:" in captured.err.lower()


# Every pr command resolves the backend before doing any work; a bad --agent
# therefore exercises the shared CLI-level `except ValueError` branch (exit 2,
# `agex:` prefix). resolve_backend runs before any stdin read, so no stdin is
# needed even for `open`/`reply`.
@pytest.mark.parametrize(
    "argv",
    [
        ["pr", "lint", "--agent", "gemini"],
        ["pr", "open", "--title", "t", "--agent", "gemini"],
        ["pr", "reply", "42", "--agent", "gemini"],
        ["pr", "read", "42", "--agent", "gemini"],
        ["pr", "await", "42", "--agent", "gemini"],
        ["pr", "delta", "--agent", "gemini"],
    ],
    ids=["lint", "open", "reply", "read", "await", "delta"],
)
def test_pr_command_bad_agent_reports_value_error(argv, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = cli.main(argv)
    captured = capsys.readouterr()
    assert code == 2
    assert captured.err.startswith("agex: ")
    assert "gemini" in captured.err


# Top-level backend commands resolve --agent via parse_backend; an invalid value
# exercises the shared `agex: error: <msg>` exit-2 branch.
@pytest.mark.parametrize(
    "argv",
    [
        ["learn", "--agent", "gemini"],
        ["gamify", "--agent", "gemini"],
        ["hook", "read", "--agent", "gemini"],
    ],
    ids=["learn", "gamify", "hook-read"],
)
def test_backend_command_bad_agent_reports_error(argv, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = cli.main(argv)
    captured = capsys.readouterr()
    assert code == 2
    assert captured.err.startswith("agex: error: ")
    assert "gemini" in captured.err


def test_error_prefix_follows_invoked_command_name(tmp_path, monkeypatch, capsys):
    """Invoked as `devex`, the error prefix is `devex: error: ` — the prefix is
    built from core.prog.prog_name(), not a hardcoded `agex`."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/devex"])
    code = cli.main(["learn", "--agent", "gemini"])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.err.startswith("devex: error: ")
