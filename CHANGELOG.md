# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.22.0] - 2026-05-25

### Added

- **Vendored 9 new skills from the guildmaster canonical kit**
  ([#58](https://github.com/agentculture/agex-cli/issues/58), cite-don't-import).
  Canonical (upstream = `guildmaster`): `agent-config`, `doc-test-alignment`,
  `pypi-maintainer`, `run-tests`, `sonarclaude`, `version-bump`. Inbound
  workflow trio (origin = `devague`, re-broadcast via guildmaster): `think`,
  `spec-to-plan`, `assign-to-workforce`. `doc-test-alignment` lands as a **stub**
  (`scripts/check.sh` exits not-yet-implemented). `version-bump`, `sonarclaude`,
  `pypi-maintainer`, `run-tests`, and `doc-test-alignment` get `type: command`
  added to their frontmatter — agex-cli's `core.skill_loader` requires
  `name`+`description`+`type`, and guildmaster ships those five without `type:`.

### Changed

- **Repointed skill provenance from steward to guildmaster** after the completed
  steward → guildmaster supplier cutover. `cicd` and `communicate` `SKILL.md`
  descriptions and `docs/skill-sources.md` now cite `guildmaster` as the
  canonical upstream (the devague trio tracks `devague` as origin). No script
  changes to either resynced skill — `cicd` keeps its adapted-thin `workflow.sh`
  -only form (agex-cli owns `agex pr`); `communicate` stays identifier-only.
  `docs/skill-sources.md` is restructured into the consumer-side mirror of
  guildmaster's two-table supplier ledger.

## [0.21.2] - 2026-05-24

### Changed

- **Clarified `agex pr read --wait` / `agex pr await --max-wait` semantics**
  ([#55](https://github.com/agentculture/agex-cli/issues/55)). `--wait N` is an
  *upper bound*, not a minimum sleep: the readiness loop already evaluates the
  predicate on entry and returns as soon as it holds — including immediately
  (`waited=0s`) when required reviewers have already posted. When that happens
  the stderr heartbeat now appends `(readiness already satisfied on entry; not
  polling)`, distinguishing "satisfied on entry; never polled" from "polled and
  became ready instantly". `--help` text and `agex explain pr` now document the
  upper-bound semantics and spell out that `ready=True` means *review-feedback-
  present* (every `[pr].required_reviewers`, default `["qodo"]`, has commented),
  **not** merge-ready — use `agex pr await` for CI + Sonar + thread gating.
  No behavior change to the polling loop. The shared heartbeat formatting now
  lives in `_readiness.heartbeat()` so `read` and `await` stay consistent.

## [0.21.1] - 2026-05-24

### Fixed

- **`agex pr` SonarCloud fetch no longer aborts on a transient failure.**
  `core.github.sonar_quality_gate` / `sonar_new_issues` previously caught
  only HTTP 404; any other `gh` failure (timeout, 5xx, rate-limit, auth) or
  a non-JSON body propagated and aborted `agex pr read` / `agex pr await`.
  They now degrade to a `SONAR_GATE_SKIPPED` sentinel (gate) / `[]` (issues)
  — distinct from `None` "project not registered" — and the briefing renders
  `Quality gate: **SKIPPED** _(SonarCloud unreachable — gate not evaluated)_`.
  `await` treats `SKIPPED` as non-blocking (exit 0). Python equivalent of
  [steward#31](https://github.com/agentculture/steward/issues/31) (the
  upstream loss of the 0.9.2 `pr-comments.sh` hardening).
- **`agex pr await` now gates on a Quality Gate of `UNKNOWN`.** The gate
  matched only `ERROR`, so a registered project reporting `UNKNOWN` (analysis
  pending / indeterminate) passed as a false-positive "clean" readiness
  signal. `UNKNOWN` now blocks (exit non-zero) with a dedicated
  `await_gate_unknown` footer across all four backends. Mirrors
  [steward#33](https://github.com/agentculture/steward/issues/33) bug 2.
  (Steward's bugs 1/3/4 and [steward#32](https://github.com/agentculture/steward/issues/32)
  are script-specific and N/A — agex-cli ships no `pr-status.sh` /
  `portability-lint.sh`.)

## [0.21.0] - 2026-05-23

### Removed

- **Retired the Jekyll docs site and its Cloudflare Pages deploy.** The
  public site is now owned by the sibling `agentculture/katvan` (technical
  writer + SEO agent), so agex-cli no longer builds or deploys one. Removed
  `.github/workflows/docs.yml`, `scripts/sync_skill_md.py`, and the Jekyll
  scaffolding under `docs/` (`_config.yml`, `Gemfile`, `_includes/`,
  `_sass/`, `assets/`, `index.md`, `getting-started.md`, `404.md`,
  `commands/`). `docs/` now holds only the maintainer-facing technical docs:
  `superpowers/` (specs + plans) and `skill-sources.md`.

### Added

- **Vendored the `cicd` skill** at `.claude/skills/cicd/`, finishing the
  cicd half of #51 (and #34). Because agex-cli **owns** `agex pr`, this is
  an *adapted-thin* vendor rather than a verbatim copy: the only script is
  `workflow.sh`, a typing-saver that delegates `lint` / `open` / `read` /
  `reply` / `delta` / `await` straight to the native `agex pr` verbs
  (steward's `await` points `read --wait` at a `pr-status.sh` gate; here it
  forwards to the native `agex pr await`). Steward's `status`/`await` shell
  extensions and the `_resolve-nick.sh` / `pr-reply.sh` / `portability-lint.sh`
  helpers are dropped — every one duplicates Python this repo already ships.
  The remaining `pr-status.sh` extras (SonarCloud hotspots, deploy-preview
  URL, explicit thread tally) are tracked as a native feature ask in #52
  instead of re-vendored as bash. Divergence recorded in the `SKILL.md`
  frontmatter and `docs/skill-sources.md` per the cite-don't-import policy.

### Fixed

- **Vendored skills are now discoverable by the Claude Code probe.** Both
  `.claude/skills/cicd/SKILL.md` and the existing
  `.claude/skills/communicate/SKILL.md` were missing the `type:` frontmatter
  field required by `core.skill_loader`, so `backends/claude_code/probe.py`
  silently skipped them (they never appeared in `agex overview`). Both now
  declare `type: command`. `cicd`'s `workflow.sh` also no longer injects a
  default `--agent` — it defers to `agex`'s own `culture.yaml` backend
  resolution per design invariant #3 (no backend defaulting), passing
  `--agent` only when `AGEX_PR_AGENT` is set.

## [0.20.0] - 2026-05-23

### Changed

- **Dropped the `typer` runtime dependency.** The CLI is now built on the
  Python standard library's `argparse`, mirroring the sibling Culture repos
  (`steward`, `devague`). This removes `typer`, `rich`, `shellingham`,
  `annotated-doc`, `markdown-it-py`, `mdurl`, and `pygments` from the shipped
  runtime closure (the wheel now depends only on `jinja2`, `pyyaml`,
  `tomlkit`, and `portalocker`), shrinking the dependency-chain attack
  surface. CLI behaviour is unchanged: every command, flag, exit code, and
  stderr message is preserved, including the `agex explain agex`
  unknown-command routing and the bare `--version` output.

## [0.19.0] - 2026-05-23

### Added

- `agex pr read` (and `pr await`) now surface **Qodo code-review
  findings** that Qodo posts inside collapsed `<details>` blocks of a
  single top-level comment. A new `## Qodo review` section lists the
  headline counts (🐞 Bugs / 📘 Rule violations / 📎 Requirement gaps)
  and each finding's title + `file:line` + link, mirroring how inline
  threads are shown. When counts are non-zero but no per-finding detail
  could be parsed, the briefing flags it (`⚠️ N finding(s) in collapsed
  Qodo review block — expand on GitHub`) so a bug is never silently
  missed. Closes [#47](https://github.com/agentculture/agex-cli/issues/47).

### Changed

- Backend resolution accepts `claude` as an alias of `claude-code`, so
  the AgentCulture-standard `culture.yaml` shape (`backend: claude`)
  works with `agex pr` out of the box. When a `culture.yaml` backend is
  genuinely unknown, the error now names the source, the offending agent
  `suffix`, and the fix (e.g. `culture.yaml agent 'devague' has unknown
  backend 'foo' / hint: expected one of claude (= claude-code), codex,
  copilot, acp`). Closes [#46](https://github.com/agentculture/agex-cli/issues/46).

## [0.18.0] - 2026-05-12

### Added

- `agex pr await [<PR>] [--max-wait SECS]` — combo verb that polls
  reviewer readiness, runs CI + SonarCloud quality gate, and dumps the
  unified briefing. **Exits 1 on quality-gate `ERROR`, unresolved
  review threads, or failing CI checks**, 0 on clean state or timeout.
  Use this when a script should fail if the PR isn't triage-able.
  Closes [#41](https://github.com/agentculture/agex-cli/issues/41).
- `SONAR_PROJECT_KEY` env var (and `[pr].sonar_project_key` config key)
  override the default `<owner>_<repo>` SonarCloud project-key
  derivation, for repos with non-standard project naming.
- `agex learn cicd` lesson now documents the 5-minute Anthropic prompt
  cache TTL and recommends running long waits inside a background
  subagent so the parent session's cache stays warm.

### Changed

- Polling helpers (`is_ready`, `threads_unresolved`, `required_reviewers`,
  `POLL_INTERVAL_SEC`) moved from `commands/pr/scripts/read.py` to a
  shared `commands/pr/scripts/_readiness.py` so `pr read --wait` and
  `pr await` share one implementation. No behavior change for
  `pr read`.

## [0.17.0] - 2026-05-10

### Added

- `agex pr` command namespace: `lint`, `open`, `read`, `reply`, `delta`. Supersedes the bash `cicd` skill.
- `agex pr open --delayed-read` chains to `agex pr read --wait 180` after creating the PR.
- `agex pr read --wait SECS` polls for required reviewer readiness (default `qodo`; configurable via `[pr].required_reviewers`) before rendering the briefing.
- Per-command "Next step:" footers driven by `commands/pr/assets/rules/next_step_rules.py` and per-backend phrasing under `commands/pr/assets/backends/<backend>.yaml`.
- `core/github.py` — thin `gh` shellout wrapper; future zero-trust httpx swap touches only this file.
- `core/journal.py` — nested-stream JSONL append/load for `.agex/data/<dir>/<stream>.jsonl`.
- `core/backend.resolve_backend()` — `--agent` resolution with `culture.yaml` fallback.
- `agex learn cicd` lesson teaching the new workflow.
- `agex hook read` discovers nested `data/<dir>/*.jsonl` streams.

### Changed

- Invariant carve-out: the `agex pr` namespace is allowed scoped network I/O and bounded `--wait` sleep. No silent retries anywhere.
- Side-effect inventory extended to include `pr open`, `pr reply`, and `pr read` (journal writes).

## [0.16.0] — 2026-05-10

### Added

- **Vendored `communicate` skill** at `.claude/skills/communicate/` —
  cross-repo issue posting and Culture mesh messaging, copied from
  steward 0.11.0. Scripts are thin wrappers around `agtag` (≥0.1) for
  issue I/O; nick auto-resolves from the new repo-root `culture.yaml`
  (`agex-cli`). Closes
  [#36](https://github.com/agentculture/agex-cli/issues/36).
- **Vendored `cicd` skill** at `.claude/skills/cicd/` — `gh`-based PR
  workflow (open + auto-wait for Qodo/Copilot, poll CI, triage feedback,
  reply, resolve), portability lint, alignment-delta check, copied from
  steward 0.11.0. Closes
  [#37](https://github.com/agentculture/agex-cli/issues/37).
- **Repo-root `culture.yaml`** — single agent block declaring
  `suffix: agex-cli`, read by `agtag` (`communicate`) and
  `_resolve-nick.sh` (`cicd`) to auto-sign GitHub posts as
  `- agex-cli (Claude)`.
- **`docs/skill-sources.md`** — provenance ledger for vendored skills;
  future steward auto-broadcasts will read this when locating downstream
  copies.

### Changed

- **`CLAUDE.md` signature rule** rewritten to defer to the vendored
  `cicd`/`communicate` scripts (auto-signing as `- agex-cli (Claude)`),
  matching the global AgentCulture convention. Manual posts now sign
  with the same `- agex-cli (Claude)` form instead of `— Claude`.

## [0.15.0] — 2026-05-04

### Added

- **Dual PyPI publish: `agex-cli` and `agent-devex`.** The same wheel is
  now published under two distribution names so users can
  `pip install agex-cli` (canonical) or `pip install agent-devex`
  (alias). Both ship the identical CLI (`agex`) and module
  (`agent_experience`); installing both at once will conflict on the
  `agex` script (intended alias semantics). `publish.yml` matrixes
  `build`, `publish-pr-testpypi`, `publish-testpypi`, and `publish-pypi`
  across the two dist names by rewriting `[project].name` in
  `pyproject.toml` before `python -m build`; `autotag` and
  `github-release` remain single-runs (one tag, one release per
  version).

### Changed

- **Runtime version lookup tolerates either distribution name.**
  `agent_experience.__version__` now resolves whether the package is
  installed as `agex-cli` or `agent-devex`, falling back to the PEP 440
  local-version sentinel `0.0.0+unknown` only in unusual installs (e.g.
  source checkouts that weren't `pip install -e`'d). `agex doctor`'s
  install hint mentions both names.

## [0.14.0] — 2026-04-26

### Added

- **`agex doctor` command.** Zero-argument health check that emits a
  deterministic markdown report covering install (`agex` version, Python
  version, package resources), project state (`.agex/` directory,
  `config.toml`, `.gitignore`, `data/` writability), and internal
  consistency (every shipped `SKILL.md` parses, every per-backend
  capability YAML loads). Exit `0` on green/warnings, `1` on hard
  failure, `2` on usage error. Strictly read-only — never initializes
  `.agex/`. Optional `--role <slug>` flag renders an extra
  role-specific section from `commands/doctor/assets/roles/<slug>.md.j2`
  (extension hook; no role files ship in this release). Adds the
  command to `agex explain agex`, the `_KNOWN_COMMANDS` registry, and
  the SKILL.md meta-tests. New addendum spec at
  `docs/superpowers/specs/2026-04-26-agex-doctor.md`.

## [0.13.2] — 2026-04-23

### Changed

- **Repo URL: `OriNachum/agex` → `agentculture/agex-cli`.** Updated all
  live-code references — `pyproject.toml` project URLs, `ISSUE_URL` in
  `capabilities.py`, issue comment in `hook_io.py`, `agex explain agex`
  topic, gamify unsupported notice, `CLAUDE.md`, docs site config
  (`_config.yml`, `index.md`), and the docs CI workflow comment.
  Historical documents (spec, implementation plan, earlier changelog
  entries) are left as-is.

## [0.13.1] — 2026-04-21

### Fixed

- **Stale canonical URL in PyPI metadata and README.** Follow-up to
  0.13.0 flagged by Copilot and Qodo on PR #26: the docs site moved
  to `https://culture.dev/agex/` but `project.urls.Homepage` in
  `pyproject.toml` still pointed at `https://agex.culture.dev`, and
  the `Docs` link in `README.md` still read
  `[agex.culture.dev](https://agex.culture.dev) (coming soon)`. Both
  user-facing entrypoints now match the Jekyll `url + baseurl`
  canonical — PyPI package page, README docs link, jekyll-seo-tag
  `<link rel="canonical">`, OG URL, and schema.org `url` all agree
  on `https://culture.dev/agex/`.

## [0.13.0] — 2026-04-21

### Changed

- **Docs site now canonically served at `https://culture.dev/agex/`**
  (was `https://agex.culture.dev/`). Path-based hosting under the
  shared origin eliminates cross-origin white flash and the transient
  403s caused by Cloudflare's cross-subdomain bot heuristic — both
  issues reported during 0.12.x rollout. Same-origin navigation also
  lets the Culture aux-nav link transition with zero handshake latency.
- `docs/_config.yml`: `url` → `https://culture.dev`, `baseurl` →
  `/agex`. Jekyll `relative_url` / `absolute_url` filters (already
  used throughout the site) regenerate all internal links under the
  `/agex/` prefix automatically.
- `docs/_includes/head_custom.html`: dropped **all** preconnect /
  dns-prefetch hints — both `https://culture.dev` (self-origin) and
  `https://agentirc.dev` (also moving to `https://culture.dev/agentirc`
  in a paired follow-up on the culture repo, becoming self-origin
  too). Kept the inline critical CSS dark-paint from 0.12.1.
- `docs/_config.yml`: `AgentIRC` aux-link + `footer_content` link now
  point at `https://culture.dev/agentirc` so the nav stays correct
  after the agentirc migration lands. Same-origin = same tab = no
  handshake = no flash.
- `docs/_includes/head_custom.html`: `<link rel="related">` for
  AgentIRC retargeted from `https://agentirc.dev` to
  `https://culture.dev/agentirc` for the same reason.

### Hosting topology (external to this repo)

The Cloudflare Pages project `agex` continues to deploy as before, but
is now proxied under `culture.dev/agex/*` by a Worker on the culture
zone (landing in a follow-up PR on `OriNachum/culture`). The legacy
`https://agex.culture.dev/` hostname is 301-redirected to
`https://culture.dev/agex/` via a Cloudflare Redirect Rule, preserving
SEO and existing bookmarks. Do **not** merge this PR until both the
Worker route and the redirect rule are live in Cloudflare — otherwise
`agex.culture.dev` will serve HTML with broken `/agex/...` internal
links for the switchover window.

## [0.12.3] — 2026-04-21

### Fixed

- **Unknown paths under `agex` served the homepage with a 200 status
  instead of returning a real 404.** Cloudflare Pages' default
  behavior, when a project has no `404.html`, is to fall back to
  `index.html`. That let `/agex/docs`, `/agex/about`, and any other
  bogus path render the agex homepage with the wrong URL — bad for
  users (confusing), bad for SEO (duplicate content across many
  URLs). Added `docs/404.md` (`permalink: /404.html`,
  `sitemap: false`, `search_exclude: true`) — Jekyll emits
  `_site/404.html`, CF Pages now serves it with an actual 404
  response.

## [0.12.2] — 2026-04-20

### Fixed

- **Sibling-site aux-nav links open in a new tab**, defeating the
  white-flash fix from 0.12.1. A fresh tab has none of the preconnect
  hints, none of the warmed TLS connection, and no shared visual
  state — so clicking "Culture" or "AgentIRC" from agex.culture.dev
  still felt like leaving the site. Flipped `aux_links_new_tab` from
  `true` to `false` in `docs/_config.yml` so the Culture / AgentIRC /
  GitHub links navigate in-tab. Users who prefer a new tab can still
  Ctrl/Cmd-click.

## [0.12.1] — 2026-04-20

### Fixed

- **Cross-site white flash** when navigating from `agex.culture.dev`
  to `culture.dev` / `agentirc.dev` (or back). Browsers painted the
  default white page before the dark-terminal stylesheet loaded,
  breaking the illusion of one unified ecosystem. Fix in
  `docs/_includes/head_custom.html`:
  - `<meta name="color-scheme" content="dark">` so the browser's own
    chrome (initial paint, scrollbars) is dark.
  - Inline critical CSS `html{background:#0B0F12;color:#F3F5F7;
    color-scheme:dark}` applied in `<head>` before the external
    stylesheet, so the very first frame is already dark.
  - `<link rel="preconnect">` + `<link rel="dns-prefetch">` for
    `https://culture.dev` and `https://agentirc.dev`, so clicking the
    aux-nav skips DNS + TLS handshake time on the hop.

Sibling fix landing in the culture repo (`culture` + `agentirc` sites)
in a separate PR; once both sides deploy the transition should feel
like a same-origin navigation instead of three separate sites.

## [0.12.0] — 2026-04-20

### Changed

- **docs site: unified with `culture.dev` ecosystem.** `agex.culture.dev`
  now feels like a sibling of `culture.dev` and `agentirc.dev` — same
  favicon, same dark-terminal chrome, shared footer voice, top-right
  aux-nav to Culture / AgentIRC / GitHub. Previously rendered as bare
  theme with no chrome because `docs/` was missing `_includes/`,
  `assets/images/`, and the `aux_links` / `footer_content` / social
  metadata keys that culture's Jekyll config provides.

### Added

- `docs/_includes/head_custom.html` — injects favicons and
  `rel="related"` links to `culture.dev` and `agentirc.dev` for
  cross-site discovery.
- `docs/assets/images/` — favicons (`favicon.ico`, `favicon-16x16.png`,
  `favicon-32x32.png`, `apple-touch-icon.png`) and OG preview images
  (`og-agex.png`, `og-culture.png`), mirrored from the culture repo.
  `og-agex.png` is currently a placeholder (a copy of `og-culture.png`)
  until an agex-specific OG image is designed.
- `docs/_config.yml` — new keys: `logo`, `twitter`, `social`, `author`,
  default OG image under `defaults`, `aux_links` (Culture / AgentIRC /
  GitHub), `aux_links_new_tab: true`, and a `footer_content` block that
  links to both sibling sites and the GitHub repo.
- `docs/index.md` — culture-style hero (`.hero` + `.btn-cta--*` classes,
  already defined in `docs/_sass/custom/custom.scss`) with `nav_order:
  0` and `permalink: /`. Existing quickstart kept below the hero.

## [0.11.1] — 2026-04-19

### Fixed

- **SonarCloud quality gate — 4 open issues resolved.** After the switch
  to Automatic Analysis (`6a6160e`), project-level suppressions in
  `sonar-project.properties` stopped being honored. Re-surfaced two
  previously suppressed false positives and two real workflow-hygiene
  findings:
  - `pythonsecurity:S2083` on `commands/gamify/scripts/install.py` —
    now suppressed inline with `# NOSONAR`; backend remains enum-validated
    via `parse_backend()` before reaching the write. False positive.
  - `pythonsecurity:S5496` on `core/render.py` — now suppressed inline
    with `# NOSONAR(pythonsecurity:S5496)`; markdown-only output, Jinja
    templates are always package-shipped. False positive.
  - `githubactions:S8264` on `.github/workflows/publish.yml` — dropped
    workflow-level `permissions: contents: read` and moved it onto the
    `build` job (the only job without explicit job-level permissions).
  - `githubactions:S7630` on `.github/workflows/docs.yml` — moved
    `${{ github.head_ref }}` out of the inline `run:` script and into an
    `env:` block so a crafted PR branch name can no longer inject shell
    commands ahead of the sed sanitiser.

## [0.11.0] — 2026-04-19

### Added

- **Auto-tag + PyPI release on main.** Every push to `main` now publishes
  the stable version to TestPyPI (canary), auto-creates the `v<version>`
  git tag if missing, publishes to PyPI, and creates a GitHub Release with
  the matching CHANGELOG section. No manual tagging needed; the version
  field in `pyproject.toml` is the release signal.
- **`version-check` CI job** (`.github/workflows/test.yml`) — PRs that
  touch `src/`, `tests/`, or `pyproject.toml` without bumping the version
  fail with a sticky PR comment pointing at `/version-bump`. Mirrors the
  enforcement pattern already in use by culture.

### Changed

- Dropped the `v*` tag trigger from `publish.yml`. Manual tagging is
  superseded by the auto-tag job; tags still exist as historical/Release
  anchors, they just get created for you.

## [0.10.0] — 2026-04-19

### Added
- **`.github/workflows/publish.yml`** — automated publish pipeline.
  Every push to `main` builds an sdist + wheel and publishes to
  **TestPyPI** (`skip-existing: true` makes it idempotent across
  pushes that don't bump the version). Every push of a `v*` tag
  publishes to **PyPI**. Both jobs use **Trusted Publishing** (OIDC),
  so no API tokens are required — the matching PyPI/TestPyPI
  publishers and GitHub repo Environments (`pypi`, `testpypi`) must
  be configured once out-of-band.
- All third-party actions SHA-pinned with trailing `# vN` comments
  per project convention #10: `actions/checkout@v4`,
  `astral-sh/setup-uv@v3`, `actions/setup-python@v5`,
  `actions/upload-artifact@v4`, `actions/download-artifact@v4`,
  `pypa/gh-action-pypi-publish@release/v1`.

### Release notes
This is the closing phase of the v0.1 implementation plan. Phases
1–11 + 13 shipped the CLI, docs site (with per-PR previews), the
Claude dogfooding workspace, and the docs-drift guards. Phase 12
(this release) lights up the publishing pipeline — `agex-cli` is
now installable from TestPyPI via `uv tool install --index-url
https://test.pypi.org/simple/ agex-cli` immediately after the first
post-merge build, and from PyPI after the maintainer pushes a
`v0.10.0` tag.

## [0.9.0] — 2026-04-19

### Added
- **`tester-agents/claude/`** — culture-meshed dogfooding workspace
  that exercises every `agex` command end-to-end from a Claude Code
  runtime. Ships `CLAUDE.md` (persona + ordered test plan),
  `culture.yaml` (mesh config), `.claude/settings.json` (allows
  `Bash(agex:*)`), and a `README.md` with registration instructions.
- **Symlink** `tester-agents/claude/.claude/skills →
  ../../../src/agent_experience/commands` so the tester invokes the
  same `SKILL.md` files the CLI ships — no stale-copy drift. Git
  stores mode `120000`; on Windows clones, directory symlinks need
  Developer Mode or an elevated shell with `core.symlinks=true` (per
  the spec's known platform limitation, documented in the workspace
  README).

## [0.8.0] — 2026-04-19

### Added
- **Jekyll documentation site** under `docs/` — landing page
  (`index.md`), `getting-started.md`, and auto-imported `commands/`
  pages (one per top-level command, plus a `Commands` parent index).
  Styled with the same just-the-docs `dark-terminal` theme + `_sass`
  overlay used by culture / agentic-human / agentic-guides so the
  agentic sites share a visual identity. Builds cleanly via
  `bundle exec jekyll build`.
- **`scripts/sync_skill_md.py`** — reuses the in-repo
  `skill_loader.load_skill` to strip each command's agex-flavored YAML
  frontmatter and emit a Jekyll-friendly one (`title`, `layout`,
  `parent`, `nav_order`). Iterates `src/agent_experience/commands/` in
  sorted order; writes with `encoding="utf-8"`. Lessons
  (`learn/assets/topics/*`) stay in CLI territory for v0.1.
- **`.github/workflows/docs.yml`** — triggers on `docs/**`,
  `commands/**/SKILL.md`, `skill_loader.py`, the sync script, and the
  workflow itself. Runs `sync_skill_md.py` before building so the
  deployed site cannot drift from the CLI's shipped docs. Deploys to
  Cloudflare Pages (project `agex`) on push-to-main only — PRs never
  deploy.

### Changed
- Swapped the plan's reference from `cloudflare/pages-action@v1` (now
  archived / DEPRECATED upstream) to `cloudflare/wrangler-action@v3`
  with `pages deploy`. All third-party actions SHA-pinned with
  trailing `# vN` comments per project convention.

### Notes
- The Cloudflare Pages project (`agex`) and the `agex.culture.dev`
  custom-domain binding require a one-time manual setup step in the
  Cloudflare dashboard; the workflow expects `CLOUDFLARE_API_TOKEN`
  and `CLOUDFLARE_ACCOUNT_ID` repo secrets. Tracked separately.

## [0.7.0] — 2026-04-19

### Added
- **Unknown-command routing** — invoking `agex <unknown>` (e.g.,
  `agex frobnicate`) now prints a one-line
  `agex: error: unknown command '<name>'` to stderr, emits the body of
  `agex explain agex` to stdout (so the agent immediately sees the full
  command list), and exits with code 2. Previously Typer's default
  "No such command" message was emitted with no recovery guidance.
  Implemented via a thin `_main_entrypoint` wrapper in `cli.py` and a
  new `agent_experience/__main__.py` so `python -m agent_experience`
  routes through the same handler as the `agex` console script.
- **SKILL.md consistency meta-test** — `tests/test_skill_md_consistency.py`
  parametrizes over every `SKILL.md` shipped under the `commands/`
  package and asserts valid frontmatter (`name`, `description`,
  `type ∈ {command, lesson}`). A companion guard test
  (`test_meta_test_discovers_all_known_skills`) fails loudly if the
  resource-discovery glob returns fewer than the expected 9 files, so
  a future packaging regression cannot silently turn every parametrize
  case into a zero-item pass-through. 15 new tests total.

### Changed
- `pyproject.toml` script entry flipped from
  `agent_experience.cli:app` to `agent_experience.cli:_main_entrypoint`
  so the unknown-command router runs before Typer's dispatcher.

### Fixed
- **#12** — `agex hook write` on Windows + Python 3.13 occasionally
  aborted with `portalocker.exceptions.AlreadyLocked` when two
  concurrent writers raced for the append lock (the kernel surfaces
  `EDEADLK` from `msvcrt.locking()`; portalocker maps it to
  `AlreadyLocked`). `core/hook_io.append_event` now retries up to
  `_LOCK_MAX_ATTEMPTS = 5` times with jittered linear backoff
  (`10ms × attempt + up to 10ms of jitter`), re-raising only if every
  attempt fails. Two deterministic regression tests monkeypatch
  `portalocker.lock` to simulate the flake and verify both the
  recovery and the final-giveup paths.

## [0.6.0] — 2026-04-19

### Added
- Minimal **stub probes** for the three remaining v0.1 backends:
  - `codex` — records the `AGENTS.md` path in
    `ProbeResult.claude_md` if present (field name reused pending a
    future `project_memory` rename); the probe does not read the
    file's contents. Further discovery deferred.
  - `copilot` — empty `ProbeResult()`; full discovery tracked as an
    open issue.
  - `acp` — empty `ProbeResult()`; full discovery tracked as an open
    issue.
- **Capability matrix data** under
  `src/agent_experience/backends/capabilities/` — one YAML per backend
  (`claude-code.yaml`, `codex.yaml`, `copilot.yaml`, `acp.yaml`)
  keyed by the four v0.1 capability facets (`hooks`, `mcp`, `skills`,
  `agents`) plus a `*_alternative` free-text field for unsupported
  ones. These YAMLs are loadable by the existing
  `core/capabilities.py::CapabilityMatrix.load(...)` API; callers that
  wire up capability-based routing (e.g., `learn.py`) land in a later
  phase.
- **Backend-specific overview YAMLs** for `codex`, `copilot`, `acp`
  under `commands/overview/assets/backends/` — mirror the `claude-
  code.yaml` shape so `agex overview --agent <backend>` renders a
  consistent snapshot across all four backends.

### Changed
- `commands/overview/scripts/overview.py` registers all four probes in
  `_PROBES`; the interim `if backend in _PROBES / else empty
  ProbeResult` fallback from Phase 4 is removed (every backend now has
  a probe, so the dead branch + stale "Phase 8 will..." comment are
  gone). `run(backend)` is now a direct dict lookup.

### Tests
- `tests/backends/test_stub_probes.py` — 4 new smoke tests exercising
  the three stub probes (codex empty + codex AGENTS.md + copilot
  empty + acp empty).
- `tests/commands/test_gamify.py` adds one regression test pinning
  that `agex gamify --agent codex` returns exit 0 with an
  "unsupported"-notice in stdout and does **not** create `.claude/`
  on disk (spec invariant #5: unsupported is success, no side
  effects).
- 66 tests passing (was 61 on 0.5.0).

## [0.5.0] — 2026-04-19

### Added
- `agex gamify --agent claude-code` — installs Claude Code hook
  fragments (tagged `agex:post-tool-use`, `agex:user-prompt`,
  `agex:stop`) into `.claude/hooks.json` so every tool use, prompt,
  and stop event calls `agex hook write`. Preserves user-authored
  hooks already in the file. Idempotent: re-running is a byte-
  identical no-op (the `[installed.gamify].at` timestamp is only
  rewritten when the fragment set actually changes).
- `agex gamify --uninstall --agent claude-code` — surgical removal:
  only entries whose `id` is tracked in `.agex/config.toml`'s
  `[installed.gamify].hook_fragment_ids` are stripped; user entries
  survive. Empty event arrays are deleted. The `gamify` record is
  popped from config.
- `commands/gamify/` skill-folder (`SKILL.md` doubles as
  `agex explain gamify`; `assets/hooks/claude-code.json` carries the
  three shipped fragments).
- Unsupported-backend path returns a markdown notice + issue-tracker
  link at exit 0 (spec invariant #5).
- 58 tests passing (53 from 0.4.0 + 4 plan tests + 1 corrupt-hooks-
  file guard).

### Safety
- Malformed `.claude/hooks.json` is NOT silently overwritten — the
  file is left untouched and `agex gamify` exits 2 with a clear
  stderr message pointing at the file. This is the first agex
  command with real side effects on the user's project; the error
  path was designed to make accidental data loss impossible.

## [0.4.0] — 2026-04-18

### Added
- `agex hook write <event> [key=value ...]` — append a JSON line with a
  UTC ISO timestamp + parsed `key=value` pairs to
  `.agex/data/<event>.json`. Silent, safe for concurrent invocation via
  `portalocker`. Empty keys (`=foo`) are dropped; the positional
  `<event>` always wins over any `event=...` pair.
- `agex hook read --agent <backend>` — render `.agex/data/*.json` as a
  markdown table with `ts | event | details` columns, one section per
  known stream (`post-tool-use`, `user-prompt`, `stop`, `sessions`).
  Empty streams show `_no events_`.
- `commands/hook/` skill-folder (`SKILL.md` doubles as
  `agex explain hook`; `assets/table.md.j2` for the read template).
- Typer sub-app pattern — `hook` is wired via `app.add_typer(...)` with
  two subcommands (`write` and `read`).
- 51 tests passing (46 from 0.3.0 + 3 CLI tests + 1 empty-key guard
  test + 1 malformed-JSON warning test); overall coverage 96%.

### Changed
- `core/hook_io.load_events` now catches `json.JSONDecodeError` on each
  line and emits a `warnings.warn(...)` instead of raising, keeping
  `agex hook read` read-only even when a `.agex/data/*.json` file is
  partially written or externally edited.

## [0.3.0] — 2026-04-18

### Added
- `agex learn [topic] --agent <backend>` — menu of available lessons
  without a topic, or teaches one with a topic. Lessons emit a
  Jinja-rendered markdown body plus an inline backend-native skill
  template the agent can write into the project itself. Rejects
  path-traversal topic arguments via the same `^[a-z][a-z0-9-]*$`
  whitelist as `agex explain`.
- Four v0.1 lessons under `commands/learn/assets/topics/`:
  `introspect`, `visualize`, `gamify` (bundles the `levelup` template),
  and `levelup`. Each ships with a `claude-code` skill template;
  Phase 8 will route non-claude-code backends through `capabilities.py`.
  The `gamify` and `levelup` lessons reference `agex gamify` and
  `agex hook read` which land in Phase 6/7 — both lessons carry an
  explicit "Preview" note until those commands ship.
- `commands/learn/` skill-folder (`SKILL.md` doubles as
  `agex explain learn`; `assets/menu.md.j2` for the topic menu).
- `tests/commands/test_learn.py` with 7 tests including a
  path-traversal guard mirroring the `explain` precedent. 46 tests
  passing total; overall coverage 97%.

## [0.2.0] — 2026-04-18

### Added
- `agex overview --agent claude-code` — deterministic markdown snapshot of
  a project's Claude Code setup (CLAUDE.md, skills, hooks, MCP, settings).
  Read-only except for first-run `.agex/` init. Unknown backends currently
  render as an empty snapshot; Phase 8 will route them to the
  unsupported-notice markdown.
- `backends/claude_code/probe.py` — `ProbeResult` dataclass + `probe()`
  that reuses `core/skill_loader.load_skill` for frontmatter parsing and
  records per-file warnings on malformed inputs instead of raising.
- `commands/overview/` skill-folder (`SKILL.md`, Jinja template,
  per-backend YAML). The `SKILL.md` doubles as `agex explain overview`.
- CLI `_agent_option()` helper and `@app.command("overview")` wiring.
- Test fixtures under `tests/fixtures/claude-code/` (`empty/`, `typical/`,
  `malformed/`). Probe test coverage 100%; overall project 98%.

### Changed
- Renamed PyPI distribution from `agent-experience` to `agex-cli` (CLI
  entry point stays `agex`); renamed GitHub repo from
  `OriNachum/agent-experience` to `OriNachum/agex`; updated issue and
  repo URLs, Homepage (`agex.culture.dev`), and SonarCloud project key
  (`OriNachum_agex`).
