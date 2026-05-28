# `agex` — agent-operated developer-experience CLI

`agex` is a non-agentic Python CLI that emits deterministic per-backend markdown for autonomous agents. You (the agent) invoke it from your shell tool to learn about and configure your own runtime.

## Commands

| Command | Purpose |
|---|---|
| `agex overview --agent X` | Snapshot of the project's current setup for backend X. |
| `agex learn --agent X` | Menu of lesson topics available for backend X. |
| `agex learn <topic> --agent X` | Teach a lesson (e.g., introspect, visualize, gamify, levelup). |
| `agex gamify --agent X` | Install usage-tracking hooks (or unsupported notice). |
| `agex gamify --uninstall --agent X` | Reverse `gamify`. |
| `agex hook write <event> [...]` | Append a tracking event. Called by installed hooks. |
| `agex hook read --agent X` | Show tracked events as markdown + source path. |
| `agex doctor` | Diagnose agex install + repo setup. |
| `agex explain <topic>` | You're reading this. |

## First steps

```bash
agex explain agex              # this page
agex doctor                    # is the install + repo healthy?
agex learn --agent claude-code  # what can I learn for my backend?
agex overview --agent claude-code  # what's in this project?
```

## Design invariants

- **Non-agentic.** Zero LLM calls inside agex. All output is deterministic.
- **Markdown is the universal format.** No `--json` flag.
- **`--agent` is required** on backend-sensitive commands.
- **Unsupported is success.** If your backend lacks a feature, you get a markdown notice + link to file an issue — exit code 0.

## Repo

<https://github.com/agentculture/devex>
