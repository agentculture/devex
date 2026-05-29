# devex

Agent-operated developer-experience CLI. Non-agentic, deterministic, markdown-first. The same wheel is published on PyPI under three distribution names — `devex-cli` (canonical), `agent-devex`, and `agex-cli` (the legacy canonical name, still published) — and installs two equivalent commands, `devex` (canonical) and `agex` (legacy alias) (emitted output reflects whichever name you invoke).

## Install

```bash
uv tool install devex-cli      # or: agex-cli
# or
pipx install devex-cli         # or: pipx install agex-cli
```

## Quick start

```bash
devex explain devex
devex overview --agent claude-code
devex learn --agent claude-code
```

## Docs

[culture.dev/devex](https://culture.dev/devex/).

Spec: `docs/superpowers/specs/2026-04-18-agex-design.md`.

## License

MIT.
