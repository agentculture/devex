---
name: visualize
description: At-a-glance snapshot of the project's agent setup — counts only, compact.
type: command
---

# Visualize

When the user says "what do I have", "show the setup", or similar.

## Process

1. `devex overview --agent claude-code`
2. Emit a compact block: `Skills: N · Hooks: M · MCP: K · CLAUDE.md: ✓/✗`
3. Stop. No recommendations, no prose paragraphs.

## Rule

Target < 500 output tokens. If you can't fit the summary, trim further.
