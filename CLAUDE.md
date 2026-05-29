# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`devex` — non-agentic Python CLI that emits deterministic per-backend markdown briefings for autonomous agents. Published on PyPI under three distribution names: `devex-cli` (canonical), `agent-devex`, and `agex-cli` (the legacy canonical name, still published) — the same wheel each time. CLI entry points: `devex` (canonical) and `agex` (legacy alias) — both invoke the same tool; emitted output reflects whichever name was typed. GitHub repo: `agentculture/devex`. Python module: `devex` (renamed from `agent_experience`).

**Source-of-truth documents:**

- Spec: `docs/superpowers/specs/2026-04-18-agex-design.md`
- Implementation plan: `docs/superpowers/plans/2026-04-18-agex-v0.1.md` — 33 tasks across 12 phases.
- Status: PR #1 merged Phases 1–3 (scaffolding, core, `devex explain`). Phases 4–12 (`overview`, `learn`, `gamify`, `hook`, backends, docs site, tester) remain.

Read the spec before any non-trivial change — the design invariants below are derived from it.

## Design invariants (non-negotiable)

1. **Zero LLM calls inside devex.** All output is deterministic markdown from Jinja templates + Python.
2. **Markdown is the only output format.** No `--json` flag.
3. **`--agent <backend>` is required** on backend-sensitive commands. The CLI never auto-detects.
4. **Side effects only in** `gamify`, `gamify --uninstall`, `hook write`, `pr open`, `pr reply`, `pr review`, `pr read` (journal writes), `pr await` (journal + `--detach` marker writes under `.devex/data/pr/<pr>/` and the detached poller subprocess), `push` (see below), and first-run `.devex/` init. Everything else is read-only. The `devex pr` namespace allows scoped network I/O (via `gh`), bounded `--wait` sleep, and — for `pr await --detach` — a detached background process that pays that sleep outside the agent session; a deliberate carve-out from the no-network/no-sleep invariants. `devex push` performs a `git push` of the current branch (push-only — it never stages or commits); a deliberate carve-out from the no-mutation invariant, introducing `git push` as a new allowed side-effect class.
5. **"Unsupported" is success** — exit 0 with a markdown notice that links to the issue tracker, not a non-zero exit.
6. **Skills are authored by the agent, not shipped by devex.** `devex learn <topic>` teaches; `devex explain <topic>` describes; devex never writes a user skill file on the agent's behalf in v0.1.

## Architecture (3-stage pipeline)

Every command follows the same shape:

```
cli.py ──► commands/<name>/scripts/<name>.py ──► core/render.py
              │                                    │
              ├─► backends/<name>/probe.py         ├─► reads SKILL.md / *.md.j2
              │   (reads project state)            ├─► injects {backend, paths, capabilities, probe}
              └─► core/capabilities.py             └─► writes markdown to stdout
                  (supported / unsupported)
```

- `cli.py` (Typer) routes `devex <command> [args] --agent X`. No business logic.
- Each `commands/<name>/` is a **skill-folder**: `SKILL.md` + `scripts/` + `assets/` + `references/`. The `SKILL.md` doubles as the content emitted by `devex explain <command>`.
- `core/` is shared plumbing — backend enum, `.devex/` paths, Jinja renderer (`StrictUndefined`), TOML config, SKILL.md frontmatter parser, capability matrix loader, hook JSON I/O. Command- and content-agnostic.
- A backend lives in three places: `core/backend.Backend` (enum entry), `backends/<name>/probe.py` (optional Python probe), and one YAML per relevant command under `commands/*/assets/backends/<name>.yaml`. Adding a backend touches only those locations.

## `devex pr` namespace (v0.17.0+)

`lint`, `open`, `read`, `reply`, `review`, `await`, `delta`. Each command ends with a deterministic "Next step:" footer. The `pr` namespace allows scoped network I/O (via `gh`) and bounded `--wait` sleep — a deliberate carve-out from the no-network/no-sleep invariants. `pr open` (non-draft, new PR) and `pr review` post the Qodo `/agentic_review` trigger comment; the legacy `/improve` is deprecated and never emitted. The trigger string lives in one place: `commands/pr/scripts/review.QODO_REVIEW_TRIGGER`. `pr await --detach` / `--check` (issue #64) move the bounded poll out of the agent session: `--detach` forks a detached worker (`commands/pr/scripts/_await_worker.py`) that writes the verdict to a marker (`commands/pr/scripts/_detach.py`, atomic `os.replace`), and `--check` reads it back without sleeping. Key modules:

- `core/github.py` — thin `gh` shellout wrapper; future zero-trust httpx swap touches only this file.
- `commands/pr/scripts/_detach.py` — await-marker read/write (atomic) + the detached-subprocess spawn helper.
- `core/journal.py` — nested-stream JSONL append/load for `.devex/data/<dir>/<stream>.jsonl`.
- `core/backend.resolve_backend()` — `--agent` resolution with `culture.yaml` fallback.
- `commands/pr/assets/rules/next_step_rules.py` — "Next step:" footer decision logic, per-backend phrasing under `commands/pr/assets/backends/<backend>.yaml`.

Spec: `docs/superpowers/specs/2026-05-10-agex-pr-design.md`. Plan: `docs/superpowers/plans/2026-05-10-agex-pr.md`.

## Conventions worth following

- **Resource loading: use `importlib.resources.files(...)` and treat the result as a `Traversable`.** Call `.joinpath()` / `.is_file()` / `.read_text(encoding="utf-8")` directly. Wrap with `importlib.resources.as_file()` only when a third-party API needs a real `pathlib.Path`. Do NOT do `Path(str(files(...)))` — it's not zipapp/PEX safe.
- **File locking: use `portalocker.lock` / `portalocker.unlock`.** Reaching for `fcntl.flock` / `msvcrt.locking` directly is a known foot-gun on Windows (see commit `923f639`).
- **Always pass `encoding="utf-8"` to `read_text` / `write_text`.** Default locale on Windows corrupts non-ASCII output.
- **Validate user-controlled CLI args before joining into paths.** `devex explain <topic>` rejects anything that doesn't match `^[a-z][a-z0-9-]*$` to block path traversal (commit `5ac796e`, test `test_explain_rejects_path_traversal`).
- **Single source of truth for the version:** `pyproject.toml`. `devex.__version__` derives from installed distribution metadata via `importlib.metadata.version("devex-cli")` (falling back to the `agent-devex` / `agex-cli` alias dists, then pyproject), and `Config.agex_version` derives from `__version__` via `field(default_factory=...)`. (The `agex_version` config-file key name is kept for back-compat with existing `.devex/config.toml` / `.agex/config.toml` files.) Bumping the version means editing `pyproject.toml` only — no `__init__.py` edit needed.

## Common commands

```bash
# Bootstrap
uv venv && uv pip install -e ".[dev]"

# Full test suite (parallel; pytest-xdist via pyproject)
uv run pytest

# Single test
uv run pytest tests/core/test_paths.py::test_ensure_init_creates_dir_and_gitignore -v

# Run the CLI
uv run devex --version
uv run devex explain devex
uv run devex explain explain

# Coverage (matches what build.yml runs; SonarCloud reads this file)
uv run pytest --cov=src/devex --cov-report=xml --cov-report=term
```

## CI surface

- `.github/workflows/test.yml` — matrix: 3 OS × 4 Python (3.10–3.13) running `uv run pytest`. Also runs a `version-check` job on PRs that fails (with a sticky `<!-- version-check -->` comment) when `pyproject.toml`'s version on the PR matches the one on `main` and any code file under `src/` / `tests/` / `pyproject.toml` changed. Docs-only PRs skip the check.
- `.github/workflows/publish.yml` — builds sdist + wheel. PRs publish a per-PR dev version to TestPyPI (sticky install-command comment); pushes to `main` publish the stable version to TestPyPI (canary), then an `autotag` job pushes `v<version>` if missing, which gates the inline `publish-pypi` + `github-release` jobs. No manual tagging — bumping `pyproject.toml` is the release signal.
- SonarCloud is configured as **Automatic Analysis** on the repo (no CI workflow). Coverage and quality are read by SonarCloud directly.
- All third-party actions are **pinned to full commit SHAs** with trailing `# vN` comments (rule `githubactions:S7637`). Keep new actions pinned the same way.

## SonarCloud notes

- `python:S5496` is **narrowly suppressed** for `src/devex/core/render.py` only via `sonar.issue.ignore.multicriteria` in `sonar-project.properties`. Reason: `render_string()` renders Jinja templates that are always package-shipped; output is markdown, never HTML in a browser. See the comment in `render.py` above `render_string` for the rationale. Do not widen the suppression to other files.
- The `render.py` autoescape decision is explicit (`autoescape=select_autoescape([])`). Don't change it.

## Git workflow

- Branch for all changes. Don't push to `main` directly.
- Bump version in `pyproject.toml` before opening a PR (CI's `version-check` job will fail the PR if you forget — `/version-bump patch` / `minor` / `major` is the fix; it also inserts a fresh section in `CHANGELOG.md`).
- Push, open a PR, let CI + SonarCloud + Qodo + Copilot run. Address inline comments + resolve threads before merge.
- Merging to `main` publishes to PyPI automatically (via `autotag` → `publish-pypi` → `github-release` in `publish.yml`). No manual tagging.
- When posting on GitHub on the user's behalf (PR descriptions, issue replies, review-thread replies), sign so it's clear the message came from an AI. Three conventions, in priority order:
  - **`devex pr open` / `devex pr reply`** — auto-append `- devex-cli (Claude)` (the nick is resolved from `culture.yaml` via `core.github.resolve_nick`, falling back to the repo basename). Don't sign manually.
  - **Inside `communicate` workflow scripts** (`post-issue.sh`, `post-comment.sh`) — `agtag` resolves the same nick from `culture.yaml`. Don't sign manually.
  - **Manual posts the scripts didn't author** (a hand-typed `gh pr create --body …`, a one-off review reply) — sign explicitly as `- devex-cli (Claude)`.
