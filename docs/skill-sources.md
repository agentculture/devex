# Vendored skills — upstream provenance

This file records where the skills under `.claude/skills/` came from, so future
resync broadcasts have a clear provenance entry to point at. Per the AgentCulture
[cite-don't-import policy](https://github.com/agentculture/guildmaster/blob/main/docs/skill-sources.md),
agex-cli owns its copies and may diverge — divergence is recorded here and in the
relevant `SKILL.md` frontmatter `description`.

**Supplier:** as of the completed **steward → guildmaster cutover**
([guildmaster `docs/cutover.md`](https://github.com/agentculture/guildmaster/blob/main/docs/cutover.md)),
[`guildmaster`](https://github.com/agentculture/guildmaster) is the mesh's sole
skill supplier and broadcaster (via `guild teach` / `guild onboard`). It owns the
canonical upstream copies and the supplier ledger; `steward` has retreated to
agent-alignment and no longer broadcasts. agex-cli re-syncs from guildmaster.
Skills marked **origin = devague** are authored in
[`devague`](https://github.com/agentculture/devague) and re-broadcast by
guildmaster — cite guildmaster's copy, track devague as origin.

The full vendored kit was synced from guildmaster via
[#58](https://github.com/agentculture/agex-cli/issues/58).

## Canonical skills (upstream = `guildmaster`)

| Skill | Path | Upstream (canonical) | Divergence | Resync issue |
|-------|------|----------------------|------------|--------------|
| `agent-config` | `.claude/skills/agent-config/` | [`guildmaster/.claude/skills/agent-config/`](https://github.com/agentculture/guildmaster/tree/main/.claude/skills/agent-config) | Verbatim (already carries `type: command`). Inventory variant backing `guild show`; ships `scripts/show.sh` + `data/backend-fingerprints.yaml`. | [#58](https://github.com/agentculture/agex-cli/issues/58) |
| `cicd` | `.claude/skills/cicd/` | [`guildmaster/.claude/skills/cicd/`](https://github.com/agentculture/guildmaster/tree/main/.claude/skills/cicd) | Adapted-thin: agex-cli owns `agex pr`, so `workflow.sh` delegates every verb to the native command and guildmaster's `status`/`await` extensions + `_resolve-nick.sh` / `pr-reply.sh` / `portability-lint.sh` helpers are dropped (only `workflow.sh` remains). Remaining `pr-status.sh` extras tracked in [#52](https://github.com/agentculture/agex-cli/issues/52). | [#58](https://github.com/agentculture/agex-cli/issues/58) (first vendored [#51](https://github.com/agentculture/agex-cli/issues/51)) |
| `communicate` | `.claude/skills/communicate/` | [`guildmaster/.claude/skills/communicate/`](https://github.com/agentculture/guildmaster/tree/main/.claude/skills/communicate) | Identifier-only (frontmatter `description` says "from agex-cli"). Scripts current as of steward 0.18.0. | [#58](https://github.com/agentculture/agex-cli/issues/58) (first vendored [#36](https://github.com/agentculture/agex-cli/issues/36)) |
| `doc-test-alignment` | `.claude/skills/doc-test-alignment/` | [`guildmaster/.claude/skills/doc-test-alignment/`](https://github.com/agentculture/guildmaster/tree/main/.claude/skills/doc-test-alignment) | Verbatim + `type: command` added (agex-cli loader requires `name`+`description`+`type`; guildmaster's copy omits it). **Stub** — `scripts/check.sh` exits not-yet-implemented; treat any green exit as a bug. | [#58](https://github.com/agentculture/agex-cli/issues/58) |
| `pypi-maintainer` | `.claude/skills/pypi-maintainer/` | [`guildmaster/.claude/skills/pypi-maintainer/`](https://github.com/agentculture/guildmaster/tree/main/.claude/skills/pypi-maintainer) | Verbatim + `type: command` added. Switches a PyPI package between pypi / test-pypi / local. | [#58](https://github.com/agentculture/agex-cli/issues/58) |
| `run-tests` | `.claude/skills/run-tests/` | [`guildmaster/.claude/skills/run-tests/`](https://github.com/agentculture/guildmaster/tree/main/.claude/skills/run-tests) | Verbatim + `type: command` added. Coverage source resolves from `[tool.coverage.run]`, so portable without edits. | [#58](https://github.com/agentculture/agex-cli/issues/58) |
| `sonarclaude` | `.claude/skills/sonarclaude/` | [`guildmaster/.claude/skills/sonarclaude/`](https://github.com/agentculture/guildmaster/tree/main/.claude/skills/sonarclaude) | Verbatim + `type: command` added. SonarCloud API client; project key from `$SONAR_PROJECT` or `--project`. | [#58](https://github.com/agentculture/agex-cli/issues/58) |
| `version-bump` | `.claude/skills/version-bump/` | [`guildmaster/.claude/skills/version-bump/`](https://github.com/agentculture/guildmaster/tree/main/.claude/skills/version-bump) | Verbatim + `type: command` added. Pure-Python; bumps `pyproject.toml` (single source of truth here) + prepends a Keep-a-Changelog entry. The `__init__.py` rewrite is a no-op — agex-cli reads `__version__` from package metadata. | [#58](https://github.com/agentculture/agex-cli/issues/58) |

## Inbound workflow skills (origin = `devague`, re-broadcast via `guildmaster`)

These three flow the **opposite** direction of guildmaster's supplier role:
[`devague`](https://github.com/agentculture/devague) authors them and guildmaster
re-broadcasts. They are the `idea → spec → plan → implement` operators for the
deterministic `devague` CLI. agex-cli cites guildmaster's copy; the origin/upstream
for resync is devague (`../devague/.claude/skills/<name>/`). Pinned at devague
`0.11.1`. Runtime dep: `uv tool install devague` (and for `assign-to-workforce`,
also `git worktree` + the vendored `cicd` skill for the gate-3 `agex pr open`).

> **Note on planning conventions.** agex-cli's own design docs use the
> `docs/superpowers/` specs/plans convention; the devague trio is an alternative
> idea→spec→plan→implement workflow vendored for mesh parity. Both coexist.

| Skill | Path | Origin (author) | Divergence | Resync issue |
|-------|------|-----------------|------------|--------------|
| `think` | `.claude/skills/think/` | [`devague/.claude/skills/think/`](https://github.com/agentculture/devague/tree/main/.claude/skills/think) | `type: command` (added upstream by guildmaster; absent in devague). Verbatim otherwise. | [#58](https://github.com/agentculture/agex-cli/issues/58) |
| `spec-to-plan` | `.claude/skills/spec-to-plan/` | [`devague/.claude/skills/spec-to-plan/`](https://github.com/agentculture/devague/tree/main/.claude/skills/spec-to-plan) | `type: command` (added upstream by guildmaster). Verbatim otherwise. | [#58](https://github.com/agentculture/agex-cli/issues/58) |
| `assign-to-workforce` | `.claude/skills/assign-to-workforce/` | [`devague/.claude/skills/assign-to-workforce/`](https://github.com/agentculture/devague/tree/main/.claude/skills/assign-to-workforce) | `type: command` (added upstream by guildmaster). Verbatim otherwise. | [#58](https://github.com/agentculture/agex-cli/issues/58) |

## Resync workflow

When a `guild teach` resync broadcast arrives for `<name>`:

1. Branch `skill/<name>-resync` (or batch several under one branch).
2. `cp -R <guildmaster-checkout>/.claude/skills/<name> .claude/skills/` (where
   `<guildmaster-checkout>` is your local clone of
   [`agentculture/guildmaster`](https://github.com/agentculture/guildmaster) —
   for the devague trio, re-sync instead from `../devague/.claude/skills/<name>/`).
3. `chmod +x .claude/skills/<name>/scripts/*` .
4. Re-apply the divergence recorded above (the `type: command` addition for any
   skill guildmaster ships without it; the identifier / adapted-thin edits for
   `communicate` / `cicd`).
5. Bump `pyproject.toml` per project convention.
6. Add a CHANGELOG entry.
7. Open PR; post a comment on the resync issue with the PR link via
   `bash .claude/skills/communicate/scripts/post-comment.sh`.

## Nick

`culture.yaml` at the repo root sets `suffix: agex-cli`. `agtag` (used
by `communicate`) and `agex pr` (which `cicd` delegates to) both read
that file to resolve the signing nick. Auto-emitted signatures are
`- agex-cli (Claude)`.
