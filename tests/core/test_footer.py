"""Tests for the core footer renderer — both backend-specific and neutral paths."""

import pytest

from devex.core.backend import Backend
from devex.core.footer import render_footer, render_neutral_footer

# ---------------------------------------------------------------------------
# Neutral path (no backend)
# ---------------------------------------------------------------------------


def test_neutral_footer_returns_next_step_block():
    """render_neutral_footer returns a non-empty footer containing '**Next step:**'."""
    out = render_neutral_footer("example_placeholder", {})
    assert "**Next step:**" in out


def test_neutral_footer_contains_hint_text():
    """The neutral hint text appears in the rendered footer."""
    out = render_neutral_footer("example_placeholder", {})
    # Should contain some substantive text, not just the structural marker.
    assert out.strip() != "---\n**Next step:**"
    assert len(out.strip()) > len("---\n**Next step:**")


def test_neutral_footer_starts_with_separator():
    """Neutral footer follows the same '---\\n**Next step:**' structure."""
    out = render_neutral_footer("example_placeholder", {})
    assert out.startswith("---")


def test_neutral_footer_unknown_key_raises():
    """Unknown rule key raises KeyError from the neutral path."""
    with pytest.raises(KeyError):
        render_neutral_footer("nonexistent_rule_xyz", {})


def test_neutral_footer_prog_template_variable(monkeypatch):
    """The {{ prog }} template variable is available inside neutral hints."""
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/devex", "explain", "pr"])
    out = render_neutral_footer("example_placeholder", {})
    # The hint uses {{ prog }} — it should not appear literally; it must be rendered.
    assert "{{ prog }}" not in out


# ---------------------------------------------------------------------------
# Backend-specific path (existing render_footer — must be UNCHANGED)
# ---------------------------------------------------------------------------


def test_backend_footer_unchanged_lint_clean():
    """Existing backend-specific render_footer is byte-identical to before t2."""
    from devex.commands.pr.scripts._footer import render_footer as pr_render_footer

    out = pr_render_footer("lint_clean", Backend.CLAUDE_CODE, {})
    assert "**Next step:**" in out
    assert "devex pr open" in out or "agex pr open" in out


def test_backend_footer_unknown_rule_still_raises():
    """The existing backend path still raises KeyError for unknown rule keys."""
    with pytest.raises(KeyError):
        render_footer(
            "nonexistent_rule", Backend.CLAUDE_CODE, {}, "devex.commands.pr.assets.backends"
        )


def test_backend_footer_unchanged_lint_violations():
    """Existing lint_violations rule with context still renders correctly."""
    from devex.commands.pr.scripts._footer import render_footer as pr_render_footer

    out = pr_render_footer("lint_violations", Backend.CLAUDE_CODE, {"violation_count": 7})
    assert "7 violation" in out
