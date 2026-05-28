# agex

Agent-operated developer-experience CLI. Non-agentic, deterministic, markdown-first. The same wheel is published on PyPI under three distribution names — `agex-cli` (canonical), `agent-devex`, and `devex-cli` — and installs two equivalent commands, `agex` and `devex` (emitted output reflects whichever name you invoke).

## Install

```bash
uv tool install agex-cli      # or: devex-cli
# or
pipx install agex-cli         # or: pipx install devex-cli
```

## Quick start

```bash
agex explain agex
agex overview --agent claude-code
agex learn --agent claude-code
```

## Docs

[culture.dev/agex](https://culture.dev/agex/).

Spec: `docs/superpowers/specs/2026-04-18-agex-design.md`.

## License

MIT.
