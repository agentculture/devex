"""`devex push` — push the current branch, then manage its PR.

One command that turns a ``git push`` into continuous PR management:

1. **Push.** ``git push`` the current branch (via :func:`devex.core.github.git_push`)
   — push-only: never stages, commits, rebases, or merges.  A failed push
   raises ``RuntimeError`` so the CLI surfaces a non-zero exit with the error
   on stderr.
2. **Detect.** Ask whether the current branch already has an open PR (via
   :func:`devex.core.github.current_branch_pr`, which returns the number or
   ``None`` and never raises on the no-PR case).
3. **Route deterministically on** ``(current branch, PR-exists)`` **only** — no
   backend auto-detection (the backend arrives via ``agent``) and no branch
   auto-detection:

   * **PR exists** → enter the *same* readiness wait a fresh PR gets and render
     the CI / SonarCloud / review-thread briefing, in ONE invocation, by
     delegating to :func:`devex.commands.pr.scripts.await_.run` (the gate-aware
     ``pr await``).  Its ``(stdout, exit_code, stderr)`` — including the
     gate-aware exit code (non-zero on quality-gate ERROR, unresolved review
     threads, or failing CI) — is passed straight through.  We do not invent a
     verdict of our own.
   * **No open PR** → after the push, print a deterministic notice pointing at
     ``<prog> pr open`` and exit 0, with NO wait.

The managed-path wait + delta is the existing ``pr await`` machinery reused
verbatim — this module owns no gate logic.  The only push-specific phrasing is
the no-PR notice footer, which follows the same per-backend ``hints:`` pattern
as the ``pr`` namespace (graceful generic fallback when the backend yaml is
absent).
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import yaml

from devex.commands.pr.scripts import await_ as _await_script
from devex.core import github
from devex.core.backend import Backend, resolve_backend
from devex.core.prog import prog_name
from devex.core.render import render_string

_BACKENDS_PKG = "devex.commands.push.assets.backends"

# Generic, backend-agnostic phrasing used whenever the per-backend yaml is
# absent (it is, until task t5 authors it) or is missing the requested key.
# ``{{ prog }}`` is injected by the shared renderer, so these stay
# invocation-aware (devex / agex) just like every rendered template.
_FALLBACK_HINTS: dict[str, str] = {
    # No open PR on the current branch after the push.
    "no_pr_notice": "no PR on this branch — open one with `{{ prog }} pr open`.",
    # Reserved trailing hint for the managed (wait+delta) path.  Empty by
    # default so the reused `pr await` footer stands alone; task t5 may opt in.
    "post_wait": "",
}


def _load_hints(backend: Backend) -> dict[str, str]:
    """Return the ``hints:`` map from the per-backend push yaml, or ``{}``.

    Uses the importlib.resources Traversable API (zipapp/PEX safe) — never
    ``Path(str(files(...)))``.  A missing file, unreadable file, or malformed
    YAML degrades to an empty map so the caller falls back to the generic
    phrasing rather than crashing.  The backend yaml files are authored by
    task t5; this code must work without them today.
    """
    resource = files(_BACKENDS_PKG).joinpath(f"{backend.value}.yaml")
    if not resource.is_file():
        return {}
    try:
        raw = resource.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except (OSError, UnicodeError, yaml.YAMLError):
        # UnicodeError covers a non-UTF8 / corrupted file (UnicodeDecodeError);
        # OSError an unreadable one; YAMLError a malformed one. All degrade to
        # the generic fallback rather than crashing `devex push`.
        return {}
    if not isinstance(data, dict):
        # A valid YAML scalar/list (e.g. a top-level list) parses fine but has
        # no `.get` — guard so it falls back instead of raising AttributeError.
        return {}
    hints = data.get("hints", {})
    return dict(hints) if isinstance(hints, dict) else {}


def _hint(backend: Backend, key: str) -> str:
    """Render the per-backend hint for ``key``, falling back to the generic one.

    The backend yaml wins when it defines ``key``; otherwise the generic
    :data:`_FALLBACK_HINTS` template is used.  Both are rendered through the
    shared renderer so ``{{ prog }}`` (and any future vars) resolve.
    """
    hints = _load_hints(backend)
    template = hints.get(key, _FALLBACK_HINTS.get(key, ""))
    if not template:
        return ""
    return render_string(template, {})


def run(
    agent: str | None,
    max_wait: int = 180,
    project_dir: Path | None = None,
) -> tuple[str, int, str]:
    """Push the current branch, then conditionally wait on / render its PR.

    Returns ``(stdout, exit_code, stderr)`` — the same convention as the ``pr``
    scripts.  On the managed (open-PR) path the tuple is the reused
    ``pr await`` result, including its gate-aware exit code.  On the no-PR path
    it is the deterministic notice with exit 0.  A failed push raises
    ``RuntimeError`` (the CLI maps it to a non-zero exit + stderr).
    """
    if project_dir is None:
        project_dir = Path.cwd()

    # Resolve the backend up front (deterministic; --agent or culture.yaml).
    # A bad backend raises ValueError *before* the push side effect, matching
    # how the `pr` verbs fail fast.
    backend = resolve_backend(agent, project_dir)

    # 1. Push first — push-only, never stage/commit.  Propagate failure.
    github.git_push()

    # 2. Detect an open PR on the current branch (never raises on no-PR).
    pr = github.current_branch_pr()

    # 3. Deterministic routing on (current branch, PR-exists).
    if pr is None:
        # No open PR → notice, no wait, exit 0.  The notice is always rendered
        # through `_hint` (per-backend yaml or the generic fallback), which
        # routes through the shared renderer so `{{ prog }}` reflects the
        # invoked name.  If a backend yaml ever blanks `no_pr_notice`, fall back
        # to the same generic phrasing built directly with `prog_name()` so the
        # notice text never goes empty.
        hint = _hint(backend, "no_pr_notice")
        if not hint:
            hint = f"no PR on this branch — open one with `{prog_name()} pr open`."
        return f"{hint}\n", 0, ""

    # PR exists → reuse the existing readiness wait + CI/Sonar/threads briefing,
    # in ONE invocation, and pass the gate-aware exit code straight through.
    stdout, exit_code, stderr = _await_script.run(
        agent=agent, project_dir=project_dir, pr=pr, max_wait=max_wait
    )

    # Optional push-specific trailing hint (empty by default → no double footer).
    post = _hint(backend, "post_wait")
    if post:
        sep = "" if stdout.endswith("\n") else "\n"
        stdout = f"{stdout}{sep}\n{post}\n"

    return stdout, exit_code, stderr
