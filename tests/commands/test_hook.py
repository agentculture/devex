import devex.cli as cli

# ---------------------------------------------------------------------------
# t7: Next step footer for hook read (hook write stays silent)
# ---------------------------------------------------------------------------


def test_hook_read_has_footer_with_events(tmp_path, monkeypatch, capsys):
    """hook read with events emits a '**Next step:**' footer."""
    monkeypatch.chdir(tmp_path)
    cli.main(["hook", "write", "post-tool-use", "tool=Read"])
    capsys.readouterr()
    code = cli.main(["hook", "read", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "**Next step:**" in captured.out


def test_hook_read_has_footer_when_empty(tmp_path, monkeypatch, capsys):
    """hook read with no events still emits a '**Next step:**' footer."""
    monkeypatch.chdir(tmp_path)
    code = cli.main(["hook", "read", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "**Next step:**" in captured.out


def test_hook_read_empty_footer_mentions_overview(tmp_path, monkeypatch, capsys):
    """hook read with no events references 'overview' in its footer hint."""
    monkeypatch.chdir(tmp_path)
    cli.main(["hook", "read", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert "overview" in captured.out


def test_hook_read_footer_all_backends(tmp_path, monkeypatch, capsys):
    """hook read emits a footer for every supported backend."""
    for backend in ("claude-code", "codex", "copilot", "acp"):
        monkeypatch.chdir(tmp_path)
        code = cli.main(["hook", "read", "--agent", backend])
        captured = capsys.readouterr()
        assert code == 0, f"hook read failed for backend={backend!r}"
        assert "**Next step:**" in captured.out, f"no footer for backend={backend!r}"


def test_hook_write_stays_silent_after_t7(tmp_path, monkeypatch, capsys):
    """hook write MUST emit empty stdout — the t7 footer must NOT appear there."""
    monkeypatch.chdir(tmp_path)
    code = cli.main(["hook", "write", "post-tool-use", "tool=Bash"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "", "hook write must stay silent; got: " + repr(captured.out[:200])
    assert "**Next step:**" not in captured.out


def test_hook_read_next_step_has_events_rule_key(tmp_path, monkeypatch):
    """hook_read_next_step returns 'hook_read_has_events' when events exist."""
    monkeypatch.chdir(tmp_path)
    from devex.commands.hook.scripts.next_step import hook_read_next_step

    key, ctx = hook_read_next_step(has_events=True)
    assert key == "hook_read_has_events"


def test_hook_read_next_step_empty_rule_key(tmp_path, monkeypatch):
    """hook_read_next_step returns 'hook_read_empty' when no events exist."""
    from devex.commands.hook.scripts.next_step import hook_read_next_step

    key, ctx = hook_read_next_step(has_events=False)
    assert key == "hook_read_empty"


# ---------------------------------------------------------------------------
# Existing tests below
# ---------------------------------------------------------------------------


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
