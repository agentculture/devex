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

# On Windows, portalocker uses msvcrt.locking() which can raise EDEADLK
# (mapped to AlreadyLocked) when two writers race for the same append lock.
# A handful of short retries is sufficient because the other writer releases
# within microseconds. See https://github.com/agentculture/devex/issues/12.
_LOCK_MAX_ATTEMPTS = 5  # total attempts before giving up
_LOCK_BASE_SLEEP_SEC = 0.01  # 10ms base backoff (writes complete in microseconds)

# Stream names are joined into `.devex/data/<stream>.json`, so they must be a
# safe slug to prevent path traversal (e.g., `../../evil`). Same whitelist as
# `explain <topic>` / `learn <topic>`.
_STREAM_RE = re.compile(r"^[a-z][a-z0-9-]*$")


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
    # Unreachable by construction — the loop always records an exception before
    # breaking — but an explicit guard keeps the re-raise safe under `python -O`
    # (which strips `assert`) and satisfies type narrowing. The re-raise is
    # outside any `except` block, so no implicit exception chain needs
    # suppressing and a bare `raise last_exc` (not `from`) is the idiomatic form.
    if last_exc is None:  # pragma: no cover
        raise RuntimeError("_acquire_lock_with_retry: no exception recorded")
    raise last_exc


def _validate_stream(stream: str) -> None:
    if not _STREAM_RE.match(stream):
        raise ValueError(f"invalid stream name {stream!r}; must match ^[a-z][a-z0-9-]*$")


def _stream_path(stream: str) -> Path:
    _validate_stream(stream)
    return data_dir() / f"{stream}.json"


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
    # Malformed lines (partial writes, external edits) are skipped with a
    # warning rather than raised, so `devex hook read` stays a read-only
    # snapshot even when a `.devex/data/*.json` file gets corrupted.
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


def render_table(events: list[dict[str, Any]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    rows = ["| " + " | ".join(str(e.get(c, "")) for c in columns) + " |" for e in events]
    return "\n".join([header, sep, *rows]) + "\n"
