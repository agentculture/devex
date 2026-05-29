"""Prioritized 'Next step:' rule keys for `devex learn`.

Returns the footer rule key + a context dict for variable substitution.
First-match-wins, matching the pr namespace convention.
Per-backend phrasing lives in `assets/backends/*.yaml`.
"""

from __future__ import annotations

from typing import Any


def learn_next_step(is_menu: bool) -> tuple[str, dict[str, Any]]:
    """Return (rule_key, context) for the learn footer.

    ``is_menu=True``  → the caller is rendering the topic-list menu.
    ``is_menu=False`` → the caller is rendering a specific lesson.
    """
    if is_menu:
        return "learn_menu", {}
    return "learn_topic", {}
