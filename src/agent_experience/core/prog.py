"""Single source of truth for the command name the CLI was invoked as.

The package ships two console-script entry points — ``agex`` (canonical) and
``devex`` (alias) — both pointing at the same ``_main_entrypoint``. So the
program name is not a constant: it depends on which entry point the user typed.
Resolving it from ``sys.argv[0]`` lets emitted output (Next-step footers,
briefing headers, error prefixes) reflect whatever name was actually invoked.

The result is whitelisted to the two real entry points. Non-entry-point
invocations (``python -m agent_experience``, pytest, a renamed shim) would
otherwise leak ``__main__``/``pytest`` into rendered markdown and make tests
non-deterministic; for those we fall back to the canonical ``agex``.
"""

import os
import sys

_CANONICAL = "agex"
_KNOWN = {"agex", "devex"}


def prog_name() -> str:
    """Return the command the CLI was invoked as (``agex`` or ``devex``)."""
    base = os.path.basename(sys.argv[0] or "")
    return base if base in _KNOWN else _CANONICAL
