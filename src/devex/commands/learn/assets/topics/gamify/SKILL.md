---
name: gamify
description: Install usage tracking hooks and build a levelup skill to advise the user.
type: lesson
---

# Lesson — set up gamification for {{ backend }}

Two parts:

## Part 1 — install the tracking hooks

Run in your shell tool:

```bash
devex gamify --agent {{ backend }}
```

This writes backend-native hook fragments that call `devex hook write <event>` whenever you use a tool, submit a prompt, or stop. The events land in `.devex/data/`.

To uninstall: `devex gamify --uninstall --agent {{ backend }}`.

## Part 2 — build the `levelup` skill

The hook data is inert without something to surface it. Build the levelup skill described in `devex learn levelup --agent {{ backend }}`, or copy its skill template directly:

### `.claude/skills/levelup/SKILL.md`

```markdown
{{ skill_template_body }}
```

## After both parts

Use your runtime normally for a few sessions. Then invoke `/levelup` — it will read the tracking data via `devex hook read` and advise the user.

{{ footer }}
