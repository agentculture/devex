import devex.cli as cli


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
