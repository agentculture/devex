---
name: cicd
description: >
  agex-cli's CI/CD lane — a thin layer over its own `agex pr` namespace.
  Delegates lint / open / read / reply / delta / await straight to
  `agex pr`. Use when: creating PRs here, handling review feedback,
  polling CI/Sonar status, or the user says "create PR", "review
  comments", "address feedback", "resolve threads". Vendored from
  steward 0.18.1 (adapted divergence: agex-cli owns `agex pr`, so the
  steward `status`/`await` shell extensions and the `_resolve-nick.sh` /
  `pr-reply.sh` / `portability-lint.sh` helpers are dropped in favor of
  the native verbs; the only file is `workflow.sh`, a typing-saver.
  Remaining `pr-status.sh` extras tracked in agex-cli#52). Renamed from
  `pr-review` upstream in steward 0.7.0; rebased on `agex pr` in 0.12.0.
type: command
---

# CI/CD — agex-cli edition

agex-cli is **itself the upstream** of `agex pr` — the five core
PR-lifecycle verbs (`lint`, `open`, `read`, `reply`, `delta`) plus the
`await` combo verb all live in this repo's `commands/pr/`. So unlike
other consumers of steward's `cicd` skill, there is nothing here to
*wrap*: this skill is just the workflow/triage framing on top of the
native verbs, dogfooded against the local build.

What steward's copy carries as shell extensions (`status` / `await`,
backed by `pr-status.sh`) is already native here:

- `agex pr await` — the "wake me when this PR is triage-able" verb:
  readiness poll → CI checks → SonarCloud gate → briefing, with a
  non-zero exit on Sonar `ERROR`, unresolved threads, or CI failure.
  `--max-wait N` bounds the poll.
- `agex pr read` — one-shot briefing: CI checks, SonarCloud quality
  gate + new issues, Qodo findings, all comments, and a per-backend
  "Next step:" footer. `--wait N` polls for reviewer readiness.

The last bits of steward's `pr-status.sh` that aren't native yet —
SonarCloud hotspots, the deploy-preview URL, and an explicit
resolved/unresolved thread tally in the briefing — are tracked as a
feature ask in [agex-cli#52](https://github.com/agentculture/agex-cli/issues/52)
rather than re-vendored as bash. When they land, this skill needs no
change.

## Prerequisites

`agex` (this repo), `gh` (GitHub CLI), `jq`, `bash`, `python3`.

This repo *is* `agex-cli`, so run the local build rather than a
published wheel:

```bash
uv run agex pr read --agent claude <PR>     # or:
uv pip install -e .   # then `agex` is on PATH
```

SonarCloud project key is derived as `<owner>_<repo>`; override with the
`SONAR_PROJECT_KEY` env var (or `[pr].sonar_project_key` in
`.agex/config.toml`) for non-standard naming.

## How to run

`scripts/workflow.sh` is a typing-saver — every verb forwards to
`agex pr <verb>`. You can call `agex pr <verb>` directly just as well.

| Command | What it does |
|---------|--------------|
| `workflow.sh lint` | `agex pr lint --exit-on-violation` — portability + alignment-trigger check on the working diff. |
| `workflow.sh open [gh-flags]` | `agex pr open --delayed-read`. Creates the PR, then polls for an initial briefing. `--title TITLE` required; body via `--body-file PATH` or stdin. |
| `workflow.sh read [PR] [--wait N]` | `agex pr read`. One-shot briefing (CI, SonarCloud gate + new issues, Qodo findings, all comments, next-step footer). `--wait N` polls up to N seconds for required reviewers. |
| `workflow.sh reply <PR>` | `agex pr reply <PR>` — batch JSONL replies (stdin) + thread resolve. agex auto-signs from `culture.yaml`. |
| `workflow.sh delta` | `agex pr delta` — sibling alignment dump. |
| `workflow.sh await [PR] [--max-wait N]` | `agex pr await`. Readiness poll → CI → Sonar gate → briefing. Exits non-zero on Sonar `ERROR`, unresolved threads, or CI failure. The single command to run after pushing a fix. |
| `workflow.sh help` | Print the verb list. |

`workflow.sh` does **not** inject a default `--agent` (design invariant #3
forbids backend defaulting). It lets `agex` resolve the backend from this
repo's `culture.yaml` (`backend: claude`), failing fast if neither that nor
a flag is present. Set `AGEX_PR_AGENT` to force a backend (`codex` /
`copilot` / `acp`).

## Long waits (background polling)

`agex pr await --max-wait N` (and `agex pr read --wait N`) poll
in-session for up to N seconds. The Anthropic prompt cache has a
5-minute TTL; sleeping past it burns context on every cache miss. Two
ways to drive the wait:

- **Synchronous** — `workflow.sh await <PR>` right after
  `workflow.sh open`. Fine when readiness is expected within ~5 minutes.
- **Asynchronous** — for longer waits, run `agex pr await <PR> --max-wait
  NNN` inside a background subagent (Agent tool, `run_in_background:
  true`) so the main session only pays the cache cost when readiness
  fires. The subagent's only job is to invoke the verb and echo its
  headline back; the parent triages when the notification arrives.

## Conventions

`agex pr` emits a **"Next step:"** footer at the end of every command
naming the right next verb — follow that rather than memorizing an order.

Branch naming: `fix/<desc>`, `feat/<desc>`, `docs/<desc>`,
`skill/<name>`. PR / comment signature: `- <nick> (Claude)`, where
`<nick>` is resolved by `agex` from this repo's `culture.yaml` (first
agent's `suffix` — `agex-cli` here), falling back to the git-repo
basename. agex auto-appends the signature on `pr open` and `pr reply`
only when the body isn't already signed. For a hand-typed `gh` post the
scripts don't author, sign `- agex-cli (Claude)` explicitly.

## Finishing a branch

When implementation is complete and tests pass, go straight to
`workflow.sh open` (push + open the PR). Do **not** stop to present a
*merge / PR / keep / discard* menu — in AgentCulture the standing default
is **always "push and create a Pull Request."** This overrides the
Superpowers `finishing-a-development-branch` menu, which otherwise pauses
the flow. Merge-locally, keep-as-is, and discard happen only on explicit
user request.

Before opening, **bump the version in `pyproject.toml`** (`/version-bump
patch|minor|major`, which also adds a `CHANGELOG.md` section) — CI's
`version-check` job fails the PR otherwise.

## Triage rules

For every comment, decide **FIX** or **PUSHBACK** with reasoning.

Default to **FIX** for: portability complaints, test or doc requests,
style nits aligned with workspace conventions.

Default to **PUSHBACK** for: architecture opinions that conflict with the
workspace `CLAUDE.md` or the design invariants in
`docs/superpowers/specs/`; greenfield false-positives (defer to a later
PR, don't refuse).

### Alignment-delta rule

If the PR touches `CLAUDE.md`, `culture.yaml`, or anything under
`.claude/skills/`, run `workflow.sh delta` **before** declaring FIX or
PUSHBACK on each comment. Note any sibling that needs a follow-up PR and
mention it in your reply.

## Stack-specific steps

agex-cli is not greenfield — run the real stack before opening:

```bash
uv run pytest                                          # full suite (pytest-xdist)
/version-bump patch|minor|major                        # bump pyproject + CHANGELOG
markdownlint-cli2 "$(git diff --name-only HEAD '*.md')" # if any .md changed
```

## Reply etiquette

Every comment must get a reply — no silent fixes. `agex pr reply`
includes thread-resolve by default. Reference the review-comment IDs in
the fix-up commit message. SonarCloud is configured as Automatic Analysis
on the repo; trust `agex pr read`'s Sonar section for the gate.
