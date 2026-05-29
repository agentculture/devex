from dataclasses import dataclass, field
from typing import Any

import tomlkit

from devex import __version__
from devex.core.paths import config_path


@dataclass
class Config:
    agex_version: str = field(default_factory=lambda: __version__)
    backend: str | None = None
    installed: dict[str, dict[str, Any]] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    pr: dict[str, Any] = field(default_factory=dict)


def load() -> Config:
    path = config_path()
    if not path.exists():
        return Config()
    doc = tomlkit.parse(path.read_text(encoding="utf-8"))
    return Config(
        agex_version=doc.get("agex_version", __version__),
        backend=doc.get("backend"),
        installed=dict(doc.get("installed", {})),
        preferences=dict(doc.get("preferences", {})),
        pr=dict(doc.get("pr", {})),
    )


def save(cfg: Config) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = tomlkit.document()
    doc["agex_version"] = cfg.agex_version
    if cfg.backend is not None:
        doc["backend"] = cfg.backend
    if cfg.installed:
        doc["installed"] = cfg.installed
    if cfg.preferences:
        doc["preferences"] = cfg.preferences
    if cfg.pr:
        doc["pr"] = cfg.pr
    path.write_text(tomlkit.dumps(doc), encoding="utf-8")
