# `devex` — agent-operated developer-experience CLI

`devex` is a non-agentic Python CLI that emits deterministic per-backend markdown for autonomous agents. You (the agent) invoke it from your shell tool to learn about and configure your own runtime.

> `agex` is the legacy command name and still works as an alias — every `devex …` invocation below can be typed `agex …`.

## Commands

| Command | Purpose |
|---|---|
| `devex overview --agent X` | Snapshot of the project's current setup for backend X. |
| `devex learn --agent X` | Menu of lesson topics available for backend X. |
| `devex learn <topic> --agent X` | Teach a lesson (e.g., introspect, visualize, gamify, levelup). |
| `devex gamify --agent X` | Install usage-tracking hooks (or unsupported notice). |
| `devex gamify --uninstall --agent X` | Reverse `gamify`. |
| `devex hook write <event> [...]` | Append a tracking event. Called by installed hooks. |
| `devex hook read --agent X` | Show tracked events as markdown + source path. |
| `devex doctor` | Diagnose devex install + repo setup. |
| `devex explain <topic>` | You're reading this. |

## First steps

```bash
devex explain devex             # this page
devex doctor                    # is the install + repo healthy?
devex learn --agent claude-code  # what can I learn for my backend?
devex overview --agent claude-code  # what's in this project?
```

## Design invariants

- **Non-agentic.** Zero LLM calls inside devex. All output is deterministic.
- **Markdown is the universal format.** No `--json` flag.
- **`--agent` is required** on backend-sensitive commands.
- **Unsupported is success.** If your backend lacks a feature, you get a markdown notice + link to file an issue — exit code 0.

## Repo

<https://github.com/agentculture/devex>
