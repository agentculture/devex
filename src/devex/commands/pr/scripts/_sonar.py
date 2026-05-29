"""SonarCloud project-key resolution for the `pr` namespace.

Resolution order:
  1. SONAR_PROJECT_KEY env var (override for non-standard naming).
  2. [pr].sonar_project_key from .devex/config.toml.
  3. <owner>_<repo> (SonarCloud GitHub-import default).
"""

from __future__ import annotations

import os

from devex.core import config as cfg_mod
from devex.core import github


def project_key() -> str:
    env = os.environ.get("SONAR_PROJECT_KEY")
    if env:
        return env
    try:
        cfg = cfg_mod.load()
        cfg_key = cfg.pr.get("sonar_project_key")
        if cfg_key:
            return str(cfg_key)
    except Exception:
        pass
    slug = github._repo_slug()  # noqa: SLF001
    return slug.replace("/", "_")
