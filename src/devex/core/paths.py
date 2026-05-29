import os
from pathlib import Path

GITIGNORE_CONTENT = "# Managed by devex — do not edit.\ndata/\n"

_CANONICAL_DIR = ".devex"
_LEGACY_DIR = ".agex"


def state_dir(cwd: Path | None = None) -> Path:
    """Path to the devex state directory.

    Prefers the canonical ``.devex/``. Falls back to a pre-existing legacy
    ``.agex/`` so older checkouts keep working transparently until
    ``ensure_init`` migrates them. Brand-new projects get ``.devex/``.
    """
    base = cwd if cwd is not None else Path.cwd()
    devex = base / _CANONICAL_DIR
    if devex.exists():
        return devex
    legacy = base / _LEGACY_DIR
    if legacy.exists():
        return legacy
    return devex


def config_path(cwd: Path | None = None) -> Path:
    return state_dir(cwd) / "config.toml"


def data_dir(cwd: Path | None = None) -> Path:
    return state_dir(cwd) / "data"


def ensure_init(cwd: Path | None = None) -> Path:
    base = cwd if cwd is not None else Path.cwd()
    devex = base / _CANONICAL_DIR
    legacy = base / _LEGACY_DIR
    # One-time migration: relocate a legacy `.agex/` to `.devex/` via an atomic
    # same-parent rename. If both somehow exist, the canonical `.devex/` wins and
    # the legacy dir is left untouched for the user to remove.
    if legacy.exists() and not devex.exists():
        os.rename(legacy, devex)
    root = devex
    root.mkdir(parents=True, exist_ok=True)
    (root / "data").mkdir(exist_ok=True)
    gi = root / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE_CONTENT, encoding="utf-8")
    return root
