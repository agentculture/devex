import pytest

from devex.core.backend import Backend, parse_backend


def test_backend_enum_values():
    assert Backend.CLAUDE_CODE.value == "claude-code"
    assert Backend.CODEX.value == "codex"
    assert Backend.COPILOT.value == "copilot"
    assert Backend.ACP.value == "acp"


def test_parse_backend_valid():
    assert parse_backend("claude-code") is Backend.CLAUDE_CODE
    assert parse_backend("codex") is Backend.CODEX


def test_parse_backend_claude_alias():
    assert parse_backend("claude") is Backend.CLAUDE_CODE


def test_parse_backend_invalid_raises():
    with pytest.raises(ValueError) as exc:
        parse_backend("gemini")
    assert "gemini" in str(exc.value)
    assert "claude (= claude-code)" in str(exc.value)  # lists valid options + alias


def test_parse_backend_case_sensitive():
    with pytest.raises(ValueError):
        parse_backend("Claude-Code")
