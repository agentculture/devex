"""Tests for the invoked-command-name resolver (`core.prog.prog_name`)."""

import pytest

from agent_experience.core.prog import prog_name


@pytest.mark.parametrize(
    "argv0,expected",
    [
        ("/usr/local/bin/agex", "agex"),
        ("/usr/local/bin/devex", "devex"),
        ("agex", "agex"),
        ("devex", "devex"),
        # Anything that isn't one of the two real entry points falls back to
        # the canonical name so rendered output / tests stay deterministic.
        ("/usr/bin/python", "agex"),
        ("pytest", "agex"),
        ("", "agex"),
    ],
)
def test_prog_name_resolves_from_argv0(monkeypatch, argv0, expected):
    monkeypatch.setattr("sys.argv", [argv0, "pr", "read", "5"])
    assert prog_name() == expected
