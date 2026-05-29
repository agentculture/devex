---
name: hook
description: Write and read devex tracking events.
type: command
---

# `devex hook write <event> [key=value ...]` / `devex hook read --agent <backend>`

## `write`

Called by installed hooks (see `devex gamify`, Phase 7). Appends a JSON line to `.devex/data/<event>.json`. Silent. Safe for concurrent invocation (file locking via `portalocker`).

```bash
devex hook write post-tool-use tool=Read
```

## `read`

Renders tracked events as a markdown table. Prints the source JSON path for deeper inspection.

```bash
devex hook read --agent claude-code
```

## Notes

- Event names are free-form; conventional names: `post-tool-use`, `user-prompt`, `stop`, `sessions`.
- Extra positional `key=value` pairs are captured into the payload. Empty keys (e.g., `=foo`) are dropped.
- Timestamp (`ts`) is attached automatically; a positional `ts=<value>` overrides it (useful for replays).
- The positional `<event>` name is authoritative — it always wins over any `event=...` pair in args.
- Malformed JSON lines in `.devex/data/*.json` (e.g., from a partial write) are skipped with a warning on `hook read`, not raised.
