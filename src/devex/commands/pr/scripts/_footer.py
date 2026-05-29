"""Render the trailing 'Next step:' footer for every `devex pr` command."""

from __future__ import annotations

from importlib.resources import files
from typing import Any

import yaml
from markupsafe import Markup

from devex.core.backend import Backend
from devex.core.render import render_string

_BACKENDS_PKG = "devex.commands.pr.assets.backends"
_TEMPLATES_PKG = "devex.commands.pr.assets.templates"


def _load_hints(backend: Backend) -> dict[str, str]:
    raw = files(_BACKENDS_PKG).joinpath(f"{backend.value}.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    return dict(data.get("hints", {}))


def render_footer(rule_key: str, backend: Backend, context: dict[str, Any]) -> Markup:
    hints = _load_hints(backend)
    if rule_key not in hints:
        raise KeyError(f"no hint defined for rule {rule_key!r} on backend {backend.value!r}")
    hint = render_string(hints[rule_key], context)
    template = files(_TEMPLATES_PKG).joinpath("footer.md.j2").read_text(encoding="utf-8")
    footer = template.replace("{{ hint }}", hint)
    # Return as Markup so subsequent render_string calls won't escape it.
    return Markup(footer)
