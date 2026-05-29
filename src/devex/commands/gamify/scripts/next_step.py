"""'Next step:' rule keys for `devex gamify` install and uninstall.

Each function takes the data the command already gathered and returns the
footer rule key + a context dict for variable substitution.  Per-backend
phrasing lives in `assets/backends/*.yaml`.
"""

from __future__ import annotations

from typing import Any

from devex.core.backend import Backend


def gamify_install_next_step(backend: Backend) -> tuple[str, dict[str, Any]]:
    """Rule key for successful install (new fragments added OR already present)."""
    return "gamify_installed", {"backend": backend.value}


def gamify_uninstall_next_step(backend: Backend) -> tuple[str, dict[str, Any]]:
    """Rule key for successful uninstall (fragments removed or file already gone)."""
    return "gamify_uninstalled", {"backend": backend.value}


def gamify_nothing_to_remove_next_step(backend: Backend) -> tuple[str, dict[str, Any]]:
    """Rule key when uninstall finds no recorded fragments to remove."""
    return "gamify_nothing_to_remove", {"backend": backend.value}


def gamify_unsupported_next_step(backend: Backend) -> tuple[str, dict[str, Any]]:
    """Rule key for the unsupported-backend notice (backend has no hook interface)."""
    return "gamify_unsupported", {"backend": backend.value}
