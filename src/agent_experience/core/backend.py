from enum import Enum
from pathlib import Path

import yaml


class Backend(str, Enum):
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    COPILOT = "copilot"
    ACP = "acp"


# Accepted aliases that are not enum values themselves.  The AgentCulture
# standard culture.yaml uses `backend: claude`, so map it onto claude-code.
_ALIASES = {"claude": Backend.CLAUDE_CODE}

# Human-facing list of accepted values, shared by every error message so
# they never drift.  Aliases are shown next to their canonical value.
_VALID_DISPLAY = "claude (= claude-code), codex, copilot, acp"


def parse_backend(value: str) -> Backend:
    if value in _ALIASES:
        return _ALIASES[value]
    try:
        return Backend(value)
    except ValueError:
        raise ValueError(f"unknown backend '{value}' (one of: {_VALID_DISPLAY})") from None


def resolve_backend(arg: str | None, project_dir: Path) -> Backend:
    """Resolve --agent: explicit arg wins, else first agent's backend
    in culture.yaml, else raise.
    """
    if arg is not None:
        return parse_backend(arg)
    culture = project_dir / "culture.yaml"
    if culture.exists():
        try:
            data = yaml.safe_load(culture.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
        agents = data.get("agents") or []
        if agents and isinstance(agents[0], dict):
            backend_value = agents[0].get("backend")
            if backend_value:
                try:
                    return parse_backend(backend_value)
                except ValueError:
                    suffix = agents[0].get("suffix") or "?"
                    raise ValueError(
                        f"culture.yaml agent '{suffix}' has unknown backend "
                        f"'{backend_value}'\n"
                        f"hint: expected one of {_VALID_DISPLAY}"
                    ) from None
    raise ValueError(
        f"--agent required (one of: {_VALID_DISPLAY}) or set 'backend:' on the "
        f"first agent in culture.yaml"
    )
