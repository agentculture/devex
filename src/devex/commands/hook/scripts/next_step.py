"""Prioritized 'Next step:' rule keys for `devex hook read`.

Each function takes the data the command already gathered and returns the
footer rule key + a context dict for variable substitution.  First match
wins.  Per-backend phrasing lives in `assets/backends/*.yaml`.
"""

from __future__ import annotations

from typing import Any


def hook_read_next_step(has_events: bool) -> tuple[str, dict[str, Any]]:
    """Return (rule_key, context) for the hook read footer.

    :param has_events: True if at least one stream has recorded events.
    """
    if has_events:
        return "hook_read_has_events", {}
    return "hook_read_empty", {}
