from concurrent.futures import ThreadPoolExecutor

import portalocker
import pytest
from portalocker.exceptions import AlreadyLocked

from devex.core.hook_io import append_event, load_events, render_table
from devex.core.paths import ensure_init


def test_append_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_init()
    append_event("post-tool-use", {"tool": "Read", "ts": "2026-04-18T10:00:00Z"})
    append_event("post-tool-use", {"tool": "Write", "ts": "2026-04-18T10:00:01Z"})
    events = load_events("post-tool-use")
    assert len(events) == 2
    assert events[0]["tool"] == "Read"


def test_load_events_missing_stream_returns_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_init()
    assert load_events("never-written") == []


def test_append_event_rejects_invalid_stream_name(tmp_path, monkeypatch):
    import pytest

    monkeypatch.chdir(tmp_path)
    ensure_init()
    for bad in ("../evil", "/etc/passwd", "..", "a/b", "UPPER", "_leading"):
        with pytest.raises(ValueError, match="invalid stream name"):
            append_event(bad, {"k": "v"})
        with pytest.raises(ValueError, match="invalid stream name"):
            load_events(bad)
    # Ensure no stray files landed in .devex/data/
    assert list((tmp_path / ".devex" / "data").iterdir()) == []


def test_load_events_skips_malformed_lines_with_warning(tmp_path, monkeypatch):
    import pytest

    monkeypatch.chdir(tmp_path)
    ensure_init()
    # Write a mix of valid and malformed lines (simulates a partial write
    # or an externally edited data file).
    data_file = tmp_path / ".devex" / "data" / "post-tool-use.json"
    data_file.parent.mkdir(parents=True, exist_ok=True)
    data_file.write_text(
        '{"ts":"2026-04-18T10:00:00Z","tool":"Read"}\n'
        '{"ts":"2026-04-18T10:00:01Z","tool"\n'  # truncated, invalid JSON
        '{"ts":"2026-04-18T10:00:02Z","tool":"Write"}\n',
        encoding="utf-8",
    )
    with pytest.warns(UserWarning, match="skipping malformed JSON line"):
        events = load_events("post-tool-use")
    assert len(events) == 2
    assert [e["tool"] for e in events] == ["Read", "Write"]


def test_render_table_produces_markdown():
    events = [
        {"ts": "2026-04-18T10:00:00Z", "tool": "Read"},
        {"ts": "2026-04-18T10:00:01Z", "tool": "Write"},
    ]
    table = render_table(events, columns=["ts", "tool"])
    assert "| ts | tool |" in table
    assert "| 2026-04-18T10:00:00Z | Read |" in table


def test_concurrent_appends_no_corruption(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_init()
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(
            ex.map(
                lambda i: append_event("stop", {"i": i}),
                range(50),
            )
        )
    events = load_events("stop")
    assert len(events) == 50
    assert sorted(e["i"] for e in events) == list(range(50))


def test_append_event_retries_on_already_locked(tmp_path, monkeypatch):
    """Regression test for issue #12: append_event retries when portalocker
    reports AlreadyLocked (Windows msvcrt EDEADLK), rather than propagating
    on the first transient failure."""
    monkeypatch.chdir(tmp_path)
    ensure_init()

    call_count = {"n": 0}
    original_lock = portalocker.lock

    def flaky_lock(fh, flags):
        call_count["n"] += 1
        if call_count["n"] <= 2:  # fail the first two attempts
            raise AlreadyLocked("simulated Windows msvcrt EDEADLK")
        return original_lock(fh, flags)

    # Import the module so we patch the SAME reference append_event uses.
    # `random.uniform` is intentionally NOT patched — the test only asserts
    # call count and final state, so the jitter value does not matter.
    from devex.core import hook_io

    monkeypatch.setattr(hook_io.portalocker, "lock", flaky_lock)
    # Patch out sleep so the test finishes instantly
    monkeypatch.setattr(hook_io.time, "sleep", lambda _: None)

    append_event("stop", {"i": 42})

    events = load_events("stop")
    assert len(events) == 1
    assert events[0]["i"] == 42
    assert call_count["n"] == 3  # two failed attempts + one success


def test_append_event_gives_up_after_max_attempts(tmp_path, monkeypatch):
    """If every retry fails, the final AlreadyLocked is propagated (no silent
    data loss)."""
    monkeypatch.chdir(tmp_path)
    ensure_init()

    # `random.uniform` is intentionally NOT patched — see the companion test
    # for the rationale (only call count and final outcome are asserted).
    from devex.core import hook_io

    def always_fail(fh, flags):
        raise AlreadyLocked("simulated persistent lock contention")

    monkeypatch.setattr(hook_io.portalocker, "lock", always_fail)
    # Patch out sleep so the test finishes instantly
    monkeypatch.setattr(hook_io.time, "sleep", lambda _: None)

    with pytest.raises(AlreadyLocked):
        append_event("stop", {"i": 42})
