import devex.cli as cli
from devex.commands.explain.scripts.next_step import explain_next_step


def test_explain_agex_prints_self_describing_page(capsys):
    code = cli.main(["explain", "agex"])
    captured = capsys.readouterr()
    assert code == 0
    assert "agex" in captured.out
    assert "overview" in captured.out
    assert "learn" in captured.out


def test_explain_explain_reads_command_skill_md(capsys):
    code = cli.main(["explain", "explain"])
    captured = capsys.readouterr()
    assert code == 0
    assert "devex explain" in captured.out.lower()


def test_explain_unknown_topic_exits_2_with_menu(capsys):
    code = cli.main(["explain", "unknown-topic-xyz"])
    captured = capsys.readouterr()
    assert code == 2
    assert "unknown" in captured.err.lower()


def test_explain_rejects_path_traversal(capsys):
    for bad in ("../../../etc/passwd", "/etc/passwd", "..", "a/b", "learn/introspect"):
        code = cli.main(["explain", bad])
        capsys.readouterr()
        assert code == 2, f"expected exit 2 for topic={bad!r}"


# ---------------------------------------------------------------------------
# Optional --agent + 'Next step:' footer (t3)
# ---------------------------------------------------------------------------


def _footer_line(out: str) -> str:
    """Return the trailing 'Next step:' footer block of an explain page."""
    marker = "---\n**Next step:**"
    assert marker in out, "no Next step footer found"
    return out[out.rindex(marker) :]


def test_explain_emits_neutral_footer_without_agent(capsys):
    """Flagless `explain` still works and now ends with a neutral footer."""
    code = cli.main(["explain", "explain"])
    captured = capsys.readouterr()
    assert code == 0
    footer = _footer_line(captured.out)
    # Neutral phrasing leaves the backend as a placeholder, not a concrete one.
    assert "--agent <backend>" in footer
    assert "--agent claude-code" not in footer


def test_explain_emits_backend_footer_with_agent(capsys):
    """With --agent the footer uses that backend's per-command hints."""
    code = cli.main(["explain", "explain", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    footer = _footer_line(captured.out)
    assert "--agent claude-code" in footer
    assert "--agent <backend>" not in footer


def test_explain_backend_footer_differs_per_backend(capsys):
    """Each backend renders its own name into the footer."""
    cli.main(["explain", "explain", "--agent", "codex"])
    codex_out = capsys.readouterr().out
    cli.main(["explain", "explain", "--agent", "acp"])
    acp_out = capsys.readouterr().out
    assert "--agent codex" in codex_out
    assert "--agent acp" in acp_out


def test_explain_concept_footer_mentions_command_map(capsys):
    """A concept page (devex.md) gets the explain_concept footer."""
    code = cli.main(["explain", "devex"])
    captured = capsys.readouterr()
    assert code == 0
    assert "explain devex" in captured.out  # the command-map nudge


def test_explain_invalid_agent_exits_2(capsys):
    """An explicit but bogus --agent value is rejected with exit 2."""
    code = cli.main(["explain", "explain", "--agent", "bogus"])
    captured = capsys.readouterr()
    assert code == 2
    assert "unknown backend" in captured.err


def test_explain_path_traversal_still_rejected_with_agent(capsys):
    """The path-traversal guard runs before the footer, even with --agent."""
    for bad in ("../../../etc/passwd", "/etc/passwd", "..", "a/b"):
        code = cli.main(["explain", bad, "--agent", "claude-code"])
        capsys.readouterr()
        assert code == 2, f"expected exit 2 for topic={bad!r}"


def test_explain_unknown_topic_with_agent_still_exits_2(capsys):
    """Unknown topic keeps exit 2 (no footer) regardless of --agent."""
    code = cli.main(["explain", "unknown-topic-xyz", "--agent", "codex"])
    captured = capsys.readouterr()
    assert code == 2
    assert "unknown" in captured.err.lower()
    assert "**Next step:**" not in captured.out


def test_explain_next_step_maps_kinds_to_rule_keys():
    """The decision fn maps each resolution kind to a distinct rule key."""
    assert explain_next_step("command", "explain") == (
        "explain_command",
        {"topic": "explain"},
    )
    assert explain_next_step("lesson", "introspect") == (
        "explain_lesson",
        {"topic": "introspect"},
    )
    assert explain_next_step("concept", "devex") == (
        "explain_concept",
        {"topic": "devex"},
    )
