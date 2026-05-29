"""Stream-name aware wrapper over core.journal for the pr namespace."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from devex.core import journal

_STREAM = "pr/events"


def append(payload: dict[str, Any]) -> None:
    """Append a pr event with a UTC ISO-8601 ts auto-injected if missing."""
    if "ts" not in payload:
        payload = {"ts": datetime.now(timezone.utc).isoformat(), **payload}
    journal.append_event(_STREAM, payload)


def load() -> list[dict[str, Any]]:
    return journal.load_events(_STREAM)
