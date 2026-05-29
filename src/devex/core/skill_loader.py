import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.DOTALL)

REQUIRED_FIELDS = ("name", "description", "type")


@dataclass
class Skill:
    name: str
    description: str
    type: str
    body: str
    path: Path


def load_skill(path: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter")
    meta = yaml.safe_load(match.group(1)) or {}
    for field_name in REQUIRED_FIELDS:
        if field_name not in meta:
            raise ValueError(f"{path}: frontmatter missing required field '{field_name}'")
    return Skill(
        name=meta["name"],
        description=meta["description"],
        type=meta["type"],
        body=match.group(2).lstrip("\n"),
        path=path,
    )
