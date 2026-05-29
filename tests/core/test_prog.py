"""Tests for the invoked-command-name resolver (`core.prog`)."""

import pytest

from devex.core.prog import error_prefix, prog_name


@pytest.mark.parametrize(
    "argv0,expected",
    [
        ("/usr/local/bin/agex", "agex"),
        ("/usr/local/bin/devex", "devex"),
        ("agex", "agex"),
        ("devex", "devex"),
        # Wrapper suffixes must be stripped before matching: Windows console
        # scripts (`devex.exe`) and legacy setuptools shims (`devex-script.py`,
        # `devex.py`) must still resolve to the real entry point, not fall back.
        # (Path separators are handled by os.path.basename on the real platform;
        # we pass bare basenames here so the test is OS-independent.)
        ("devex.exe", "devex"),
        ("agex.exe", "agex"),
        ("devex-script.py", "devex"),
        ("devex.py", "devex"),
        # Anything that isn't one of the two real entry points falls back to
        # the canonical name so rendered output / tests stay deterministic.
        ("/usr/bin/python", "devex"),
        ("pytest", "devex"),
        ("", "devex"),
    ],
)
def test_prog_name_resolves_from_argv0(monkeypatch, argv0, expected):
    monkeypatch.setattr("sys.argv", [argv0, "pr", "read", "5"])
    assert prog_name() == expected


@pytest.mark.parametrize("argv0,prog", [("agex", "agex"), ("devex", "devex")])
def test_error_prefix_follows_invocation(monkeypatch, argv0, prog):
    monkeypatch.setattr("sys.argv", [argv0])
    assert error_prefix("boom") == f"{prog}: error: boom"
