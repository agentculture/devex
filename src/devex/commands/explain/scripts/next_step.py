"""Prioritized 'Next step:' rule key for `devex explain`.

Returns ``(rule_key, context)`` for the footer renderers
(:func:`devex.core.footer.render_footer` with a backend, or
:func:`devex.core.footer.render_neutral_footer` without one).

`devex explain` resolves a topic to one of three *kinds* — a command
skill, a lesson topic, or a standalone concept page — and the most useful
"next step" differs per kind:

* ``explain_command`` — the topic is a devex command; nudge the agent to run
  it (or read the matching ``learn`` lesson).
* ``explain_lesson`` — the topic is a ``learn`` lesson; nudge toward
  ``devex learn <topic>`` which teaches it interactively.
* ``explain_concept`` — the topic is a free-standing concept page; nudge
  toward the broader ``devex explain devex`` overview / picking a command.

Per-backend hint phrasing lives in
``commands/explain/assets/backends/<backend>.yaml``; the neutral phrasing
lives in ``core/assets/backends/neutral.yaml``.
"""

from __future__ import annotations

from typing import Any

# Map explain's internal resolution `kind` (returned by `resolve_topic`) onto
# the footer rule key. Kept as a dict so adding a kind is a one-line change and
# the rule keys appear exactly once in source.
_KIND_TO_RULE = {
    "command": "explain_command",
    "lesson": "explain_lesson",
    "concept": "explain_concept",
}


def explain_next_step(kind: str, topic: str) -> tuple[str, dict[str, Any]]:
    """Return the footer rule key and context for a resolved `devex explain`.

    *kind* is the resolution kind from
    :func:`devex.commands.explain.scripts.explain.resolve_topic`
    (``"command"`` / ``"lesson"`` / ``"concept"``); *topic* is the resolved
    topic slug. The returned context exposes ``topic`` to the hint template.
    """
    rule_key = _KIND_TO_RULE.get(kind, "explain_concept")
    return rule_key, {"topic": topic}
