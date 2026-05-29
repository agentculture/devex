"""Detached-await mechanics for `devex pr await --detach` / `--check`.

PR-namespace home for the non-blocking await (issue #64): the result-marker
schema, atomic marker read/write, and the detached-subprocess spawn helper.
Mirrors how `_journal.py` wraps `core/journal.py` — keeps the pr-specific
``await.json`` contract out of `core/`, which it only *uses* (``data_dir``).

The marker lives at ``.devex/data/pr/<pr>/await.json`` (gitignored, like the
journal).  The foreground ``--detach`` writes a ``polling`` marker and spawns a
detached worker; the worker atomically overwrites it with the final ``done``
verdict.  ``--check`` only ever reads it.

Marker is written via temp-file + ``os.replace`` (atomic on POSIX and Windows),
so a concurrent reader always sees a complete old-or-new file — no lock needed
for the whole-file marker (the append-only JSONL journal keeps its lock).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from devex.core.paths import data_dir

# Bump when the marker shape changes incompatibly; `check` reports a clear
# notice (rather than crashing) when it reads a marker with a different schema.
MARKER_SCHEMA = 1

# Importable module path for the detached worker, run as `python -m <this>`.
WORKER_MODULE = "devex.commands.pr.scripts._await_worker"


def _pr_dir(pr: int, cwd: Path | None = None) -> Path:
    return data_dir(cwd) / "pr" / str(pr)


def marker_path(pr: int, cwd: Path | None = None) -> Path:
    return _pr_dir(pr, cwd) / "await.json"


def worker_log_path(pr: int, cwd: Path | None = None) -> Path:
    return _pr_dir(pr, cwd) / "await.worker.log"


def write_marker(pr: int, payload: dict[str, Any], cwd: Path | None = None) -> None:
    """Atomically write the await marker for ``pr``.

    Writes a sibling ``await.json.tmp`` then ``os.replace``s it into place so a
    concurrent ``--check`` reader never observes a torn write.
    """
    path = marker_path(pr, cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def read_marker(pr: int, cwd: Path | None = None) -> dict[str, Any] | None:
    """Return the await marker for ``pr``, or ``None`` if missing/corrupt."""
    path = marker_path(pr, cwd)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _spawn_detached(argv: list[str], cwd: Path, *, log_path: Path) -> int:
    """Spawn ``argv`` as a detached background process; return its PID.

    The child outlives the agent's shell session: on POSIX it gets its own
    session (``setsid`` via ``start_new_session``); on Windows it detaches from
    the console and gets a fresh process group.  stdin is ``/dev/null``; stdout
    and stderr go to ``log_path`` so a child that dies before writing its marker
    still leaves a forensic trail.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    kwargs: dict[str, Any] = {}
    if os.name == "nt":
        # These flags exist only on Windows (re-exported from _winapi); guarded
        # by the os.name check so the attribute access never runs on POSIX.
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
            | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        kwargs["start_new_session"] = True
        kwargs["close_fds"] = True

    log = open(log_path, "ab", buffering=0)
    try:
        # nosec B603 — argv is [sys.executable, "-m", fixed-module, validated
        # int/int/enum-value/whitelisted-prog]; no shell, no untrusted input.
        proc = subprocess.Popen(  # nosec B603
            argv,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            **kwargs,
        )
    finally:
        log.close()  # parent's handle; the child inherited its own
    return proc.pid


def spawn_worker(
    pr: int,
    max_wait: int,
    backend_value: str,
    prog: str,
    cwd: Path,
) -> int:
    """Spawn the detached await worker for ``pr``; return its PID."""
    argv = [
        sys.executable,
        "-m",
        WORKER_MODULE,
        str(pr),
        str(max_wait),
        backend_value,
        prog,
    ]
    return _spawn_detached(argv, cwd, log_path=worker_log_path(pr, cwd))
