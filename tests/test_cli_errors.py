"""Tests for unknown-command routing and CLI entry-point behaviour.

The first four tests use subprocess so that sys.argv manipulation inside
_main_entrypoint is exercised rather than bypassed; the remaining tests call
_main_entrypoint directly in-process to give the coverage tracker a chance to
observe the branch execution (subprocess children do not propagate the parent's
pytest-cov instrumentation).
"""

import argparse
import subprocess
import sys

import pytest

import agent_experience.cli as cli
from agent_experience.cli import _KNOWN_COMMANDS, _main_entrypoint


def test_unknown_command_emits_agex_page_and_exits_2(tmp_path):
    """An unknown subcommand prints agex explain agex to stdout and exits 2."""
    result = subprocess.run(
        [sys.executable, "-m", "agent_experience", "frobnicate"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert "agex" in result.stdout
    assert "overview" in result.stdout
    assert "unknown command" in result.stderr.lower()


def test_known_command_still_works(tmp_path):
    """A known command (explain agex) still routes correctly and exits 0."""
    result = subprocess.run(
        [sys.executable, "-m", "agent_experience", "explain", "agex"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert "agex" in result.stdout


def test_version_flag_still_works(tmp_path):
    """The --version flag bypasses the unknown-command handler and exits 0."""
    result = subprocess.run(
        [sys.executable, "-m", "agent_experience", "--version"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0
    # Version string is a non-empty line on stdout
    assert result.stdout.strip() != ""


def test_zero_args_shows_help(tmp_path):
    """Invoking agex with no arguments prints usage and exits 2.

    argparse has no built-in no-args-help behaviour, so main() prints the help
    to stderr and returns 2 — preserving the exit code Typer used (the standard
    Unix convention for "usage error: missing required argument"). We assert the
    exact code so a future regression that silently flips this to 0 is caught.
    """
    result = subprocess.run(
        [sys.executable, "-m", "agent_experience"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    combined = (result.stdout + result.stderr).lower()
    assert result.returncode == 2
    assert "usage:" in combined


# ---------------------------------------------------------------------------
# In-process tests for _main_entrypoint — the subprocess tests above exercise
# the real argv path end-to-end but do not propagate pytest-cov instrumentation
# into the child interpreter. Calling the function directly here lets coverage
# observe every branch of the router.
# ---------------------------------------------------------------------------


def test_main_entrypoint_unknown_command_exits_2(monkeypatch, capsys):
    """Direct invocation: unknown argv[0] triggers the sys.exit(2) branch."""
    monkeypatch.setattr(sys, "argv", ["agex", "frobnicate"])
    with pytest.raises(SystemExit) as excinfo:
        _main_entrypoint()
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "unknown command 'frobnicate'" in captured.err
    assert "overview" in captured.out  # body of agex explain agex


def _patch_fake_main(monkeypatch):
    """Replace cli.main with a recorder; _main_entrypoint wraps it in sys.exit()."""
    calls: list = []

    def fake_main(argv=None) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr("agent_experience.cli.main", fake_main)
    return calls


def test_main_entrypoint_known_command_falls_through(monkeypatch):
    """Direct invocation: known argv[0] falls through to main() unchanged."""
    calls = _patch_fake_main(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["agex", "explain", "agex"])
    with pytest.raises(SystemExit) as excinfo:
        _main_entrypoint()
    assert excinfo.value.code == 0
    assert len(calls) == 1


def test_main_entrypoint_flag_falls_through(monkeypatch):
    """Flag-led argv (e.g. --version) must bypass the unknown-command check."""
    calls = _patch_fake_main(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["agex", "--version"])
    with pytest.raises(SystemExit) as excinfo:
        _main_entrypoint()
    assert excinfo.value.code == 0
    assert len(calls) == 1


def test_main_entrypoint_zero_args_falls_through(monkeypatch):
    """Empty argv falls through to main() (which then handles no-args help)."""
    calls = _patch_fake_main(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["agex"])
    with pytest.raises(SystemExit) as excinfo:
        _main_entrypoint()
    assert excinfo.value.code == 0
    assert len(calls) == 1


def test_known_commands_set_matches_registered_commands():
    """Guard: _KNOWN_COMMANDS must stay in sync with the top-level subcommands
    registered on the argparse parser (per the maintenance comment in cli.py)."""
    parser = cli._build_parser()
    subparsers_actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(subparsers_actions) == 1
    registered = set(subparsers_actions[0].choices.keys())
    assert _KNOWN_COMMANDS == registered


def test_dunder_main_module_imports_cleanly():
    """Exercise agent_experience/__main__.py so its top-level imports and
    `if __name__ == '__main__'` guard are observed by the coverage tracker."""
    import importlib

    module = importlib.import_module("agent_experience.__main__")
    # The module must re-export the real entry point.
    assert module._main_entrypoint is _main_entrypoint
