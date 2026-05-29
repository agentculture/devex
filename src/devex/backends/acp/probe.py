from pathlib import Path

from devex.backends.claude_code.probe import ProbeResult


def probe(project_dir: Path) -> ProbeResult:
    """Stub ACP probe — v0.1 returns empty. Full discovery tracked as open issue."""
    del project_dir  # accepted for signature parity with other probes; real discovery deferred
    return ProbeResult()
