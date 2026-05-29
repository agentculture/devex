"""Flat-stream JSON-per-line hook I/O for `.devex/data/<stream>.json`.

Sister to `core/journal.py` (nested `<stream>.jsonl`); both delegate the file
locking and append/load mechanics to `core/_jsonl.py`. This module owns the flat
stream-name shape (no slash) and the markdown table renderer used by
`devex hook read`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from devex.core import _jsonl
from devex.core.paths import data_dir

# Stream names are joined into `.devex/data/<stream>.json`, so they must be a
# safe slug to prevent path traversal (e.g., `../../evil`). Same whitelist as
# `explain <topic>` / `learn <topic>`.
_STREAM_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def _validate_stream(stream: str) -> None:
    if not _STREAM_RE.match(stream):
        raise ValueError(f"invalid stream name {stream!r}; must match ^[a-z][a-z0-9-]*$")


def _stream_path(stream: str) -> Path:
    _validate_stream(stream)
    return data_dir() / f"{stream}.json"


def append_event(stream: str, payload: dict[str, Any]) -> None:
    _jsonl.append_line(_stream_path(stream), payload)


def load_events(stream: str) -> list[dict[str, Any]]:
    return _jsonl.load_lines(_stream_path(stream))


def render_table(events: list[dict[str, Any]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    rows = ["| " + " | ".join(str(e.get(c, "")) for c in columns) + " |" for e in events]
    return "\n".join([header, sep, *rows]) + "\n"
