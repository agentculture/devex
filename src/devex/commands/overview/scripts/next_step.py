"""Prioritized 'Next step:' rule key for `devex overview`.

Returns ``(rule_key, context)`` for :func:`devex.core.footer.render_footer`.
Per-backend hint phrasing lives in
``commands/overview/assets/backends/<backend>.yaml``.
"""

from __future__ import annotations

from typing import Any


def overview_next_step() -> tuple[str, dict[str, Any]]:
    """Return the footer rule key and context for `devex overview`.

    Currently emits a single rule key — ``overview_done`` — that directs the
    running agent to drill deeper into a skill or topic after reviewing the
    overview briefing.
    """
    return "overview_done", {}
