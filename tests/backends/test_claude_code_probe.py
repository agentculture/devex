from pathlib import Path

from devex.backends.claude_code.probe import probe

FIXTURES = Path(__file__).parent.parent / "fixtures" / "claude-code"


def test_probe_empty_project():
    result = probe(FIXTURES / "empty")
    assert result.skills == []
    assert result.hooks == []
    assert result.claude_md is None


def test_probe_typical_project():
    result = probe(FIXTURES / "typical")
    assert len(result.skills) == 1
    assert result.skills[0]["name"] == "example"
    assert result.claude_md is not None
    assert "CLAUDE.md" in str(result.claude_md)
    assert len(result.hooks) == 1
    assert result.hooks[0]["event"] == "post-tool-use"


def test_probe_missing_directory_returns_empty():
    result = probe(Path("/nonexistent-path-abc-123"))
    assert result.skills == []


def test_probe_malformed_inputs_warn_and_continue():
    result = probe(FIXTURES / "malformed")
    assert result.settings is None
    assert result.skills == []
    assert result.hooks == []
    # One warning each: settings.json, bad/SKILL.md (no frontmatter → ValueError),
    # broken-yaml/SKILL.md (frontmatter present, YAML parse error), hooks.json.
    assert len(result.warnings) == 4
    joined = " ".join(result.warnings)
    assert "settings.json" in joined
    assert "hooks.json" in joined
    # Accept both POSIX and Windows path separators.
    assert any("bad" in w and "SKILL.md" in w for w in result.warnings)
    assert any("broken-yaml" in w and "SKILL.md" in w for w in result.warnings)
    # Warnings must include the underlying error reason.
    assert "missing YAML frontmatter" in joined


def test_probe_hooks_json_not_dict_warns(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "hooks.json").write_text("[]", encoding="utf-8")
    result = probe(tmp_path)
    assert result.hooks == []
    assert any("expected a JSON object" in w for w in result.warnings)


def test_probe_hooks_json_entries_not_list_warns(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "hooks.json").write_text(
        '{"post-tool-use": "not-a-list"}', encoding="utf-8"
    )
    result = probe(tmp_path)
    assert result.hooks == []
    assert any("expected list for event 'post-tool-use'" in w for w in result.warnings)
