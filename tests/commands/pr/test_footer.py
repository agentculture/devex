import pytest

from agent_experience.commands.pr.scripts._footer import render_footer
from agent_experience.core.backend import Backend


def test_lint_clean_for_claude_code():
    out = render_footer("lint_clean", Backend.CLAUDE_CODE, {})
    assert "Next step" in out
    assert "agex pr open" in out


def test_lint_violations_includes_count():
    out = render_footer("lint_violations", Backend.CLAUDE_CODE, {"violation_count": 3})
    assert "3 violation" in out
    assert "agex pr lint" in out


def test_read_wait_recommendation_uses_schedule_for_claude_code():
    out = render_footer("open_recommend_read", Backend.CLAUDE_CODE, {"pr": 42})
    assert "agex pr read 42 --wait 180" in out


def test_read_wait_recommendation_plain_for_codex():
    out = render_footer("open_recommend_read", Backend.CODEX, {"pr": 42})
    assert "agex pr read 42 --wait 180" in out


def test_unknown_rule_key_raises():
    with pytest.raises(KeyError):
        render_footer("nonexistent_rule", Backend.CLAUDE_CODE, {})


def test_footer_follows_invoked_command_name(monkeypatch):
    # When invoked as `devex`, the footer hint must say `devex pr ...` rather
    # than the canonical `agex` — the `{{ prog }}` template var resolves from
    # sys.argv[0] via core.prog.prog_name().
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/devex", "pr", "open"])
    out = render_footer("open_recommend_read", Backend.CLAUDE_CODE, {"pr": 42})
    assert "devex pr read 42 --wait 180" in out
    assert "agex" not in out


def test_footer_defaults_to_agex_without_devex_invocation(monkeypatch):
    monkeypatch.setattr("sys.argv", ["agex", "pr", "open"])
    out = render_footer("open_recommend_read", Backend.CLAUDE_CODE, {"pr": 42})
    assert "agex pr read 42 --wait 180" in out


def test_footer_does_not_double_escape_quotes():
    # Regression: render_string autoescape used to escape `"` to `&#34;`,
    # then the second pass escaped it again to `&amp;#34;`.
    out = render_footer("lint_clean", Backend.CLAUDE_CODE, {})
    assert "&amp;" not in out
    assert "&#34;" not in out
    assert '"' in out
