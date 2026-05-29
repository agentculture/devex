from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from devex.backends.acp.probe import probe as acp_probe
from devex.backends.claude_code.probe import probe as claude_code_probe
from devex.backends.codex.probe import probe as codex_probe
from devex.backends.copilot.probe import probe as copilot_probe
from devex.core.backend import Backend
from devex.core.paths import ensure_init
from devex.core.render import render_string

_PROBES = {
    Backend.CLAUDE_CODE: claude_code_probe,
    Backend.CODEX: codex_probe,
    Backend.COPILOT: copilot_probe,
    Backend.ACP: acp_probe,
}


def _assets_root() -> Traversable:
    # Anchor on the `commands` package (which has __init__.py) and navigate in,
    # matching explain.py's pattern. Avoids relying on namespace-package
    # semantics for `assets/`, which is a data directory, not a package.
    return files("devex.commands").joinpath("overview", "assets")


def run(backend: Backend) -> tuple[str, int, str]:
    """Return (stdout, exit_code, stderr)."""
    ensure_init()
    project_dir = Path.cwd()

    probe_result = _PROBES[backend](project_dir)

    template_text = _assets_root().joinpath("sections.md.j2").read_text(encoding="utf-8")
    out = render_string(
        template_text,
        {"backend": backend.value, "project_dir": project_dir, "probe": probe_result},
    )
    return (out, 0, "")
