import re
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable

from devex.core.backend import Backend
from devex.core.prog import error_prefix
from devex.core.render import render_string
from devex.core.skill_loader import Skill, load_skill

_TOPIC_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_SKILL_FILENAME = "SKILL.md"


def _learn_assets() -> Traversable:
    # Anchor on the `commands` package (which has __init__.py) and navigate in.
    # Avoids relying on namespace-package semantics for `assets/`, which is a
    # data directory, not a package. Matches explain.py / overview.py pattern.
    return files("devex.commands").joinpath("learn", "assets")


def _load_skill_from_traversable(trav: Traversable) -> Skill:
    # load_skill expects a pathlib.Path; resolve via as_file when needed.
    with as_file(trav) as path:
        return load_skill(path)


def _list_topics() -> list[dict]:
    topics: list[dict] = []
    topics_root = _learn_assets().joinpath("topics")
    for topic_dir in sorted(topics_root.iterdir(), key=lambda p: p.name):
        if topic_dir.is_file():
            continue
        skill_md = topic_dir.joinpath(_SKILL_FILENAME)
        if not skill_md.is_file():
            continue
        skill = _load_skill_from_traversable(skill_md)
        # Use the directory name as the canonical slug — `run_topic` looks up
        # by directory, so the menu's `devex learn <name>` invocation must
        # match. Frontmatter `skill.name` is still available for drift checks.
        topics.append(
            {"name": topic_dir.name, "description": skill.description, "unsupported": None}
        )
    return topics


def run_menu(backend: Backend) -> tuple[str, int, str]:
    """Return (stdout, exit_code, stderr) for the topic menu."""
    topics = _list_topics()
    template_text = _learn_assets().joinpath("menu.md.j2").read_text(encoding="utf-8")
    out = render_string(template_text, {"backend": backend.value, "topics": topics})
    return (out, 0, "")


def run_topic(topic: str, backend: Backend) -> tuple[str, int, str]:
    """Return (stdout, exit_code, stderr) for a specific lesson topic."""
    if not _TOPIC_RE.match(topic):
        menu_out, _, _ = run_menu(backend)
        return (menu_out, 2, error_prefix(f"unknown topic '{topic}'"))

    topic_dir = _learn_assets().joinpath("topics", topic)
    skill_md = topic_dir.joinpath(_SKILL_FILENAME)
    if not skill_md.is_file():
        menu_out, _, _ = run_menu(backend)
        return (menu_out, 2, error_prefix(f"unknown topic '{topic}'"))

    skill = _load_skill_from_traversable(skill_md)
    template_path = topic_dir.joinpath("assets", "skill-template", backend.value, _SKILL_FILENAME)
    template_body = template_path.read_text(encoding="utf-8") if template_path.is_file() else ""
    rendered = render_string(
        skill.body,
        {"backend": backend.value, "skill_template_body": template_body},
    )
    return (rendered, 0, "")
