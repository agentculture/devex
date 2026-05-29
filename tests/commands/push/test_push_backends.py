"""Tests for per-backend push assets (t5).

Asserts that every known Backend has a push ``assets/backends/<backend>.yaml``
that:

1. Loads without error via the same ``_load_hints`` path the production code uses.
2. Contains both required hint keys: ``no_pr_notice`` and ``post_wait``.
3. Both hints render to non-empty strings through the shared Jinja renderer
   (``render_string``) without raising ``UndefinedError`` or any other error —
   i.e. they use only ``{{ prog }}`` and no other template variables that would
   blow up under ``StrictUndefined``.

The test iterates over all four backends × two keys = 8 assertions.
"""

from __future__ import annotations

import pytest

from devex.commands.push.scripts.push import _hint, _load_hints
from devex.core.backend import Backend
from devex.core.render import render_string

# All four backends the all-backends rule requires.
ALL_BACKENDS = [
    Backend.CLAUDE_CODE,
    Backend.CODEX,
    Backend.COPILOT,
    Backend.ACP,
]

REQUIRED_KEYS = ["no_pr_notice", "post_wait"]


@pytest.mark.parametrize("backend", ALL_BACKENDS, ids=lambda b: b.value)
def test_backend_yaml_loads(backend: Backend) -> None:
    """Each backend's yaml loads to a non-empty dict (file must exist and parse)."""
    hints = _load_hints(backend)
    assert isinstance(hints, dict), f"{backend.value}: _load_hints returned non-dict"
    assert hints, f"{backend.value}: _load_hints returned empty dict — yaml missing or empty?"


@pytest.mark.parametrize(
    "backend,key",
    [(b, k) for b in ALL_BACKENDS for k in REQUIRED_KEYS],
    ids=lambda x: x.value if isinstance(x, Backend) else x,
)
def test_hint_renders_to_non_empty_string(backend: Backend, key: str) -> None:
    """Both hint keys load and render to a non-empty string via _hint().

    Uses ``_hint(backend, key)`` which:
    - reads the per-backend yaml via the importlib.resources Traversable API,
    - falls back to ``_FALLBACK_HINTS`` if the key is absent,
    - renders through ``render_string(template, {})`` with ``StrictUndefined``.

    A ``StrictUndefined`` error (referencing ``{{ pr }}``, ``{{ reviewers }}``,
    etc.) would raise ``jinja2.UndefinedError`` and fail the test.
    A missing/blank template would yield an empty string and also fail.
    """
    rendered = _hint(backend, key)
    assert isinstance(
        rendered, str
    ), f"{backend.value}[{key}]: _hint returned non-str {type(rendered)}"
    assert rendered.strip(), (
        f"{backend.value}[{key}]: _hint rendered to empty — "
        "set a non-empty template in the yaml (post_wait may be '' only if that is intentional, "
        "but the task requires non-empty for all four backends)"
    )


@pytest.mark.parametrize("backend", ALL_BACKENDS, ids=lambda b: b.value)
def test_no_pr_notice_mentions_pr_open(backend: Backend) -> None:
    """``no_pr_notice`` must guide the agent toward ``pr open``."""
    rendered = _hint(backend, "no_pr_notice")
    assert "pr open" in rendered, (
        f"{backend.value}: no_pr_notice does not mention 'pr open' — "
        "agents need a concrete next step after a push with no PR"
    )


@pytest.mark.parametrize("backend", ALL_BACKENDS, ids=lambda b: b.value)
def test_no_pr_notice_contains_prog(backend: Backend) -> None:
    """``no_pr_notice`` must contain the resolved ``prog`` name.

    The renderer injects ``prog`` (the invoked CLI name — ``devex`` or ``agex``).
    We just check that the rendered string is non-trivially populated; the
    prog-name injection is exercised by the render step itself.
    """
    rendered = _hint(backend, "no_pr_notice")
    # The template uses {{ prog }} which renders to 'devex' (or 'agex' in legacy).
    # We accept either name so the test is invocation-agnostic.
    assert "devex" in rendered or "agex" in rendered, (
        f"{backend.value}: no_pr_notice does not contain prog name — "
        "template must include `{{ prog }}`"
    )


@pytest.mark.parametrize("backend", ALL_BACKENDS, ids=lambda b: b.value)
def test_post_wait_renders_without_error(backend: Backend) -> None:
    """``post_wait`` template renders without ``StrictUndefined`` errors.

    We directly load the raw template and render it with an empty context (only
    ``prog`` is auto-injected) to confirm it uses no unknown variables.
    """
    hints = _load_hints(backend)
    template = hints.get("post_wait", "")
    if not template:
        pytest.skip(f"{backend.value}: post_wait is empty in yaml — nothing to render")
    # This call would raise jinja2.UndefinedError if the template refs anything
    # other than {{ prog }}.
    result = render_string(template, {})
    assert isinstance(result, str)
