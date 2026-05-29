---
name: introspect
description: Build an agent-native introspect skill that audits your project setup and suggests next steps.
type: lesson
---

# Lesson — build an `introspect` skill for {{ backend }}

## What you'll end up with

A backend-native skill (for {{ backend }}) that:
1. Calls `devex overview --agent {{ backend }}` to read the project's current state.
2. Identifies gaps (missing CLAUDE.md, no skills, no hooks, etc.).
3. Suggests the next one or two improvements you could apply.
4. Is small enough that invoking it doesn't blow your context budget.

## Why build it instead of shipping it

Two reasons: (1) each agent backend has its own native skill format, so no shipped skill fits perfectly; (2) you and the user stay in control of what gets installed into the project.

## Step 1 — review the `devex overview` output

Run `devex overview --agent {{ backend }}` now. Note which sections are empty — those are your candidate gaps.

## Step 2 — create the skill file

Write the file shown below to the path noted above its fence. Adjust the prose/tone to your project's voice.

### `.claude/skills/introspect/SKILL.md`

```markdown
{{ skill_template_body }}
```

## Step 3 — try it

Invoke `/introspect` (or equivalent) in your runtime. Read the output, apply one suggestion.

## Why one suggestion at a time

Agents that shove 10 recommendations into one turn overwhelm the user. The skill you just built is explicitly capped at two — if you want more later, iterate.

{{ footer }}
