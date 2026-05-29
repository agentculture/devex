import devex.cli as cli


def test_hook_write_is_silent_and_creates_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["hook", "write", "post-tool-use", "tool=Read"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == ""
    assert (tmp_path / ".devex" / "data" / "post-tool-use.json").exists()


def test_hook_read_renders_table_with_source(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cli.main(["hook", "write", "post-tool-use", "tool=Read"])
    capsys.readouterr()
    cli.main(["hook", "write", "post-tool-use", "tool=Write"])
    capsys.readouterr()
    code = cli.main(["hook", "read", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "post-tool-use" in captured.out
    assert "Source:" in captured.out
    assert "Read" in captured.out or "tool=Read" in captured.out
    # Row count: exactly two `| post-tool-use |` rows, one per write
    assert captured.out.count("| post-tool-use |") == 2


def test_hook_write_drops_empty_key_pairs(tmp_path, monkeypatch, capsys):
    import json as json_mod

    monkeypatch.chdir(tmp_path)
    code = cli.main(["hook", "write", "post-tool-use", "=orphan", "tool=Read"])
    capsys.readouterr()
    assert code == 0
    line = (
        (tmp_path / ".devex" / "data" / "post-tool-use.json")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    payload = json_mod.loads(line)
    assert "" not in payload  # empty key dropped
    assert payload["tool"] == "Read"
    assert payload["event"] == "post-tool-use"


def test_hook_read_empty_shows_no_events(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["hook", "read", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "_no events_" in captured.out


def test_hook_read_discovers_nested_jsonl(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from devex.core import journal as core_journal
    from devex.core.paths import ensure_init

    ensure_init()
    core_journal.append_event("pr/events", {"type": "pr_opened", "pr": 42})

    from devex.commands.hook.scripts import read as hook_read
    from devex.core.backend import Backend

    stdout, exit_code, _ = hook_read.run(backend=Backend.CLAUDE_CODE)
    assert exit_code == 0
    assert "pr_opened" in stdout
    # The stream identifier somewhere in output (could be "pr/events" or "pr/events.jsonl")
    assert "pr/events" in stdout or "pr/events.jsonl" in stdout or "pr_events" in stdout


def test_hook_write_rejects_path_traversal(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    for bad in ("../../etc/passwd", "/etc/passwd", "..", "a/b", "POST-TOOL-USE", "_underscore"):
        code = cli.main(["hook", "write", bad, "k=v"])
        captured = capsys.readouterr()
        assert code == 2, f"expected exit 2 for event={bad!r}"
        assert "invalid stream name" in captured.err.lower()
        # The bad name must never land on disk.
        assert not any((tmp_path / ".devex" / "data").rglob(f"*{bad.split('/')[-1]}*"))
