"""Render the trailing 'Next step:' footer for every `devex pr` command.

Thin shim over the command-agnostic :mod:`devex.core.footer` renderer. The only
``pr``-specific knowledge here is *where* the per-backend hints live — the
``commands/pr/assets/backends`` package — which this module supplies so the core
renderer stays command-neutral and reusable by other namespaces.
"""

from __future__ import annotations

from typing import Any

from markupsafe import Markup

from devex.core.backend import Backend
from devex.core.footer import render_footer as _render_footer

_BACKENDS_PKG = "devex.commands.pr.assets.backends"


def render_footer(rule_key: str, backend: Backend, context: dict[str, Any]) -> Markup:
    return _render_footer(rule_key, backend, context, _BACKENDS_PKG)
