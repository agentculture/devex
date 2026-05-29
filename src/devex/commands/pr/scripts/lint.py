"""`devex pr lint` — portability + alignment-trigger lint on the working diff."""

from __future__ import annotations

import subprocess
from importlib.resources import files
from pathlib import Path

from devex.commands.pr.assets.rules.lint_rules import (
    Violation,
    check_alignment_trigger,
    check_files,
)
from devex.commands.pr.assets.rules.next_step_rules import lint_next_step
from devex.commands.pr.scripts._footer import render_footer
from devex.core.backend import resolve_backend
from devex.core.render import render_string

_TEMPLATES_PKG = "devex.commands.pr.assets.templates"


def _collect_diff() -> list[tuple[str, str]]:
    """Return [(path, post-change content)] for staged + unstaged files.

    For deleted files, returns an empty content string — rules treat that as
    nothing to lint.
    """
    paths_staged = subprocess.run(
        ["git", "diff", "--staged", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    paths_unstaged = subprocess.run(
        ["git", "diff", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    paths = sorted(set(paths_staged) | set(paths_unstaged))
    out: list[tuple[str, str]] = []
    for p in paths:
        try:
            content = Path(p).read_text(encoding="utf-8", errors="replace")
        except (FileNotFoundError, IsADirectoryError):
            content = ""
        out.append((p, content))
    return out


def run(agent: str | None, project_dir: Path, exit_on_violation: bool) -> tuple[str, int, str]:
    backend = resolve_backend(agent, project_dir)

    file_pairs = _collect_diff()
    violations: list[Violation] = check_files(file_pairs)
    alignment_triggered = check_alignment_trigger([p for p, _ in file_pairs])

    footer_key, footer_ctx = lint_next_step(violations, alignment_triggered)
    footer = render_footer(footer_key, backend, footer_ctx)

    template = files(_TEMPLATES_PKG).joinpath("lint_result.md.j2").read_text(encoding="utf-8")
    stdout = render_string(
        template,
        {
            "violations": [v.__dict__ for v in violations],
            "alignment_triggered": alignment_triggered,
            "footer": footer,
        },
    )

    exit_code = 1 if (exit_on_violation and violations) else 0
    return stdout, exit_code, ""
