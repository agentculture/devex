# `agex pr` — porting the cicd skill into agex

**Date:** 2026-05-10
**Status:** Draft (pending user review)
**Scope:** A new `agex pr <verb>` command namespace that supersedes the bash `cicd` skill at `.claude/skills/cicd/`. v0.1 covers `pr lint`, `pr open`, `pr read`, `pr reply`, `pr delta`. Sibling future namespaces (`agex actions ...`, `agex release ...`) are deliberately out of scope.

## Context

Agex v0.1 (spec `2026-04-18-agex-design.md`) shipped as a strictly non-agentic, deterministic CLI: zero LLM calls, markdown-only output, no network, no sleep, side effects strictly enumerated to `gamify`, `gamify --uninstall`, `hook write`, and first-run `.agex/` init.

In parallel, `.claude/skills/cicd/` accreted ten bash scripts (~1135 lines) that handle the project's PR loop end-to-end: portability lint, `gh pr create`, readiness polling against Qodo/Copilot, fetching CI/SonarCloud/comments into a single briefing, batch-replying with thread resolution, and an alignment-delta dump. The bash skill works but is the wrong layer for two reasons:

1. **It's bash.** Hard to test, hard to extend, hard to share with sibling repos.
2. **It already encodes everything an agent needs to do CI/CD well.** The "intelligence" the agent applies on top is just chaining these primitives in the right order. That chaining is itself testable, deterministic, and worth promoting to a first-class agex command surface.

The opportunity is to move that bash logic into agex while extending agex's invariants in a scoped, deliberate way — and to use the move as an occasion to add the one thing the bash skill can't easily provide: a per-command **"Next step:" footer** so the agent never has to guess what to chain next.

This spec is also the test bed for relaxing agex's "no network / no sleep" invariants. If `agex pr` ships clean, the same pattern unlocks future siblings (`agex actions ...` for GitHub Actions, `agex release ...` for tagging/changelog).

## Design invariants — additions and carve-outs

The original agex invariants stand, with two scoped relaxations:

- **Invariant 3 carve-out:** "no retries, no sleeps, no network" is relaxed for the `agex pr` namespace only, and only for: GitHub API reads/writes (via `gh` shellout in v0.1), and `--wait`-gated bounded sleep in `agex pr read`. **No silent retries anywhere** — if the agent wants retry, it reruns the command.
- **Invariant 6 extension:** the enumerated side-effecting commands gain `pr open`, `pr reply`, and `pr read` (journal writes only). Network reads in `pr read` are not "side effects" by this definition; journal writes are.

Unchanged invariants:

- **Invariant 1 (non-agentic):** all output is deterministic markdown from Jinja templates + Python. Next-step footers come from a small prioritized rule table per command, not from an LLM.
- **Invariant 2 (markdown-only):** no `--json` flag.
- **Invariant 3 (`--agent` required):** required, with `culture.yaml`'s first-agent `backend` field as a fallback source.
- **Invariant 7 (idempotency):** `pr open` short-circuits when the branch already has an open PR; `pr reply` is naturally idempotent per-comment-id; `pr read` is read-only on GitHub.
- **Invariant 8 (skills authored by the agent):** the existing bash skill at `.claude/skills/cicd/` dissolves; its content moves into `commands/learn/assets/topics/cicd/SKILL.md`, taught to the agent via `agex learn cicd`. agex does not write a skill file into the user's project.
- **Invariant 9 (unsupported = success):** if `gh` is unavailable, exit 1 with instructive stderr (this isn't an unsupported capability, it's a missing prerequisite — see Error handling).

## Command surface (v0.1)

| Verb | Replaces (bash) | Side effects |
|---|---|---|
| `agex pr lint` | `portability-lint.sh` | Read-only. |
| `agex pr open --title T [--body-file F] [--draft] [--delayed-read]` | first half of `create-pr-and-wait.sh` | `gh pr create`; one journal append. With `--delayed-read`, chains to `read --wait 180`. |
| `agex pr read [<PR>] [--wait SECS]` | `pr-status.sh` + `pr-comments.sh` + `poll-readiness.sh` | Read-only network; one journal append (or two with readiness). Bounded sleep when `--wait` given. |
| `agex pr reply <PR>` | `pr-reply.sh` + `pr-batch.sh` | Posts comments, resolves threads; one journal append per reply, one per batch. |
| `agex pr delta` | `delta` subcommand of `workflow.sh` | Read-only. |

Every command ends with a deterministic **"Next step:"** footer derived from a small per-command rule table. Footers reference the next agex command in the typical chain (e.g. `pr lint` clean → "commit, push, then `agex pr open --title ...`"; `pr open` → "rerun `agex pr read <N> --wait 180` (recommended) or `agex pr read <N>` in ~3 min").

Deliberately **not** in v0.1:

- `agex pr next` — replaced by per-command footers. Reconsider once journals are rich enough to power retrospective hints.
- `agex pr poll`, `agex pr status`, `agex pr comments` — folded into `read`.
- `agex actions ...`, `agex release ...` — sibling namespaces, future work.
- Test running, version bump, changelog generation — agex doesn't shell `pytest` or edit `pyproject.toml`. Footers can suggest the right invocation; the agent runs them.

## Architecture

Same three-stage pipeline as the rest of agex (cli → command script → core renderer). New directory `commands/pr/` joins the existing command set. New module `core/github.py` wraps every `gh` shellout behind a stable Python interface so the future zero-trust httpx swap touches only that file (tracked as a separate issue).

```
cli.py ──► commands/pr/scripts/<verb>.py ──► core/render.py
              │           │                       │
              │           ├─► core/github.py      ├─► reads templates/*.md.j2
              │           │   (gh shellout)       ├─► injects {backend, paths, gh_data, footer}
              │           ├─► assets/rules/*.py   └─► writes markdown to stdout
              │           └─► core/journal.py        + heartbeats to stderr (read --wait)
              └─► core/backend.py
                  (resolves --agent or culture.yaml fallback)
```

## Components

### New: `commands/pr/`

```
commands/pr/
  SKILL.md                       # frontmatter + body; doubles as `agex explain pr`
  scripts/
    __init__.py
    lint.py
    open_.py                     # avoid keyword shadow
    read.py
    reply.py
    delta.py
    _footer.py                   # render Next-step footer per command + state
    _journal.py                  # thin wrapper over core/journal.py for the pr/ stream
  assets/
    backends/                    # one YAML per backend with footer-hint variants
      claude-code.yaml
      codex.yaml
      copilot.yaml
      acp.yaml
    templates/
      lint_result.md.j2
      pr_briefing.md.j2          # the unified read output
      pr_open_result.md.j2
      pr_reply_result.md.j2
      delta.md.j2
      footer.md.j2               # shared footer template
    rules/
      lint_rules.py              # ports portability-lint.sh checks
      next_step_rules.py         # prioritized rules → next-step hint
  references/                    # dev notes; not emitted at runtime
```

### New: `core/github.py`

Stable Python surface wrapping `gh`:

```python
def pr_create(title: str, body: str, draft: bool) -> int: ...
def pr_view(pr_or_branch: str | None) -> dict: ...
def pr_checks(pr: int) -> list[dict]: ...
def pr_comments(pr: int) -> list[dict]: ...        # inline + thread + top-level + reviews
def pr_post_comment(pr: int, body: str, in_reply_to: int | None) -> int: ...
def pr_resolve_thread(thread_id: str) -> None: ...
def sonar_quality_gate(project_key: str, pr: int) -> dict | None: ...
def sonar_new_issues(project_key: str, pr: int) -> list[dict]: ...
def resolve_nick(project_dir: Path) -> str: ...    # ports _resolve-nick.sh
```

Every call shells `gh api ...` / `gh pr ...` and parses JSON. `RuntimeError` with the gh stderr first line on hard failure; soft failures (missing SonarCloud project) return `None` / `[]` so renders still succeed. When httpx replaces gh, only this file changes.

### New: `core/journal.py`

`append_event(stream, payload)` — JSONL append using `portalocker.lock` / `portalocker.unlock` (matches the existing convention in `core/hook_io.py`). `pr` events go to `.agex/data/pr/events.jsonl`. `core/hook_io.py` stays unchanged in v0.1 (a future refactor can collapse them); the new `pr` namespace uses `core/journal.py` directly to avoid touching the existing hook surface.

### Extended: `core/backend.py`

Add one helper:

```python
def resolve_backend(arg: str | None, project_dir: Path) -> Backend:
    """Resolve --agent: explicit arg wins, else first agent's backend in
    culture.yaml, else raise the existing missing-agent error."""
```

### Extended: `core/config.py`

Add an optional `[pr]` section to `.agex/config.toml`:

```toml
[pr]
wait_default = 180                  # seconds; default for --wait when bare
required_reviewers = ["qodo"]       # readiness gate set
gh_exec = "gh"                      # override path to gh binary
```

All keys optional; sensible defaults if absent.

### Reused (no change)

`core/render.py`, `core/paths.py`, `core/skill_loader.py`, `core/capabilities.py`.

### Lesson: `commands/learn/assets/topics/cicd/`

The `cicd` lesson teaches the agent the workflow. SKILL.md content is the existing bash skill's `SKILL.md` rewritten around `agex pr ...` invocations. No skill file is shipped to the agent's project (per invariant 8). `agex learn cicd` becomes the canonical entry point.

## Data flow per command

### `agex pr lint`

1. `cli.py` validates `--agent` (or resolves via `culture.yaml`).
2. `lint.py` calls `git diff --staged` + `git diff` for the file list and contents.
3. Runs rules from `assets/rules/lint_rules.py`:
   - **Portability:** no absolute `/home/<user>/` paths in committed files; no per-user dotfile refs (`~/.claude/...`, `~/.codex/...`) in committed docs.
   - **Alignment-delta trigger:** flag if `CLAUDE.md`, `culture.yaml`, or `.claude/skills/**` are touched (informational — points the agent at `agex pr delta`).
4. Render `templates/lint_result.md.j2` with `{violations, alignment_triggered, backend}`.
5. Footer driven by violation state and alignment trigger (see "Next-step rules" below).
6. Exit 0 always (lint failures aren't process errors; markdown carries the verdict). `--exit-on-violation` opt-in flag for CI use.

Read-only. No journal entry (high frequency, low signal).

### `agex pr open --title T [--body-file F] [--draft] [--delayed-read]`

1. Validate `--agent`. Read body from `--body-file` or stdin.
2. `core/github.py::resolve_nick(cwd)` → `<nick>`. If body lacks a `- <nick> (Claude)` signature, append it.
3. Idempotency check: `gh pr view <branch> --json number` — if a PR already exists for this branch, render "PR #N already open" and short-circuit to step 6.
4. `core/github.py::pr_create(title, signed_body, draft)` → `pr_number`.
5. Append journal event: `{type: "pr_opened", pr: N, ts, title}`.
6. Render `templates/pr_open_result.md.j2` with `{pr, url, title, signed: bool}`.
7. **If `--delayed-read`:** chain immediately to `read.py::run(pr=N, wait=180)`; output is concatenated (open result + briefing).
8. Footer (without `--delayed-read`): "Next: `agex pr read <N> --wait 180` (recommended) or `agex pr read <N>` in ~3 min."

Side effects: one `gh pr create`, one journal append (plus whatever `--delayed-read` chains).

### `agex pr read [<PR>] [--wait SECS]`

1. Validate `--agent`. Resolve `<PR>`: explicit arg wins, else `gh pr view --json number` for current branch.
2. **If `--wait SECS` given:** loop with bounded sleep (60s interval, capped by `SECS`). `SECS` is an **upper bound**, not a minimum sleep: readiness is evaluated on entry, so the loop may return at `waited=0s` when it's already satisfied (the stderr heartbeat then notes "readiness already satisfied on entry; not polling").
   - Each iteration: `gh api repos/.../pulls/<PR>` for state, `gh api repos/.../issues/<PR>/comments` for new bot comments.
   - Readiness gate: required reviewers (default from `[pr].required_reviewers`, falling back to `["qodo"]`) have posted real (non-placeholder) feedback, OR PR closed.
   - Heartbeat to **stderr** every iteration (final briefing only on stdout — preserves the bash invariant).
   - On readiness: append `{type: "readiness_arrived", pr, ts, waited_secs}` to journal, fall through to step 3.
   - On timeout: render briefing-so-far with a "Still waiting on: <reviewers>" banner; footer suggests rerun. Exit 0.
3. Pull briefing inputs in parallel (one shell per call, sequenced via `concurrent.futures`):
   - `gh pr checks <PR>` → CI checks.
   - `gh api repos/.../pulls/<PR>` → PR meta + state.
   - `gh api repos/.../pulls/<PR>/comments` + `.../issues/<PR>/comments` + `.../pulls/<PR>/reviews` → all comments.
   - SonarCloud quality gate + new issues (silent skip if project not registered).
4. Append journal event: `{type: "pr_read", pr, ts, comment_count, threads_unresolved, ci_state}`.
5. Render `templates/pr_briefing.md.j2`. Sections mirror the bash output: CI checks, SonarCloud, inline comments by file:line, threads, top-level comments, sonar-new issues.
6. Footer driven by `next_step_rules.py` against the briefing data.

Side effects: read-only network; one or two journal appends.

### `agex pr reply <PR>`

1. Validate `--agent`. Read JSONL from stdin. Each line: `{comment_id?, thread_id?, body, in_reply_to?}`.
2. For each entry:
   - Resolve nick; auto-sign body if not already signed.
   - `core/github.py::pr_post_comment(...)` (uses `comment_id` / `in_reply_to` / top-level as appropriate).
   - `pr_resolve_thread(thread_id)` if `thread_id` given.
   - Journal: `{type: "pr_reply", pr, ts, thread_id?, comment_id?}` per entry.
3. After loop: journal `{type: "pr_batch_replied", pr, ts, count: N, resolved: M}`.
4. Render `templates/pr_reply_result.md.j2` with `{count, resolved, failures}`.
5. Footer driven by `next_step_rules.py` (failures → resubmit guidance; clean → push + reread).

Side effects: posts comments, resolves threads, multiple journal appends.

### `agex pr delta`

1. Read `sibling_projects` from `.claude/skills.local.yaml` (existing convention).
2. For each sibling: dump the first 50 lines of `CLAUDE.md` (configurable via `[pr].delta_claude_md_lines` in `config.toml`) plus the entire `culture.yaml`.
3. Render `templates/delta.md.j2`.
4. Footer: "Next: triage each sibling — open follow-up PRs where alignment drifted; mention them in your reply."

Read-only. No journal entry.

### Next-step rules (`next_step_rules.py`)

Small prioritized rule list. First match wins. Each rule is a pure function `(command_context, briefing_data | None, journal_state) -> Optional[str]`. Examples for v0.1:

| Triggered after | Condition | Hint |
|---|---|---|
| `pr lint` | violations > 0 | "Fix violations above and rerun `agex pr lint`." |
| `pr lint` | clean + alignment trigger | "Run `agex pr delta` (this PR touches alignment files), then commit, push, and `agex pr open --title ...`." |
| `pr lint` | clean | "Commit, push, then `agex pr open --title ...`." |
| `pr open` | always | "`agex pr read <N> --wait 180` (recommended) or `agex pr read <N>` in ~3 min." |
| `pr read` | unresolved threads + local commits newer than the last `pr_read` event for this PR in the journal | "Push fixes, then `agex pr read <PR> --wait 180`." |
| `pr read` | unresolved threads + no new local commits since last `pr_read` | "Triage, then `agex pr reply <PR>` with replies on stdin." |
| `pr read` | CI red | "Fix CI before requesting re-review." |
| `pr read` | clean + CI green + no unresolved | "Wait for human merge." |
| `pr read --wait` | timeout reached | "Rerun `agex pr read <PR> --wait 180` to continue waiting." |
| `pr reply` | any failures | "Resubmit the failed lines from the table above to `agex pr reply <PR>`." |
| `pr reply` | all succeeded | "Push fixes (if any), then `agex pr read <PR> --wait 180`." |
| `pr delta` | always | "Triage each sibling — open follow-up PRs where alignment drifted; mention them in your reply." |

Per-backend variants live in `assets/backends/<backend>.yaml` (e.g., Claude Code may suggest `ScheduleWakeup 180` instead of plain "in ~3 min"). The rule produces a key; the YAML fills in the backend-specific phrasing.

## On-disk state

### `.agex/data/pr/`

```
.agex/data/pr/
  events.jsonl      # append-only journal
```

Event schema:

```json
{"ts": "2026-05-10T14:23:01Z", "agent": "agex-cli", "backend": "claude-code",
 "type": "pr_opened", "pr": 42, "title": "feat: ..."}
```

Event types in v0.1: `pr_opened`, `pr_read`, `readiness_arrived`, `pr_reply`, `pr_batch_replied`. Future types (`pr_merged`, `pr_closed`) just append. `agex hook read` extends to discover `pr/` alongside `data/*.json`.

### `config.toml` additions

```toml
[pr]
wait_default = 180
required_reviewers = ["qodo"]
gh_exec = "gh"
```

All optional.

## Error handling

Markdown to stdout for the agent (full diagnosis); single-line **instructive** stderr for shell wrappers (verb-first resolution step, never bare diagnosis).

| Condition | Exit | Stdout | Stderr (instructive) |
|---|---|---|---|
| `--agent` missing AND `culture.yaml` absent | 2 | Markdown listing valid backends + how to set in `culture.yaml` | `agex: pass --agent <claude-code\|codex\|copilot\|acp> or add 'backend:' to culture.yaml` |
| `gh` not installed | 1 | Markdown with `gh` install link + zero-trust roadmap note | `agex: install gh — https://cli.github.com/ — then rerun` |
| `gh` not authenticated | 1 | Markdown with `gh auth login` walkthrough | `agex: run 'gh auth login' then rerun` |
| Network failure on read | 0 | Partial briefing with `> ⚠️ failed to fetch <section> — skipped` inline | (none) |
| Network failure on `pr open` | 1 | Markdown with the gh stderr fenced + retry guidance | `agex: rerun 'agex pr open ...' once network is reachable` |
| Network failure on `pr reply` | 1 | Markdown listing which JSONL entries posted vs failed, with the failed lines fenced for direct resubmission | `agex: resubmit lines N..M from the table above to 'agex pr reply <PR>'` |
| `pr open` when branch already has open PR | 0 | "PR #N already open — skipping create" then chains to `read` | (none) |
| `pr reply` JSONL parse error on line N | 1 | Markdown showing the bad line, the parse error, and the safe resubmit slice | `agex: fix line N (see stdout) and resubmit lines N..end to 'agex pr reply <PR>'` |
| `pr read --wait` timeout reached | 0 | Briefing-so-far + "Still waiting on: <reviewers>" + suggested rerun | (none) |
| SonarCloud project not registered | 0 | Briefing renders without sonar sections (silent skip) | (none) |
| `pr delta` with no `skills.local.yaml` | 0 | Markdown explaining the file is needed + pointer to `.example` | `agex: copy .claude/skills.local.yaml.example to .claude/skills.local.yaml and fill sibling_projects` |
| `.agex/data/pr/` write failure | 1 | Markdown stating "network action succeeded, journal write failed" + manual recovery steps | `agex: ensure .agex/data/ is writable then rerun (the gh action already succeeded — do not retry it)` |

### Stderr conventions

- **Verb-first.** "install gh", "run gh auth login", "resubmit lines N..M", "ensure .agex/data is writable" — not "gh CLI not found".
- **Single line.** stderr is for grep/log scrapers; long-form goes to stdout markdown.
- **No diagnosis in stderr unless it's part of the fix.**
- **Half-succeeded actions** (e.g., `pr reply` partial, `.agex/` write after gh succeeded) explicitly say "do not retry the X step" so the agent doesn't double-post.

### Design rules

1. Network failure on read = partial render, exit 0.
2. Network failure on write = exit 1 with surgical recovery info.
3. Journal write failures are surfaced loudly, never silently retried.
4. No silent retries anywhere — agent reruns if it wants retry.
5. `--wait` timeout is success, not failure.

## Testing

### Pytest layout

```
tests/
  commands/pr/
    test_lint.py
    test_open.py
    test_read.py
    test_reply.py
    test_delta.py
    test_footer.py
  core/
    test_github.py
    test_journal.py
    test_backend_resolution.py
  fixtures/
    gh/                         # canned gh JSON responses
    journals/                   # canned events.jsonl files
```

### Test strategy

- **Pure rule logic** (`lint_rules.py`, `next_step_rules.py`) — plain unit tests, no mocking. Feed in `(diff, file_list, journal_state)` tuples; assert returned violations / hint strings. Cover heavily — this is most of the new code's value.
- **`core/github.py` shellout** — monkeypatch `subprocess.run` to return canned `gh` JSON fixtures from `tests/fixtures/gh/`. When httpx replaces gh, only fixtures stay; wrapper tests get rewritten.
- **Command scripts** — invoke through `cli.py` with `typer.testing.CliRunner`, monkeypatch `core/github.py` functions, snapshot-test the rendered markdown, assert exit codes, assert journal events appended.
- **`--wait` loop in `read.py`** — inject a fake clock + a mock `pr_view` that flips state on the Nth call. Assert: heartbeat goes to stderr, briefing goes to stdout, journal records `readiness_arrived` with correct `waited_secs`, timeout path renders the "still waiting" banner.
- **Idempotency** — `pr open` test runs twice; second call asserts no second `gh pr create`. `pr reply` test sends the same JSONL twice; assert agex doesn't crash and journal records both attempts honestly.
- **Error paths** — one test per row in the section above.
- **Backend resolution** — `--agent` flag wins, then `culture.yaml`'s first-agent backend, then error.

### Dogfood acceptance gate

The integration test for v0.1 is **the PR that introduces `agex pr` itself**. The implementation plan ends with this checklist:

1. Implementation complete; pytest green; lint clean.
2. `agex pr lint` on the implementation branch — must report clean.
3. `agex pr open --title "feat: agex pr commands (v0.x.0)" --body-file ./docs/.../pr-body.md --delayed-read` — must create the PR and chain into `read --wait 180`.
4. `agex pr read <PR> --wait 180` re-run after Qodo posts — must render the briefing including Qodo's inline comments.
5. Triage Qodo/Copilot/Sonar feedback by writing a `replies.jsonl`; `agex pr reply <PR> < replies.jsonl` — must post each reply, resolve every thread, and append the journal events.
6. Repeat steps 4–5 until reviewers are quiet and CI green.
7. Inspect `.agex/data/pr/events.jsonl` after merge — must contain `pr_opened`, several `pr_read` + `readiness_arrived`, several `pr_reply`, one `pr_batch_replied` per batch call. This becomes `tests/fixtures/journals/dogfood_<PR>.jsonl` — real input the next-step rule tests pin against.

If any step requires falling back to the bash `cicd` skill, that's a **bug**, not a workaround — file it and fix before merge. Specifically:

- Step 3 fails (`pr open` broken) → fall back to `gh pr create`, file a blocker, fix, force-push, retry from step 3.
- Step 4 fails (`pr read --wait` wrong) → fall back to bash `workflow.sh await`, file a blocker, fix, retry.
- Step 5 fails (replies don't post or threads don't resolve) → critical; do NOT manually post via `gh`. Fix `pr reply` first; the whole point is to validate the write path.

Forces us to ship `agex pr lint` early in the implementation (so it can lint itself), which surfaces the bootstrap-circularity question now rather than after merge.

### CI surface

`.github/workflows/test.yml` matrix (3 OS × 4 Python) picks up the new tests with no config changes. Coverage target stays whatever Sonar already enforces. Dogfood acceptance is a manual checklist on the introducing PR, not a CI job (it requires writing to the live PR).

## Verification

After implementation, verify end-to-end by walking the dogfood acceptance gate above against the introducing PR. Specifically, the spec is satisfied when:

- `uv run pytest` is green on the matrix.
- `agex pr lint` runs clean against the implementation branch.
- `agex pr open --delayed-read` creates a real PR and chains into `pr read --wait 180`.
- `agex pr read <PR> --wait 180` renders a briefing with all CI/Sonar/comments sections; journal records `pr_read` + `readiness_arrived`.
- `agex pr reply <PR> < replies.jsonl` posts every reply, resolves every thread, and journals one `pr_reply` per line plus one `pr_batch_replied`.
- `agex pr delta` dumps every sibling project's `CLAUDE.md` head + `culture.yaml`.
- `agex learn cicd` teaches the workflow without referencing the deleted `.claude/skills/cicd/` bash scripts.

## Out of scope (tracked separately)

- **Pure-Python httpx GitHub I/O** (zero-trust prerequisite) — file as a follow-up issue. v0.1 ships `gh` shellout.
- **`agex actions ...`** (GitHub Actions verbs) — sibling future namespace.
- **`agex release ...`** (tagging, changelog, version-bump glue) — sibling future namespace.
- **`agex pr next`** as a standalone command — reconsider once journals are rich enough to power retrospective hints; v0.1 covers the use case via per-command footers.
- **Live integration test against real GitHub in CI** — replaced by manual dogfood acceptance on the introducing PR.

## Critical files

New:

- `src/agent_experience/commands/pr/SKILL.md`
- `src/agent_experience/commands/pr/scripts/{lint,open_,read,reply,delta,_footer,_journal}.py`
- `src/agent_experience/commands/pr/assets/templates/{lint_result,pr_briefing,pr_open_result,pr_reply_result,delta,footer}.md.j2`
- `src/agent_experience/commands/pr/assets/backends/{claude-code,codex,copilot,acp}.yaml`
- `src/agent_experience/commands/pr/assets/rules/{lint_rules,next_step_rules}.py`
- `src/agent_experience/core/github.py`
- `src/agent_experience/core/journal.py`
- `src/agent_experience/commands/learn/assets/topics/cicd/SKILL.md`
- `tests/commands/pr/test_*.py`
- `tests/core/test_{github,journal,backend_resolution}.py`
- `tests/fixtures/{gh,journals}/...`

Modified:

- `src/agent_experience/cli.py` — register `pr` subcommand.
- `src/agent_experience/core/backend.py` — add `resolve_backend(arg, project_dir)` with `culture.yaml` fallback.
- `src/agent_experience/core/config.py` — add optional `[pr]` section.
- `src/agent_experience/core/hook_io.py` — delegate to `core/journal.py` (or stay as alias; decide in plan).
- `pyproject.toml` — bump version, no new runtime deps (gh is system).
- `CHANGELOG.md` — describe the new namespace.
- `CLAUDE.md` — document the `agex pr` namespace and the dissolved cicd bash skill.

Removed:

- `.claude/skills/cicd/` (entire directory, after the introducing PR's dogfood succeeds and the lesson is in place).
