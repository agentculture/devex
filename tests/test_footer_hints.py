"""Hint-coverage and hint-form guard tests for the cross-command footer system.

This file (together with ``tests/core/test_footer.py``, aka the "footer
guarantee" sibling file) forms the CI guard for the footer guarantee:

- **test_all_backends_define_same_rule_keys** (h2, c7): walks every command
  that has an ``assets/backends/`` directory, discovers all four per-backend
  YAML files, and asserts that all backends define *identical* sets of
  ``hints:`` keys.  Adding a command or rule_key without updating every backend
  YAML causes this test to FAIL loudly.

- **test_render_footer_succeeds_for_every_triple** (h2, c7): calls
  ``render_footer`` for each (command, backend, rule_key) triple and asserts no
  ``KeyError`` or ``UndefinedError`` is raised.  This catches a missing hint or
  a template variable that was never injected.

- **test_neutral_covers_explain_and_doctor_keys** (h2, c7): asserts that every
  ``explain_*`` / ``doctor_*`` rule_key found in the per-backend explain/doctor
  YAMLs is *also* present in ``devex/core/assets/backends/neutral.yaml``, and
  that ``render_neutral_footer`` succeeds for each neutral key.

- **test_hint_form_is_agent_imperative** (h6, c2): checks every hint string
  (per-backend + neutral) against a heuristic that distinguishes agent-facing
  imperatives from human prose.  See the in-test comment for the exact
  heuristic definition.

All four tests run under the standard ``uv run pytest`` CI job automatically
because pytest collects every ``tests/test_*.py`` file.  No CI YAML edits are
required.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Generator

import pytest
import yaml

from devex.core.backend import Backend
from devex.core.footer import render_footer, render_neutral_footer

# ---------------------------------------------------------------------------
# Helpers — local to this file (no shared conftest; t8 sibling runs in parallel)
# ---------------------------------------------------------------------------

_SRC_COMMANDS = Path(__file__).parent.parent / "src" / "devex" / "commands"
_NEUTRAL_YAML = (
    Path(__file__).parent.parent / "src" / "devex" / "core" / "assets" / "backends" / "neutral.yaml"
)

_ALL_BACKENDS: list[Backend] = list(Backend)
_BACKEND_VALUES: list[str] = [b.value for b in _ALL_BACKENDS]

# Permissive context dict that satisfies every Jinja template variable used
# across all current hints (excluding ``{{ prog }}``, which render_string
# auto-injects from sys.argv[0]).
_FULL_CONTEXT: dict = {
    "backend": "claude-code",
    "elapsed": "42",
    "fail_count": 3,
    "pr": 99,
    "reviewers": "@alice, @bob",
    "topic": "pr",
    "violation_count": 5,
}


_KNOWN_BACKENDS = ("acp", "claude-code", "codex", "copilot")


def _commands_with_backends() -> list[str]:
    """Command names whose assets/backends/ holds real per-backend hint YAMLs.

    Requires at least one known ``<backend>.yaml`` to be present, so stray dirs
    (e.g. a leftover ``__pycache__``-only command tree from another branch) are
    ignored rather than crashing discovery.
    """
    out: list[str] = []
    for d in _SRC_COMMANDS.iterdir():
        if not d.is_dir() or d.name.startswith("__"):
            continue
        bdir = d / "assets" / "backends"
        if bdir.is_dir() and any((bdir / f"{b}.yaml").is_file() for b in _KNOWN_BACKENDS):
            out.append(d.name)
    return sorted(out)


def _load_hints(cmd: str, backend_value: str) -> dict[str, str]:
    yaml_path = _SRC_COMMANDS / cmd / "assets" / "backends" / f"{backend_value}.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    return dict(data.get("hints") or {})


def _load_neutral_hints() -> dict[str, str]:
    data = yaml.safe_load(_NEUTRAL_YAML.read_text(encoding="utf-8")) or {}
    return dict(data.get("hints") or {})


def _all_triples() -> Generator[tuple[str, Backend, str], None, None]:
    """Yield (command, Backend, rule_key) for every triple discovered."""
    for cmd in _commands_with_backends():
        for backend in _ALL_BACKENDS:
            hints = _load_hints(cmd, backend.value)
            for rule_key in hints:
                yield cmd, backend, rule_key


# ---------------------------------------------------------------------------
# Test 1 — All backends define the same rule_key set per command (h2, c7)
# ---------------------------------------------------------------------------


def test_all_backends_define_same_rule_keys() -> None:
    """All 4 backends must expose identical hint keys for every command.

    This is the primary structural guard: if someone adds a rule_key to one
    backend's YAML but forgets the other three, this test fails loudly.
    """
    commands = _commands_with_backends()
    assert commands, "No commands with backends/ directories found — discovery broken."

    mismatches: list[str] = []
    for cmd in commands:
        key_sets: dict[str, frozenset[str]] = {}
        for bv in _BACKEND_VALUES:
            key_sets[bv] = frozenset(_load_hints(cmd, bv).keys())

        # All sets must be equal
        reference_backend = _BACKEND_VALUES[0]
        reference_keys = key_sets[reference_backend]
        for bv, keys in key_sets.items():
            if keys != reference_keys:
                extra = keys - reference_keys
                missing = reference_keys - keys
                mismatches.append(
                    f"  command={cmd!r}: backend {bv!r} vs {reference_backend!r} — "
                    f"extra={sorted(extra)}, missing={sorted(missing)}"
                )

    assert not mismatches, (
        "Backend hint-key sets are NOT in sync for the following commands:\n"
        + "\n".join(mismatches)
        + "\n\nFix: add the missing rule_keys to the affected backends/*.yaml files."
    )


# ---------------------------------------------------------------------------
# Test 2 — render_footer succeeds for every (command, backend, rule_key) triple
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd,backend,rule_key",
    [
        (cmd, backend, rule_key)
        for cmd in _commands_with_backends()
        for backend in _ALL_BACKENDS
        for rule_key in _load_hints(cmd, backend.value)
    ],
    ids=lambda x: x if isinstance(x, str) else getattr(x, "value", str(x)),
)
def test_render_footer_succeeds_for_every_triple(cmd: str, backend: Backend, rule_key: str) -> None:
    """render_footer must not raise for any (command, backend, rule_key) triple.

    A missing hint raises ``KeyError``; an unsatisfied Jinja variable raises
    ``UndefinedError``.  Both are caught here as hard failures.

    The ``_FULL_CONTEXT`` dict is intentionally permissive — it carries every
    context variable that any hint currently references so that template
    rendering succeeds even when the test doesn't know which subset a
    particular hint needs.
    """
    backends_pkg = f"devex.commands.{cmd}.assets.backends"
    # Should NOT raise
    result = render_footer(rule_key, backend, _FULL_CONTEXT, backends_pkg)
    assert "**Next step:**" in result, (
        f"render_footer({rule_key!r}, {backend.value!r}) returned output "
        f"without '**Next step:**' marker: {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — neutral.yaml covers every explain_* / doctor_* key (h2, c7)
# ---------------------------------------------------------------------------


def test_neutral_covers_explain_and_doctor_keys() -> None:
    """Every explain_* and doctor_* key in per-backend YAMLs must exist in neutral.yaml.

    ``devex explain`` and ``devex doctor`` are invoked both with and without
    ``--agent``; the neutral path must mirror every rule key the backend path
    defines so callers can freely use either footer entrypoint.
    """
    neutral_hints = _load_neutral_hints()

    per_backend_keys: set[str] = set()
    for cmd_name in ("explain", "doctor"):
        for bv in _BACKEND_VALUES:
            per_backend_keys.update(_load_hints(cmd_name, bv).keys())

    missing = sorted(per_backend_keys - set(neutral_hints.keys()))
    assert not missing, (
        "The following explain_*/doctor_* rule_keys are defined in per-backend YAMLs "
        "but MISSING from neutral.yaml:\n"
        + "\n".join(f"  {k}" for k in missing)
        + "\n\nFix: add them to src/devex/core/assets/backends/neutral.yaml."
    )


@pytest.mark.parametrize(
    "rule_key",
    sorted(_load_neutral_hints().keys()),
)
def test_render_neutral_footer_succeeds_for_every_key(rule_key: str) -> None:
    """render_neutral_footer must not raise for any key in neutral.yaml."""
    result = render_neutral_footer(rule_key, _FULL_CONTEXT)
    assert "**Next step:**" in result, (
        f"render_neutral_footer({rule_key!r}) returned output "
        f"without '**Next step:**' marker: {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Hint-form lint: every hint is an agent-imperative (h6, c2)
# ---------------------------------------------------------------------------

# Heuristic rationale (acknowledged as heuristic — may need future tuning):
#
# A hint is considered a valid agent-imperative if it satisfies AT LEAST ONE of:
#
#   (A) Contains a backtick-wrapped command reference (`` ` `` ... `` ` ``).
#       This covers the vast majority of hints: e.g. "`{{ prog }} pr lint`".
#
#   (B) Contains a Jinja template variable (``{{ ... }}``).
#       This covers hints like "PR #{{ pr }} is ready — wait for human merge."
#       which reference runtime context and are clearly agent-directed.
#
#   (C) The first non-whitespace word (lowercased, punctuation stripped) is one
#       of a fixed set of imperative English verbs that denote an agent action:
#       {fix, run, push, commit, wait, triage, apply, pick, act, rerun, re-run,
#        resubmit, post, poll, setup}.
#       This covers the handful of prose-style hints such as "Fix CI before…",
#       "Wait for human merge.", "Triage each sibling…".
#
# The heuristic rejects empty strings and hints that read as passive human-
# facing prose with no imperative verb and no command reference.
#
# NOTE: do NOT tighten the heuristic without first running the full suite to
# confirm every existing hint still passes.  If a new hint genuinely looks like
# human prose but is intentional, add its first word to the IMPERATIVE_VERBS
# set below, and document why.

_IMPERATIVE_VERBS: frozenset[str] = frozenset(
    {
        "act",
        "apply",
        "commit",
        "fix",
        "pick",
        "poll",
        "post",
        "push",
        "re-run",
        "rerun",
        "resubmit",
        "run",
        "setup",
        "triage",
        "wait",
    }
)

_BACKTICK_RE = re.compile(r"`[^`]+`")
_TEMPLATE_VAR_RE = re.compile(r"\{\{[^}]+\}\}")


def _hint_is_agent_imperative(hint: str) -> bool:
    """Return True iff ``hint`` passes the agent-imperative heuristic."""
    if not hint.strip():
        return False
    if _BACKTICK_RE.search(hint):
        return True
    if _TEMPLATE_VAR_RE.search(hint):
        return True
    first_word = re.split(r"\W+", hint.strip())[0].lower()
    return first_word in _IMPERATIVE_VERBS


def _all_hint_strings() -> Generator[tuple[str, str, str], None, None]:
    """Yield (source_label, rule_key, hint_string) for every hint across all sources."""
    for cmd in _commands_with_backends():
        for bv in _BACKEND_VALUES:
            hints = _load_hints(cmd, bv)
            for rule_key, hint_str in hints.items():
                yield f"{cmd}/{bv}.yaml", rule_key, hint_str

    for rule_key, hint_str in _load_neutral_hints().items():
        yield "neutral.yaml", rule_key, hint_str


@pytest.mark.parametrize(
    "source,rule_key,hint_str",
    list(_all_hint_strings()),
    ids=lambda x: x if isinstance(x, str) else str(x),
)
def test_hint_form_is_agent_imperative(source: str, rule_key: str, hint_str: str) -> None:
    """Every hint string must be an agent-facing imperative naming a devex action.

    See the module-level comment above ``_IMPERATIVE_VERBS`` for the full
    heuristic definition.  If this test fails for a newly added hint, either:

    - Rewrite the hint to start with an imperative verb or contain a command
      reference (preferred), OR
    - Add the hint's first word to ``_IMPERATIVE_VERBS`` and document why.
    """
    assert _hint_is_agent_imperative(hint_str), (
        f"Hint in {source} [{rule_key!r}] does not look like an agent-imperative.\n"
        f"  Hint: {hint_str!r}\n"
        f"  Fix: start with an imperative verb (e.g. 'Run', 'Fix', 'Wait') or "
        f"include a backtick-wrapped command reference, or add the first word to "
        f"_IMPERATIVE_VERBS in tests/test_footer_hints.py."
    )
