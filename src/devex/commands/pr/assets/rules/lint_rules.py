"""Portability and alignment rules for `devex pr lint`.

Pure functions over (file_path, file_content) tuples so they can be
unit-tested without git.  The CLI driver in `commands/pr/scripts/lint.py`
collects the diff and feeds it in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HOME_PATH_RE = re.compile(r"/home/[a-zA-Z0-9_-]+/")
_DOTFILE_RE = re.compile(r"~/\.[a-zA-Z][a-zA-Z0-9_-]*/")
_DOC_EXTS = (".md", ".rst", ".txt")
_ALIGNMENT_PATHS = ("CLAUDE.md", "culture.yaml")
_ALIGNMENT_PREFIXES = (".claude/skills/",)


@dataclass
class Violation:
    rule: str
    file: str
    line: int
    evidence: str


def _check_absolute_home(path: str, content: str) -> list[Violation]:
    out: list[Violation] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        m = _HOME_PATH_RE.search(line)
        if m:
            out.append(
                Violation(
                    rule="absolute-home-path",
                    file=path,
                    line=lineno,
                    evidence=line.strip(),
                )
            )
    return out


def _check_dotfile_in_doc(path: str, content: str) -> list[Violation]:
    if not path.lower().endswith(_DOC_EXTS):
        return []
    out: list[Violation] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        if _DOTFILE_RE.search(line):
            out.append(
                Violation(
                    rule="user-dotfile-reference",
                    file=path,
                    line=lineno,
                    evidence=line.strip(),
                )
            )
    return out


def check_files(files: list[tuple[str, str]]) -> list[Violation]:
    """Run all portability rules over (path, content) tuples."""
    out: list[Violation] = []
    for path, content in files:
        out.extend(_check_absolute_home(path, content))
        out.extend(_check_dotfile_in_doc(path, content))
    return out


def check_alignment_trigger(file_paths: list[str]) -> bool:
    """Return True if the changed file list touches any alignment-relevant
    file (CLAUDE.md, culture.yaml, .claude/skills/**)."""
    for p in file_paths:
        if p in _ALIGNMENT_PATHS:
            return True
        for prefix in _ALIGNMENT_PREFIXES:
            if p.startswith(prefix):
                return True
    return False
