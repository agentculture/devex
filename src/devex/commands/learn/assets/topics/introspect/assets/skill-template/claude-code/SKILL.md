---
name: introspect
description: Audit the current project's agent setup and suggest 1-2 next improvements.
type: command
---

# Introspect

When the user asks to audit the agent setup, improve it, or "what should I add", invoke this skill.

## Process

1. Run in your shell tool: `devex overview --agent claude-code`
2. Read the output. Count what exists under each section (skills, hooks, MCP, settings).
3. Identify the two weakest sections — the ones most likely to unblock a real workflow next.
4. Emit a short markdown reply: what's missing, why it matters, what adding it costs.

## Rules

- Cap suggestions at 2.
- No "nice-to-haves." Only suggestions that unblock something concrete.
- Don't install anything. Advise only.
