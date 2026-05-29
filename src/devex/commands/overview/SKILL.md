---
name: overview
description: Render a descriptive markdown snapshot of the project's current agent setup.
type: command
---

# `devex overview --agent <backend>`

Call this to get a read-only markdown snapshot of what's configured in the
current project for a given backend — skills, hooks, agents, MCP servers,
and relevant config files. Descriptive, not diagnostic. Read it before you
act.

## From your shell tool

```bash
devex overview --agent claude-code
devex overview --agent codex
```

## What you get

Markdown sections: Project root, `CLAUDE.md`/`AGENTS.md` presence, Skills,
Hooks, MCP servers, Settings.

## Notes

- Malformed files are skipped with a `> ⚠️` inline warning.
- Read-only except first-run `.devex/` init.
- Build diagnostic logic (gaps, recommendations) into an agent-authored skill:
  `devex learn introspect --agent <backend>`.
