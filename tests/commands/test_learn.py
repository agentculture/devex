import devex.cli as cli


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
