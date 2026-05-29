---
name: push
description: Push the current branch, then continuously manage its PR — wait for readiness and render the CI/Sonar/threads delta when a PR exists, or point at `pr open` when one doesn't. One command for the "push and watch" loop.
type: command
---

# `devex push` — push, then manage the PR

`devex push` turns a `git push` into continuous PR management. It is the single
command an agent runs after committing: it pushes, then either waits on and
reports the open PR, or tells the agent to open one.

```text
devex push --agent <backend> [--max-wait SECS]
```

## What it does

1. **Push.** Runs exactly `git push` of the current branch — **push-only**: it
   never stages, commits, rebases, merges, or touches branches. A failed push
   surfaces as a non-zero exit with the `git` error on stderr.
2. **Detect.** Checks whether the current branch already has an **open PR**.
3. **Route — deterministically on `(current branch, PR-exists)` only:**
   - **PR exists** → enter the *same* readiness wait a fresh PR gets and render
     the unified briefing (CI checks, SonarCloud quality gate + new issues +
     `TO_REVIEW` hotspots, deploy-preview URL, comments, the review-thread
     tally, reviewer readiness) — all in **one invocation**. This reuses the
     `devex pr await` machinery verbatim, so the **exit code is gate-aware**:
     **non-zero on quality-gate `ERROR`, unresolved review threads, or failing
     CI**; `0` on a clean PR or a wait timeout. `--max-wait` (default **180s**)
     bounds the poll, exactly like `pr await`/`pr read --wait`.
   - **No open PR** → after the push, print a deterministic notice
     (`no PR on this branch — open one with <prog> pr open`) and exit `0`, with
     **no wait**.

There is no backend auto-detection (the backend arrives via `--agent`) and no
branch auto-detection — the same inputs always pick the same path.

## Why one command

After a push, an agent otherwise has to decide whether a PR exists, then chain
the right `pr` verb. `devex push` collapses that into a single deterministic
step: push, and either get the live PR delta (with a gate-aware exit code you
can branch on) or a clear "open a PR" pointer. The wait + delta is the existing
`pr await` logic reused as-is — `push` owns no gate logic of its own.

## Relationship to `devex pr`

`devex push` is a thin orchestration layer over `devex pr`:

- The managed (open-PR) path delegates entirely to `devex pr await` — same
  readiness loop, same CI + Sonar + thread gate, same exit semantics, same
  trailing `**Next step:**` footer.
- Use `devex pr open` to create the PR the no-PR path points you at; subsequent
  `devex push` runs then take the managed path automatically.

## Side effects

- **Disk / network:** inherits everything `pr await` does on the managed path
  (GitHub via `gh`, the bounded `--max-wait` poll, journal writes under
  `.devex/data/pr/<PR>/`).
- **`git push`:** the new, push-specific side effect — a deliberate carve-out
  from the no-mutation invariant. Push-only; it never stages or commits.

## Prerequisites

- `git` with an upstream tracking branch configured for the current branch
  (so a bare `git push` knows where to go).
- `gh` (GitHub CLI) on PATH and authenticated (`gh auth login`).
- `--agent` flag, or first agent's `backend:` set in `culture.yaml`.

## Per-backend "Next step:" phrasing (`assets/backends/<backend>.yaml`)

Like the `pr` namespace, `push` resolves its footer phrasing from a per-backend
YAML keyed by the agent backend (`claude-code`, `codex`, `copilot`, `acp`).
The file is loaded via the importlib.resources Traversable API from
`devex.commands.push.assets.backends`. **It is optional**: when the file is
absent or a key is missing, `push` falls back to generic, backend-agnostic
phrasing, so the command works with no yaml present.

Schema — a top-level `hints:` map of Jinja templates (rendered with the shared
renderer, so `{{ prog }}` is always available):

```yaml
hints:
  # Footer shown after the push when the current branch has NO open PR.
  # Should point the agent at `{{ prog }} pr open`. Required key (has a
  # generic fallback if omitted).
  no_pr_notice: "no PR on this branch — open one with `{{ prog }} pr open`."

  # Optional trailing hint appended to the managed (wait + delta) briefing.
  # The managed path already carries the `pr await` footer, so this defaults
  # to empty (no extra line). Set a non-empty string only to add push-specific
  # framing after the reused `pr await` output.
  post_wait: ""
```

Available template variables: `{{ prog }}` (the invoked CLI name, `devex` or
`agex`). Keep templates one line; the footer wrapper supplies surrounding
markdown.

> **Note:** the `assets/backends/*.yaml` files are authored separately (the
> backend-phrasing wave). This skill-folder ships only the `__init__.py` package
> marker for that directory; the generic fallback covers their absence.
