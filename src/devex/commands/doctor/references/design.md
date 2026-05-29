# `doctor` — design notes

Internal reference for maintainers. Not emitted at runtime.

## Categories

| Category | Checks |
|---|---|
| Install | `devex` version resolves, Python ≥ 3.10, package resources reachable. |
| Project state | `.devex/` dir, `config.toml` parses, `.gitignore` matches `GITIGNORE_CONTENT`, `data/` writable. |
| Internal consistency | every shipped `SKILL.md` parses, every per-backend capability YAML loads. |

## Statuses

- `ok` — green; check passed.
- `warn` — non-fatal anomaly. Exit code stays `0`.
- `fail` — hard failure. Exit code `1`, plus a one-line stderr summary.
- `info` — neutral observation (e.g. `.devex/` not initialized — that's not a problem in a fresh project).

## Read-only contract

`doctor` must never write. It deliberately does **not** call `core.paths.ensure_init()`. New checks should use `os.access(..., os.W_OK)` or pure read paths — never probe writability with an actual write.

## Role-flag contract

`devex doctor --role <slug>` renders the contents of `assets/roles/<slug>.md.j2` (validated against `^[a-z][a-z0-9-]*$`) as an extra section after Operator verification.

The role asset is a Jinja template, but v0.1 passes no extra context — keep role files static markdown until a use case justifies the coupling. Unknown role → exit `2` with a stderr message.

## Adding a check

1. Add a `_check_<name>() -> CheckResult` function in `scripts/doctor.py`.
2. Append it to the appropriate `Category` in `_build_categories()`.
3. Cover it in `tests/commands/test_doctor.py`.

Keep each check small, side-effect-free, and tolerant of partial state — return `info` when the precondition (e.g. presence of `.devex/`) isn't met rather than `fail`.
