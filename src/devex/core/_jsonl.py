"""Shared file-locked JSON-per-line append/load primitives.

Used by both `core/journal.py` (nested `pr/events.jsonl` streams) and
`core/hook_io.py` (flat `<event>.json` hook streams). Each caller owns its own
stream-name validation and path layout (`.jsonl` vs `.json`, one-slash vs flat);
this module owns the cross-platform file locking (portalocker with bounded
retry) and the append/read mechanics that were otherwise copy-pasted between the
two. See the pr-design spec note: "a future refactor can collapse the two."
"""

from __future__ import annotations

import json
import os
import random
import time
import warnings
from pathlib import Path
from typing import Any

import portalocker
from portalocker.exceptions import AlreadyLocked

# On Windows, portalocker uses msvcrt.locking() which can raise EDEADLK
# (mapped to AlreadyLocked) when two writers race for the same append lock.
# A handful of short retries is sufficient because the other writer releases
# within microseconds. See https://github.com/agentculture/devex/issues/12.
_LOCK_MAX_ATTEMPTS = 5  # total attempts before giving up
_LOCK_BASE_SLEEP_SEC = 0.01  # 10ms base backoff (writes complete in microseconds)


def acquire_lock_with_retry(fh) -> None:
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
        raise RuntimeError("acquire_lock_with_retry: no exception recorded")
    raise last_exc


def append_line(path: Path, payload: dict[str, Any]) -> None:
    """Append one compact JSON line to ``path`` under an exclusive lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        acquire_lock_with_retry(fh)
        try:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            portalocker.unlock(fh)


def load_lines(path: Path) -> list[dict[str, Any]]:
    """Read JSON-per-line from ``path``; skip malformed lines with a warning.

    Missing file → ``[]``. A partial write or external edit can't crash the
    reader — the bad line is skipped with a ``UserWarning`` instead.
    """
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
