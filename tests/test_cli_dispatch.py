"""In-process coverage for the argparse dispatch behaviours added when the CLI
moved off Typer: the no-command help path, the bare sub-group help fallbacks,
and the CLI-level ValueError handling shared by every ``pr`` command.

These run through ``cli.main(argv)`` directly (not subprocess) so pytest-cov
observes the branches.
"""

import pytest

import devex.cli as cli


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
    assert captured.err.startswith("devex: ")
    assert "gemini" in captured.err


# Top-level backend commands resolve --agent via parse_backend; an invalid value
# exercises the shared `devex: error: <msg>` exit-2 branch.
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
    assert captured.err.startswith("devex: error: ")
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


# ---------------------------------------------------------------------------
# push subcommand dispatch tests
# ---------------------------------------------------------------------------


def test_push_dispatches_to_push_script(tmp_path, monkeypatch):
    """`devex push --agent claude-code` calls push_script.run with correct args."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    with patch("devex.cli.push_script.run", return_value=("out\n", 0, "")) as mock_run:
        code = cli.main(["push", "--agent", "claude-code"])
    assert code == 0
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args
    assert call_kwargs.kwargs["agent"] == "claude-code"
    assert call_kwargs.kwargs["max_wait"] == 180
    assert call_kwargs.kwargs["project_dir"] == tmp_path


def test_push_default_max_wait_is_180(tmp_path, monkeypatch):
    """`--max-wait` defaults to 180 when not specified."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    with patch("devex.cli.push_script.run", return_value=("", 0, "")) as mock_run:
        cli.main(["push", "--agent", "claude-code"])
    assert mock_run.call_args.kwargs["max_wait"] == 180


def test_push_max_wait_override_is_threaded(tmp_path, monkeypatch):
    """`--max-wait 60` is threaded through to push_script.run."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    with patch("devex.cli.push_script.run", return_value=("", 0, "")) as mock_run:
        cli.main(["push", "--agent", "claude-code", "--max-wait", "60"])
    assert mock_run.call_args.kwargs["max_wait"] == 60


def test_push_runtime_error_maps_to_exit_1(tmp_path, monkeypatch, capsys):
    """`push_script.run` raising RuntimeError → exit 1, message on stderr."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    with patch("devex.cli.push_script.run", side_effect=RuntimeError("git push failed: rejected")):
        code = cli.main(["push", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 1
    assert "git push failed: rejected" in captured.err


def test_push_no_agent_uses_culture_yaml_fallback(tmp_path, monkeypatch):
    """`devex push` without --agent is accepted (resolves via culture.yaml fallback)."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    # Without --agent the parser passes agent=None; push_script.run handles
    # resolution internally via resolve_backend.  We mock run so the test
    # never touches the real git layer.
    with patch("devex.cli.push_script.run", return_value=("", 0, "")) as mock_run:
        code = cli.main(["push"])
    assert code == 0
    assert mock_run.call_args.kwargs["agent"] is None


def test_push_runs_non_interactively(tmp_path, monkeypatch):
    """push completes to completion without requiring any interactive input."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    # stdin is closed — a truly non-interactive run must not block on it.
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    with patch("devex.cli.push_script.run", return_value=("result\n", 0, "")):
        code = cli.main(["push", "--agent", "claude-code"])
    assert code == 0
