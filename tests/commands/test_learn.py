import devex.cli as cli
from devex.commands.learn.scripts.next_step import learn_next_step

# ---------------------------------------------------------------------------
# Unit tests for learn_next_step decision function
# ---------------------------------------------------------------------------


def test_learn_next_step_menu_returns_learn_menu():
    rule_key, ctx = learn_next_step(is_menu=True)
    assert rule_key == "learn_menu"
    assert isinstance(ctx, dict)


def test_learn_next_step_topic_returns_learn_topic():
    rule_key, ctx = learn_next_step(is_menu=False)
    assert rule_key == "learn_topic"
    assert isinstance(ctx, dict)


# ---------------------------------------------------------------------------
# Integration tests: footer present in rendered output
# ---------------------------------------------------------------------------


def test_learn_menu_ends_with_next_step_footer(capsys):
    code = cli.main(["learn", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "**Next step:**" in captured.out
    # The menu footer should reference the learn command
    assert "learn" in captured.out.split("**Next step:**")[-1]


def test_learn_topic_ends_with_next_step_footer(capsys):
    code = cli.main(["learn", "introspect", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "**Next step:**" in captured.out
    # The topic footer should reference the learn command
    assert "learn" in captured.out.split("**Next step:**")[-1]


def test_learn_menu_footer_all_backends(capsys):
    """All four backends produce a Next step footer from the menu."""
    for backend in ("claude-code", "codex", "copilot", "acp"):
        code = cli.main(["learn", "--agent", backend])
        captured = capsys.readouterr()
        assert code == 0, f"exit {code} for backend={backend!r}"
        assert "**Next step:**" in captured.out, f"no footer for backend={backend!r}"


def test_learn_topic_footer_all_backends(capsys):
    """All four backends produce a Next step footer for a topic lesson."""
    for backend in ("claude-code", "codex", "copilot", "acp"):
        code = cli.main(["learn", "introspect", "--agent", backend])
        captured = capsys.readouterr()
        assert code == 0, f"exit {code} for backend={backend!r}"
        assert "**Next step:**" in captured.out, f"no footer for backend={backend!r}"


def test_learn_menu_lists_introspect(capsys):
    code = cli.main(["learn", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "introspect" in captured.out


def test_learn_introspect_emits_lesson_and_template(capsys):
    code = cli.main(["learn", "introspect", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "build an `introspect` skill" in captured.out
    # Template body embedded as code block
    assert "Audit the current project" in captured.out


def test_learn_unknown_topic_errors_with_menu(capsys):
    code = cli.main(["learn", "xyz", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 2
    assert "unknown topic" in captured.err.lower()
    assert "introspect" in captured.out  # menu in stdout


def test_learn_rejects_path_traversal(capsys):
    for bad in ("../../../etc/passwd", "/etc/passwd", "..", "a/b", "INTROSPECT"):
        code = cli.main(["learn", bad, "--agent", "claude-code"])
        captured = capsys.readouterr()
        assert code == 2, f"expected exit 2 for topic={bad!r}"
        assert "unknown topic" in captured.err.lower()


def test_learn_menu_lists_all_v01_topics(capsys):
    cli.main(["learn", "--agent", "claude-code"])
    captured = capsys.readouterr()
    for topic in ("introspect", "visualize", "gamify", "levelup"):
        assert topic in captured.out


def test_learn_visualize_emits_lesson(capsys):
    code = cli.main(["learn", "visualize", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "visualize" in captured.out.lower()


def test_learn_gamify_includes_levelup_template(capsys):
    code = cli.main(["learn", "gamify", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "gamify" in captured.out
    assert "levelup" in captured.out
