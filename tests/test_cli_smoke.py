import pytest

import devex.cli as cli
from devex import __version__


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_push_listed_in_top_level_help(capsys):
    """`devex --help` lists the `push` subcommand."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "push" in captured.out


def test_push_help_shows_max_wait_and_agent(capsys):
    """`devex push --help` shows --max-wait (default 180) and --agent."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["push", "--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "--max-wait" in captured.out
    assert "180" in captured.out
    assert "--agent" in captured.out
