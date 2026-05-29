"""Prioritized 'Next step:' rule key for `devex doctor`.

Returns ``(rule_key, context)`` for the footer renderers
(:func:`devex.core.footer.render_footer` with a backend, or
:func:`devex.core.footer.render_neutral_footer` without one).

`devex doctor` ends in one of two states:

* ``doctor_clean`` — no hard failures (exit 0); nudge the agent to proceed
  with its task.
* ``doctor_failures`` — one or more ``✗`` rows (exit 1); nudge the agent to
  fix the failing checks and rerun ``devex doctor``.

The footer reflects state only — it never changes the exit code. Per-backend
phrasing lives in ``commands/doctor/assets/backends/<backend>.yaml``; the
neutral phrasing lives in ``core/assets/backends/neutral.yaml``.
"""

from __future__ import annotations

from typing import Any


def doctor_next_step(fail_count: int) -> tuple[str, dict[str, Any]]:
    """Return the footer rule key and context for a completed `devex doctor`.

    *fail_count* is the number of hard ``fail`` rows in the report. The
    returned context exposes ``fail_count`` to the hint template so the
    failure phrasing can name how many checks need fixing.
    """
    if fail_count > 0:
        return "doctor_failures", {"fail_count": fail_count}
    return "doctor_clean", {}
