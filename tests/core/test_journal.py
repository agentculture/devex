import json

import pytest

from devex.core import journal


def test_append_event_creates_nested_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    journal.append_event("pr/events", {"type": "pr_opened", "pr": 42})
    out = tmp_path / ".devex" / "data" / "pr" / "events.jsonl"
    assert out.exists()
    line = out.read_text(encoding="utf-8").strip()
    assert json.loads(line) == {"type": "pr_opened", "pr": 42}


def test_append_event_appends_multiple_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    journal.append_event("pr/events", {"type": "pr_opened", "pr": 42})
    journal.append_event("pr/events", {"type": "pr_read", "pr": 42})
    out = tmp_path / ".devex" / "data" / "pr" / "events.jsonl"
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["type"] == "pr_opened"
    assert json.loads(lines[1])["type"] == "pr_read"


def test_load_events_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert journal.load_events("pr/events") == []


def test_load_events_skips_malformed_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / ".devex" / "data" / "pr" / "events.jsonl"
    out.parent.mkdir(parents=True)
    out.write_text('{"type":"ok"}\n{not json\n{"type":"ok2"}\n', encoding="utf-8")
    with pytest.warns(UserWarning, match="malformed"):
        events = journal.load_events("pr/events")
    assert [e["type"] for e in events] == ["ok", "ok2"]


def test_validate_stream_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="invalid stream"):
        journal.append_event("../evil", {})
    with pytest.raises(ValueError, match="invalid stream"):
        journal.append_event("pr/../evil", {})
