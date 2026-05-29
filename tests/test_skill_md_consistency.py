"""Meta-tests that guard SKILL.md consistency across all commands and lessons.

These tests parametrize over every SKILL.md discovered under the commands
package and assert that frontmatter is valid.  They also verify that the
five top-level command SKILL.md files exist so that future renames or
deletions don't silently break the contract.

Zipapp/PEX safety: `as_file()` may extract resources to a temporary
directory that gets cleaned up when the context exits.  So we never
parametrize over `Path` objects captured inside an `as_file()` context
— we parametrize over relative-path strings (always safe) and
re-enter `as_file()` inside each test to materialize a real Path just
long enough to read the file.  This works identically on editable
filesystem installs (where `as_file` is a no-op) and on zipped wheel
installs (where it extracts on demand).
"""

from importlib.resources import as_file, files

import pytest

from devex.core.skill_loader import load_skill

_VALID_TYPES = frozenset({"command", "lesson"})


def _all_skill_md_relpaths() -> list[str]:
    """Return relative paths (strings) of every SKILL.md under the commands
    package. Strings survive across `as_file()` boundaries; Path objects
    captured inside the context do not."""
    with as_file(files("devex.commands")) as root:
        return sorted("/".join(p.relative_to(root).parts) for p in root.glob("**/SKILL.md"))


# ---------------------------------------------------------------------------
# Guard: ensure the parametrize fixture actually discovers enough files.
# If the import mechanics break, all parametrized tests silently pass (0
# items), so we add an explicit lower-bound check here.
# ---------------------------------------------------------------------------


def test_meta_test_discovers_all_known_skills() -> None:
    """Verify that at least 10 SKILL.md files are found (6 commands + 4 lessons)."""
    relpaths = _all_skill_md_relpaths()
    assert (
        len(relpaths) >= 10
    ), f"Expected >= 10 SKILL.md files under devex.commands, found {len(relpaths)}: {relpaths}"


# ---------------------------------------------------------------------------
# Parametrized frontmatter tests — one test case per SKILL.md file.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relpath", _all_skill_md_relpaths(), ids=str)
def test_skill_md_has_valid_frontmatter(relpath: str) -> None:
    """Each SKILL.md must parse without error and have name, description, and type."""
    with as_file(files("devex.commands")) as commands_root:
        skill_path = commands_root / relpath
        skill = load_skill(skill_path)
    assert skill.name, f"{relpath}: 'name' frontmatter field is empty"
    assert skill.description, f"{relpath}: 'description' frontmatter field is empty"
    assert (
        skill.type in _VALID_TYPES
    ), f"{relpath}: 'type' value {skill.type!r} is not one of {sorted(_VALID_TYPES)}"


# ---------------------------------------------------------------------------
# Structural test — every top-level command must have a SKILL.md.
# ---------------------------------------------------------------------------


def test_every_command_has_skill_md() -> None:
    """Each of the six top-level commands must ship a SKILL.md."""
    with as_file(files("devex.commands")) as commands_root:
        for cmd in ("explain", "overview", "learn", "gamify", "hook", "doctor"):
            assert (
                commands_root / cmd / "SKILL.md"
            ).is_file(), f"{cmd}/SKILL.md is missing from devex.commands"
