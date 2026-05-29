import re
from importlib.resources import files
from importlib.resources.abc import Traversable

from devex.core.prog import error_prefix
from devex.core.skill_loader import Skill, load_skill

_TOPIC_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def _commands_root() -> Traversable:
    return files("devex.commands")


def resolve_topic(topic: str) -> tuple[str, Traversable] | None:
    """Resolve topic per spec precedence. Returns (kind, traversable) or None.

    Rejects any topic that isn't a simple slug to prevent path traversal.
    """
    if not _TOPIC_RE.match(topic):
        return None

    # `agex` is the legacy alias for the canonical `devex` overview page; resolve
    # it to the single devex.md so `devex explain agex` / `agex explain agex`
    # still work without duplicating the page.
    if topic == "agex":
        topic = "devex"

    cmds = _commands_root()

    cmd_skill = cmds.joinpath(topic, "SKILL.md")
    if cmd_skill.is_file():
        return ("command", cmd_skill)

    lesson_skill = cmds.joinpath("learn", "assets", "topics", topic, "SKILL.md")
    if lesson_skill.is_file():
        return ("lesson", lesson_skill)

    concept = cmds.joinpath("explain", "assets", "topics", f"{topic}.md")
    if concept.is_file():
        return ("concept", concept)

    return None


def _load_skill_from_traversable(trav: Traversable) -> Skill:
    # load_skill expects a pathlib.Path; resolve via as_file when needed. Since
    # our package resources are on a real filesystem (hatch force-include), the
    # Traversable is a MultiplexedPath / PosixPath wrapper whose .read_text()
    # works directly. We rebuild a Skill by parsing the body in-line to avoid
    # Path coupling.
    from importlib.resources import as_file

    with as_file(trav) as path:
        return load_skill(path)


def run(topic: str) -> tuple[str, int, str]:
    """Return (stdout, exit_code, stderr)."""
    resolved = resolve_topic(topic)
    if resolved is None:
        overview_page = _commands_root().joinpath("explain", "assets", "topics", "devex.md")
        body = overview_page.read_text(encoding="utf-8") if overview_page.is_file() else ""
        return (body, 2, error_prefix(f"unknown topic '{topic}'"))

    kind, trav = resolved
    if kind == "concept":
        return (trav.read_text(encoding="utf-8"), 0, "")
    skill = _load_skill_from_traversable(trav)
    return (skill.body, 0, "")
