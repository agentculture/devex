"""Nested-stream JSONL journal for `.devex/data/<stream>.jsonl`.

Sister to `core/hook_io.py`, which only supports flat `<stream>.json` files
under `data/`.  The `pr` command namespace needs `data/pr/events.jsonl`, so
this module accepts stream names with one slash (e.g. `pr/events`) and
writes `.jsonl` extensions.

`hook_io.py` is left untouched — a future refactor can collapse the two.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
import warnings
from pathlib import Path
from typing import Any

import portalocker
from portalocker.exceptions import AlreadyLocked

from devex.core.paths import data_dir

_LOCK_MAX_ATTEMPTS = 5
_LOCK_BASE_SLEEP_SEC = 0.01

# Allow one optional slash so `pr/events`, `actions/runs`, etc. work.  Each
# segment must match the same slug rules `hook_io._STREAM_RE` enforces.
_SEGMENT = r"[a-z][a-z0-9-]*"
_STREAM_RE = re.compile(rf"^{_SEGMENT}(?:/{_SEGMENT})?$")


def _validate_stream(stream: str) -> None:
    if not _STREAM_RE.match(stream):
        raise ValueError(f"invalid stream {stream!r}; must match ^{_SEGMENT}(/{_SEGMENT})?$")


def _stream_path(stream: str) -> Path:
    _validate_stream(stream)
    return data_dir() / f"{stream}.jsonl"


def _acquire_lock_with_retry(fh) -> None:
    last_exc: AlreadyLocked | None = None
    for attempt in range(1, _LOCK_MAX_ATTEMPTS + 1):
        try:
            portalocker.lock(fh, portalocker.LOCK_EX)
            return
        except AlreadyLocked as exc:
            last_exc = exc
            if attempt == _LOCK_MAX_ATTEMPTS:
                break
            time.sleep(_LOCK_BASE_SLEEP_SEC * attempt + random.uniform(0, _LOCK_BASE_SLEEP_SEC))
    if last_exc is None:  # pragma: no cover
        raise RuntimeError("_acquire_lock_with_retry: no exception recorded")
    raise last_exc


def append_event(stream: str, payload: dict[str, Any]) -> None:
    path = _stream_path(stream)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        _acquire_lock_with_retry(fh)
        try:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            portalocker.unlock(fh)


def load_events(stream: str) -> list[dict[str, Any]]:
    path = _stream_path(stream)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as e:
            warnings.warn(f"{path}:{lineno}: skipping malformed JSON line: {e}", stacklevel=2)
    return events
