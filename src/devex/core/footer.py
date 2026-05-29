"""Render the trailing 'Next step:' footer shared by command namespaces.

This is the command-agnostic footer machinery. A caller supplies *where* the
per-backend hints live (``backends_pkg``, a dotted package name resolvable via
:func:`importlib.resources.files`) plus the rule key, backend and template
context; this module loads ``<backend>.yaml`` from that package, renders the
hint string through :func:`devex.core.render.render_string`, and wraps it in the
core-shipped ``footer.md.j2`` template.

The decision logic for *which* rule key to use, and the per-backend hint
phrasing, are command-specific and live with each command (e.g. the ``pr``
namespace keeps ``next_step_rules.py`` and ``assets/backends/*.yaml``).
"""

from __future__ import annotations

from importlib.resources import files
from typing import Any

import yaml
from markupsafe import Markup

from devex.core.backend import Backend
from devex.core.render import render_string

_TEMPLATES_PKG = "devex.core.assets"


def _load_hints(backends_pkg: str, backend: Backend) -> dict[str, str]:
    raw = files(backends_pkg).joinpath(f"{backend.value}.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    return dict(data.get("hints", {}))


def render_footer(
    rule_key: str, backend: Backend, context: dict[str, Any], backends_pkg: str
) -> Markup:
    hints = _load_hints(backends_pkg, backend)
    if rule_key not in hints:
        raise KeyError(f"no hint defined for rule {rule_key!r} on backend {backend.value!r}")
    hint = render_string(hints[rule_key], context)
    template = files(_TEMPLATES_PKG).joinpath("footer.md.j2").read_text(encoding="utf-8")
    footer = template.replace("{{ hint }}", hint)
    # Return as Markup so subsequent render_string calls won't escape it.
    return Markup(footer)
