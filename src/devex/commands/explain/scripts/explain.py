import re
from importlib.resources import files
from importlib.resources.abc import Traversable

from devex.commands.explain.scripts._footer import render_footer
from devex.commands.explain.scripts.next_step import explain_next_step
from devex.core.backend import Backend
from devex.core.footer import render_neutral_footer
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


def _footer_for(kind: str, topic: str, backend: Backend | None) -> str:
    """Render the trailing 'Next step:' footer for a resolved topic.

    With *backend* the per-backend explain hints are used; without it the
    shared neutral footer is emitted.  Returns the footer prefixed with a
    blank line so it never glues onto the body's last line.
    """
    rule_key, ctx = explain_next_step(kind, topic)
    if backend is not None:
        footer = render_footer(rule_key, backend, ctx)
    else:
        footer = render_neutral_footer(rule_key, ctx)
    return f"\n\n{footer}\n"


def run(topic: str, backend: Backend | None = None) -> tuple[str, int, str]:
    """Return (stdout, exit_code, stderr).

    *backend* is optional: when supplied the trailing 'Next step:' footer is
    rendered from that backend's explain hints, otherwise a neutral footer is
    emitted.  The footer is appended only on a successful resolution (exit 0);
    the path-traversal rejection and unknown-topic paths (exit 2) are
    unchanged.
    """
    resolved = resolve_topic(topic)
    if resolved is None:
        overview_page = _commands_root().joinpath("explain", "assets", "topics", "devex.md")
        body = overview_page.read_text(encoding="utf-8") if overview_page.is_file() else ""
        return (body, 2, error_prefix(f"unknown topic '{topic}'"))

    kind, trav = resolved
    if kind == "concept":
        body = trav.read_text(encoding="utf-8")
    else:
        skill = _load_skill_from_traversable(trav)
        body = skill.body
    return (body + _footer_for(kind, topic, backend), 0, "")
