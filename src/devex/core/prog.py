"""Single source of truth for the command name the CLI was invoked as.

The package ships two console-script entry points — ``devex`` (canonical) and
``agex`` (legacy alias) — both pointing at the same ``_main_entrypoint``. So the
program name is not a constant: it depends on which entry point the user typed.
Resolving it from ``sys.argv[0]`` lets emitted output (Next-step footers,
briefing headers, error prefixes) reflect whatever name was actually invoked.

The result is whitelisted to the two real entry points. Non-entry-point
invocations (``python -m devex``, pytest, a renamed shim) would
otherwise leak ``__main__``/``pytest`` into rendered markdown and make tests
non-deterministic; for those we fall back to the canonical ``devex``.
"""

import os
import sys

_CANONICAL = "devex"
_KNOWN = {"agex", "devex"}


def prog_name() -> str:
    """Return the command the CLI was invoked as (``devex`` or ``agex``)."""
    base = os.path.basename(sys.argv[0] or "")
    # Strip common entry-point wrapper suffixes before matching: Windows
    # console scripts are `devex.exe`; legacy setuptools shims can be
    # `devex.py` / `devex-script.py`. Without this, a real `agex` invocation
    # on Windows would fall back to the canonical `devex`.
    stem = base
    for ext in (".exe", ".py"):
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break
    if stem.endswith("-script"):
        stem = stem[: -len("-script")]
    return stem if stem in _KNOWN else _CANONICAL


def error_prefix(message: str) -> str:
    """``<prog>: error: <message>`` — the canonical CLI error line, phrased with
    whichever entry point (`agex`/`devex`) was invoked. Use for user-facing
    stderr in command scripts so output follows invocation (the Jinja `prog`
    injection in `render` only covers rendered templates, not plain strings)."""
    return f"{prog_name()}: error: {message}"
