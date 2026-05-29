---
name: visualize
description: Build a skill that renders a compact visual of your agent setup.
type: lesson
---

# Lesson — build a `visualize` skill for {{ backend }}

Same shape as introspect, but the output optimizes for *at-a-glance* rather than recommendations. The skill runs `devex overview --agent {{ backend }}`, compresses it into a tight markdown block (counts only, with a token target of < 500 output tokens), and echoes it for situational awareness.

## Step 1 — understand the goal

Run `devex overview --agent {{ backend }}` now. Note the counts of skills, hooks, MCP integrations, and CLAUDE.md status. The visualize skill will display these as a one-liner for quick reference.

## Step 2 — create the skill file

Write the file shown below to the path noted above its fence. This skill is intentionally minimal — no prose, no recommendations.

### Skill template — `.claude/skills/visualize/SKILL.md`

```markdown
{{ skill_template_body }}
```

## Step 3 — invoke it

Say "what do I have" or "show the setup" and invoke `/visualize` (or equivalent). You'll get a compact status bar.
