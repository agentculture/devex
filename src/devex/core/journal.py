"""Nested-stream JSONL journal for `.devex/data/<stream>.jsonl`.

Sister to `core/hook_io.py` (flat `<stream>.json`); both delegate the file
locking and append/load mechanics to `core/_jsonl.py`. This module owns the
stream-name shape it needs: one optional slash (e.g. `pr/events`,
`actions/runs`) and a `.jsonl` extension.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from devex.core import _jsonl
from devex.core.paths import data_dir

# Allow one optional slash so `pr/events`, `actions/runs`, etc. work. Each
# segment matches the same slug rules `hook_io._STREAM_RE` enforces.
_SEGMENT = r"[a-z][a-z0-9-]*"
_STREAM_RE = re.compile(rf"^{_SEGMENT}(?:/{_SEGMENT})?$")


def _validate_stream(stream: str) -> None:
    if not _STREAM_RE.match(stream):
        raise ValueError(f"invalid stream {stream!r}; must match ^{_SEGMENT}(/{_SEGMENT})?$")


def _stream_path(stream: str) -> Path:
    _validate_stream(stream)
    return data_dir() / f"{stream}.jsonl"


def append_event(stream: str, payload: dict[str, Any]) -> None:
    _jsonl.append_line(_stream_path(stream), payload)


def load_events(stream: str) -> list[dict[str, Any]]:
    return _jsonl.load_lines(_stream_path(stream))
