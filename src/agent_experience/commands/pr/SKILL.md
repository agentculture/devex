---
name: pr
description: GitHub PR lifecycle commands for agents — lint, open, read, reply, review, await, delta. Each command ends with a deterministic "Next step:" footer so the agent never has to guess what to chain.
type: command
---

# `agex pr` — PR lifecycle for agents

Seven verbs, in roughly the order an agent uses them on a PR:

| Verb | Purpose |
|---|---|
| `agex pr lint` | Portability + alignment-trigger lint on the working diff. |
| `agex pr open --title T [--body-file F] [--draft] [--delayed-read]` | `gh pr create` with auto-signed body; with `--delayed-read` chains to `read --wait 180`. |
| `agex pr read [<PR>] [--wait SECS]` | Unified briefing: CI checks, SonarCloud quality gate + new issues + `TO_REVIEW` security hotspots, Cloudflare Pages deploy-preview URL, all comments, a Total/Resolved/Unresolved review-thread tally, and reviewer readiness. With `--wait`, polls until required reviewers are ready or timeout. Always exits 0. |
| `agex pr reply <PR>` | Read JSONL replies on stdin, post each, resolve threads. |
| `agex pr review [<PR>]` | Post the Qodo agentic-review trigger (`/agentic_review`) on a PR. Re-triggers on an already-open PR; `pr open` posts it automatically for a new non-draft PR. |
| `agex pr await [<PR>] [--max-wait SECS]` | "Wake me when this is triage-able" — polls readiness, runs CI + Sonar gate, dumps briefing. **Exits 1 on quality-gate `ERROR`, unresolved threads, or failing CI checks**, 0 on clean state or timeout. Default `--max-wait 1800` (30 min). |
| `agex pr delta` | Dump sibling-project `CLAUDE.md` heads + `culture.yaml` for alignment review. |

`pr read --wait` and `pr await` share the same readiness-polling loop; the
difference is the exit code. Use `read` when you want the briefing
unconditionally; use `await` when you want to **gate** the next step on
PR health (e.g., in scripts that should fail if Sonar errors).

## Readiness and `--wait` semantics

- **`--wait` / `--max-wait` is an upper bound, not a minimum sleep.** It's the
  *maximum* time to poll (60s interval). The loop returns as soon as the
  readiness predicate holds — including **immediately** (`waited=0s`) if it
  already held on entry. When that happens the stderr heartbeat appends
  `(readiness already satisfied on entry; not polling)`, so a fast return on a
  large `--wait` is expected, not a bug.
- **What "ready" means.** `ready=True` when every reviewer in
  `[pr].required_reviewers` (default `["qodo"]`) has posted a non-empty comment.
  This is **review-feedback-present**, *not* merge-ready: it says nothing about
  unresolved review threads, CI checks, or the SonarCloud quality gate. Widen
  the predicate by adding reviewers to `[pr].required_reviewers` in
  `.agex/config.toml`.
- **Need merge-gating?** Use `agex pr await`, which adds the CI + Sonar + thread
  gates on top of the same readiness loop and **exits non-zero** when the PR
  isn't clean.

## Qodo agentic review

When a PR is opened, Qodo runs an agentic code review on demand when it sees a
trigger comment. The current command is **`/agentic_review`**. The legacy
`/improve` command is **deprecated** (Qodo replies with a deprecation banner and
no committed removal date), so agex never posts `/improve`.

- `agex pr open` posts `/agentic_review` **automatically** for a freshly created,
  non-draft PR — out of the box, no flag. Drafts are skipped (not review-ready)
  and already-open PRs are skipped (idempotent re-opens shouldn't spam the
  thread).
- `agex pr review [<PR>]` posts the same trigger on demand — use it to re-trigger
  a review on an existing PR (e.g. after pushing fixes) or to trigger a draft
  once it's ready.

The command string lives in one place (`scripts/review.QODO_REVIEW_TRIGGER`), so
a future Qodo rename is a one-line change for every consumer of `agex pr`.

## SonarCloud project key

`pr read` and `pr await` query the SonarCloud quality gate, new-code issues, and
`TO_REVIEW` security hotspots for the current PR. The project key is resolved in
order:

1. `SONAR_PROJECT_KEY` env var (override for non-standard naming).
2. `[pr] sonar_project_key` in `.agex/config.toml`.
3. `<owner>_<repo>` (SonarCloud GitHub-import default).

When the project isn't on SonarCloud the API 404s and agex silently
skips the section, so the verbs stay safe for non-Sonar repos. A non-zero
`TO_REVIEW` hotspot count is surfaced alongside the new-issue tally; both are
omitted when empty.

## Deploy-preview URL and review-thread tally

Two more net-additive briefing lines, both safe on repos that don't have them:

- **Deploy preview** — when a bot posts a Cloudflare Pages `*.pages.dev` link in a
  PR comment, the first such URL is lifted into the briefing header. Skipped when
  no `*.pages.dev` URL is present (non-Cloudflare repos).
- **Review threads** — a `Total / Resolved / Unresolved` tally under Readiness.
  The unresolved count is the same one that drives the "Next step:" footer and the
  `await` gate; the line is omitted when the PR has no review threads.

Every command ends with a `**Next step:**` footer — chase the chain without guessing.

## Side effects

Network: every command except `lint` and `delta` talks to GitHub via `gh`.
`pr open` (non-draft, new PR) and `pr review` post the `/agentic_review` trigger
comment.
Disk: `pr open`, `pr read`, `pr reply`, and `pr review` append events to
`.agex/data/pr/events.jsonl`.

## Prerequisites

- `gh` (GitHub CLI) on PATH and authenticated (`gh auth login`).
- `--agent` flag, or first agent's `backend:` set in `culture.yaml`.

For each verb's full behavior, error modes, and exit codes, see
`docs/superpowers/specs/2026-05-10-agex-pr-design.md`.
