# Vendored skills — upstream provenance

This file records where the skills under `.claude/skills/` came from, so future
resync broadcasts (steward auto-files one per skill update) have a clear
provenance entry to point at. Per the AgentCulture
[cite-don't-import policy](https://github.com/agentculture/steward/blob/main/docs/skill-sources.md),
agex-cli owns its copies and may diverge — divergence is recorded in the
relevant `SKILL.md` frontmatter `description`.

| Skill | Path | Upstream (canonical) | Divergence | Resync issue |
|-------|------|----------------------|------------|--------------|
| `communicate` | `.claude/skills/communicate/` | [`steward/.claude/skills/communicate/`](https://github.com/agentculture/steward/tree/main/.claude/skills/communicate) | Identifier-only (frontmatter `description` says "from agex-cli"). | [#36](https://github.com/agentculture/agex-cli/issues/36) |
| `cicd` | `.claude/skills/cicd/` | [`steward/.claude/skills/cicd/`](https://github.com/agentculture/steward/tree/main/.claude/skills/cicd) | Adapted-thin: agex-cli owns `agex pr`, so `workflow.sh` delegates every verb to the native command and the steward `status`/`await` extensions + `_resolve-nick.sh` / `pr-reply.sh` / `portability-lint.sh` helpers are dropped (only `workflow.sh` remains). Remaining `pr-status.sh` extras tracked in [#52](https://github.com/agentculture/agex-cli/issues/52). | [#51](https://github.com/agentculture/agex-cli/issues/51) |

## Resync workflow

When an issue arrives titled "Resync vendored `<name>` skill from steward":

1. Branch `skill/<name>-resync`.
2. `cp -R <steward-checkout>/.claude/skills/<name> .claude/skills/` (where
   `<steward-checkout>` is your local clone of
   [`agentculture/steward`](https://github.com/agentculture/steward)).
3. `chmod +x .claude/skills/<name>/scripts/*.sh`.
4. Re-apply identifier adaption (see the divergence column above).
5. Bump `pyproject.toml` per project convention.
6. Add a CHANGELOG entry.
7. Open PR; post a comment on the resync issue with the PR link via
   `bash .claude/skills/communicate/scripts/post-comment.sh`.

## Nick

`culture.yaml` at the repo root sets `suffix: agex-cli`. `agtag` (used
by `communicate`) and `agex pr` (which `cicd` delegates to) both read
that file to resolve the signing nick. Auto-emitted signatures are
`- agex-cli (Claude)`.
