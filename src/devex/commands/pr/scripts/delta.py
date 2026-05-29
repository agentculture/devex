"""`devex pr delta` — sibling project alignment dump."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import yaml

from devex.commands.pr.assets.rules.next_step_rules import delta_next_step
from devex.commands.pr.scripts._footer import render_footer
from devex.core import config as cfg_mod
from devex.core.backend import resolve_backend
from devex.core.prog import prog_name
from devex.core.render import render_string

_TEMPLATES_PKG = "devex.commands.pr.assets.templates"
_DEFAULT_CLAUDE_MD_LINES = 50


def _load_siblings(project_dir: Path) -> list[Path] | None:
    skills_local = project_dir / ".claude" / "skills.local.yaml"
    if not skills_local.exists():
        return None
    data = yaml.safe_load(skills_local.read_text(encoding="utf-8")) or {}
    raw = data.get("sibling_projects") or []
    return [Path(p) for p in raw]


def _claude_md_lines() -> int:
    try:
        cfg = cfg_mod.load()
    except Exception:
        return _DEFAULT_CLAUDE_MD_LINES
    return int(cfg.pr.get("delta_claude_md_lines", _DEFAULT_CLAUDE_MD_LINES))


def _gather(sibling: Path, claude_md_lines: int) -> dict:
    claude_md = sibling / "CLAUDE.md"
    culture = sibling / "culture.yaml"
    head = None
    if claude_md.exists():
        lines = claude_md.read_text(encoding="utf-8").splitlines()
        head = "\n".join(lines[:claude_md_lines])
    culture_text = culture.read_text(encoding="utf-8") if culture.exists() else None
    return {
        "name": sibling.name,
        "path": str(sibling),
        "claude_md_head": head,
        "culture_yaml": culture_text,
    }


def run(agent: str | None, project_dir: Path) -> tuple[str, int, str]:
    backend = resolve_backend(agent, project_dir)
    siblings = _load_siblings(project_dir)
    claude_md_lines = _claude_md_lines()

    if siblings is None:
        prog = prog_name()
        stdout = (
            f"# `{prog} pr delta`\n\n"
            "No `.claude/skills.local.yaml` found.  Copy "
            "`.claude/skills.local.yaml.example` and fill `sibling_projects`.\n"
        )
        stderr = (
            f"{prog}: copy .claude/skills.local.yaml.example to "
            ".claude/skills.local.yaml and fill sibling_projects\n"
        )
        return stdout, 0, stderr

    template = files(_TEMPLATES_PKG).joinpath("delta.md.j2").read_text(encoding="utf-8")
    rendered_siblings = [_gather(s, claude_md_lines) for s in siblings]
    footer_key, footer_ctx = delta_next_step()
    footer = render_footer(footer_key, backend, footer_ctx)
    stdout = render_string(
        template,
        {
            "siblings": rendered_siblings,
            "claude_md_lines": claude_md_lines,
            "footer": footer,
        },
    )
    return stdout, 0, ""
