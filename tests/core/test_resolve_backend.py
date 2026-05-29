from pathlib import Path

import pytest
import yaml

from devex.core.backend import Backend, resolve_backend


def test_explicit_arg_wins(tmp_path: Path) -> None:
    (tmp_path / "culture.yaml").write_text(
        yaml.safe_dump({"agents": [{"name": "a", "backend": "codex"}]}), encoding="utf-8"
    )
    assert resolve_backend("claude-code", tmp_path) is Backend.CLAUDE_CODE


def test_culture_yaml_fallback(tmp_path: Path) -> None:
    (tmp_path / "culture.yaml").write_text(
        yaml.safe_dump({"agents": [{"name": "a", "backend": "codex"}]}), encoding="utf-8"
    )
    assert resolve_backend(None, tmp_path) is Backend.CODEX


def test_no_arg_no_culture_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="--agent required"):
        resolve_backend(None, tmp_path)


def test_culture_yaml_without_backend_raises(tmp_path: Path) -> None:
    (tmp_path / "culture.yaml").write_text(
        yaml.safe_dump({"agents": [{"name": "a"}]}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="--agent required"):
        resolve_backend(None, tmp_path)


def test_invalid_arg_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown backend"):
        resolve_backend("invalid", tmp_path)


def test_explicit_arg_claude_alias(tmp_path: Path) -> None:
    assert resolve_backend("claude", tmp_path) is Backend.CLAUDE_CODE


def test_culture_yaml_claude_alias(tmp_path: Path) -> None:
    (tmp_path / "culture.yaml").write_text(
        yaml.safe_dump({"agents": [{"suffix": "devex-cli", "backend": "claude"}]}),
        encoding="utf-8",
    )
    assert resolve_backend(None, tmp_path) is Backend.CLAUDE_CODE


def test_culture_yaml_unknown_backend_descriptive(tmp_path: Path) -> None:
    (tmp_path / "culture.yaml").write_text(
        yaml.safe_dump({"agents": [{"suffix": "devague", "backend": "foo"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as exc:
        resolve_backend(None, tmp_path)
    msg = str(exc.value)
    assert "culture.yaml agent 'devague' has unknown backend 'foo'" in msg
    assert "hint: expected one of claude (= claude-code)" in msg
