---
name: levelup
description: Build a skill that reads devex usage data and advises the user.
type: lesson
---

# Lesson — build the `levelup` skill for {{ backend }}

> **Preview:** This lesson depends on `devex gamify` (Phase 7) and `devex hook read` (Phase 6); neither is available in devex 0.3.0. Treat the steps below as a design preview — the emitted skill template won't have real data to read until those commands ship.

Prerequisite: you've run `devex gamify --agent {{ backend }}` so there's data to read.

## Step 1 — understand the data source

Run `devex hook read --agent {{ backend }}` now. You'll see a JSON list of events (tool calls, prompts submitted, stops). The levelup skill will parse this and suggest one area for improvement.

## Step 2 — create the skill file

Write the file shown below to the path noted above its fence. This skill reads the tracking data and offers one concrete suggestion per invocation.

### Skill template — `.claude/skills/levelup/SKILL.md`

```markdown
{{ skill_template_body }}
```

## Step 3 — try it after a few sessions

Use your runtime normally for a few turns. Then invoke `/levelup` to see what the skill suggests.

See also: `devex learn gamify --agent {{ backend }}` (bundles the full setup).

{{ footer }}
