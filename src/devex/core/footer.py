"""Render the trailing 'Next step:' footer shared by command namespaces.

This is the command-agnostic footer machinery.  Two entry points are provided:

:func:`render_footer`
    For commands that are always invoked with ``--agent <backend>``.  A caller
    supplies *where* the per-backend hints live (``backends_pkg``, a dotted
    package name resolvable via :func:`importlib.resources.files`) plus the
    rule key, backend and template context; this function loads
    ``<backend>.yaml`` from that package, renders the hint string through
    :func:`devex.core.render.render_string`, and wraps it in the
    core-shipped ``footer.md.j2`` template.

:func:`render_neutral_footer`
    For commands that may be invoked *without* ``--agent`` (e.g. ``devex
    explain``, ``devex doctor``).  Resolves hints from the shared
    ``devex.core.assets.backends.neutral`` YAML instead of a per-backend
    file; otherwise produces an identical ``---\\n**Next step:** …`` block.

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
_NEUTRAL_BACKENDS_PKG = "devex.core.assets.backends"
_NEUTRAL_YAML = "neutral.yaml"


def _load_hints(backends_pkg: str, backend: Backend) -> dict[str, str]:
    raw = files(backends_pkg).joinpath(f"{backend.value}.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    return dict(data.get("hints", {}))


def _load_neutral_hints() -> dict[str, str]:
    raw = files(_NEUTRAL_BACKENDS_PKG).joinpath(_NEUTRAL_YAML).read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    return dict(data.get("hints", {}))


def _render_hint_to_footer(hint_template: str, context: dict[str, Any]) -> Markup:
    """Render *hint_template* through Jinja and wrap in the footer block."""
    hint = render_string(hint_template, context)
    template = files(_TEMPLATES_PKG).joinpath("footer.md.j2").read_text(encoding="utf-8")
    footer = template.replace("{{ hint }}", hint)
    # Return as Markup so subsequent render_string calls won't escape it.
    return Markup(footer)


def render_footer(
    rule_key: str, backend: Backend, context: dict[str, Any], backends_pkg: str
) -> Markup:
    """Render a backend-specific 'Next step:' footer.

    Loads ``<backend>.yaml`` from *backends_pkg*, looks up *rule_key* in its
    ``hints:`` dict, renders the Jinja template with *context*, and returns
    the footer block as :class:`~markupsafe.Markup`.

    Raises :class:`KeyError` if *rule_key* is not present in the loaded hints.
    """
    hints = _load_hints(backends_pkg, backend)
    if rule_key not in hints:
        raise KeyError(f"no hint defined for rule {rule_key!r} on backend {backend.value!r}")
    return _render_hint_to_footer(hints[rule_key], context)


def render_neutral_footer(rule_key: str, context: dict[str, Any]) -> Markup:
    """Render a backend-agnostic 'Next step:' footer from the neutral hints source.

    Resolves *rule_key* from ``devex/core/assets/backends/neutral.yaml``
    (the shared, backend-independent hint store).  The rendered block is
    structurally identical to the output of :func:`render_footer`:

        ---
        **Next step:** <rendered hint>

    Use this for commands that are invoked *without* ``--agent`` (e.g.
    ``devex explain``, ``devex doctor``).

    Raises :class:`KeyError` if *rule_key* is not present in ``neutral.yaml``.
    """
    hints = _load_neutral_hints()
    if rule_key not in hints:
        raise KeyError(f"no hint defined for neutral rule {rule_key!r}")
    return _render_hint_to_footer(hints[rule_key], context)
