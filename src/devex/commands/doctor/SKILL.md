---
name: doctor
description: Diagnose the devex install and the current project's `.devex/` state with a deterministic markdown health report.
type: command
---

# `devex doctor`

Run a zero-argument health check across:

1. **Install** — `devex` version, Python version, package resources are reachable.
2. **Project state** — whether `.devex/` exists in the current directory; if it does, that `config.toml` parses, `.gitignore` matches the managed content, and `data/` is writable.
3. **Internal consistency** — every shipped `commands/*/SKILL.md` parses with the required frontmatter, every per-backend capability YAML loads.
4. **Operator verification** — a short markdown checklist of things `doctor` cannot verify automatically (network reach, git-tracking of `.devex/config.toml`, agent shell-tool wiring).

`doctor` is strictly read-only. It will never create `.devex/` or write anywhere on disk — if the directory is missing, that is reported as info and the command keeps going.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | All checks `ok`, possibly with `warn` rows. |
| `1` | At least one `fail` row. Stderr carries a one-line summary. |
| `2` | CLI usage error (e.g., unknown role passed via `--role`). |

## From your shell tool

```bash
devex doctor                       # base health check
devex doctor --role pr-review      # base + role-specific checks (when a role file ships)
```

## Role-specific checks

`doctor` has an extension hook: a role file at `commands/doctor/assets/roles/<role>.md.j2` (slug-validated, `^[a-z][a-z0-9-]*$`) is rendered as an extra section when the user passes `--role <role>`. The current release ships zero role files — the contract exists so role-specific diagnostics can be added without touching `doctor` itself.

## What `doctor` does *not* do

- It does not run backend probes — that's `devex overview --agent X`.
- It does not perform any auto-fix. Recovery instructions are emitted as markdown for the operator (agent or human) to act on.
- It does not touch the network.
