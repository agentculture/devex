from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from agent_experience.core.backend import Backend

ISSUE_URL = "https://github.com/agentculture/devex/issues"


@dataclass
class CapabilityMatrix:
    data: dict[Backend, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, sources: dict[Backend, Path]) -> "CapabilityMatrix":
        matrix: dict[Backend, dict[str, Any]] = {}
        for backend, path in sources.items():
            matrix[backend] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(matrix)


def is_supported(matrix: CapabilityMatrix, backend: Backend, capability: str) -> bool:
    return bool(matrix.data.get(backend, {}).get(capability, False))


def unsupported_notice(matrix: CapabilityMatrix, backend: Backend, capability: str) -> str:
    data = matrix.data.get(backend, {})
    alt = data.get(f"{capability}_alternative", "").strip()
    lines = [
        f"## `{capability}` is not supported on {backend.value}",
        "",
    ]
    if alt:
        lines.append("**Closest alternative:**")
        lines.append("")
        lines.append(alt)
        lines.append("")
    lines.append(
        f"Want `{capability}` supported on {backend.value}, or have a better alternative? "
        f"Open an issue: <{ISSUE_URL}>"
    )
    return "\n".join(lines) + "\n"
