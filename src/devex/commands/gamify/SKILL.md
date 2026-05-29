---
name: gamify
description: Install or uninstall backend-native hooks that track usage via devex hook write.
type: command
---

# `devex gamify --agent <backend>` / `devex gamify --uninstall --agent <backend>`

## What it does

Writes backend-native hook fragments (each tagged with a stable `agex:*` ID) that call `devex hook write <event>` on PostToolUse, UserPromptSubmit, and Stop events. Agent-authored skills (e.g., `levelup`) read the accumulated data via `devex hook read`.

## Why it's safe

- Idempotent: re-running is a no-op.
- Reversible: `--uninstall` removes exactly the `agex:*` fragments; user-authored hooks are untouched.
- Calling `devex gamify` explicitly is the confirmation — no separate prompt.

## Unsupported backends

If your backend doesn't support hooks, you get a markdown notice + issue link instead.

## From your shell tool

```bash
devex gamify --agent claude-code
# ... use your runtime for a while ...
devex hook read --agent claude-code
# ... later, to undo:
devex gamify --uninstall --agent claude-code
```
