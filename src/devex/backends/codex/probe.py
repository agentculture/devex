from pathlib import Path

from devex.backends.claude_code.probe import ProbeResult


def probe(project_dir: Path) -> ProbeResult:
    """Minimal Codex probe — reads AGENTS.md if present. Other discovery deferred."""
    result = ProbeResult()
    if not project_dir.exists():
        return result
    agents_md = project_dir / "AGENTS.md"
    if agents_md.exists():
        result.claude_md = (
            agents_md  # reusing field — rename to `project_memory` in a future cleanup
        )
    return result
