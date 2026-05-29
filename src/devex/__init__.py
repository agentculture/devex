from importlib.metadata import PackageNotFoundError, version


def _resolve_version() -> str:
    # `devex-cli` is the canonical PyPI distribution name; `agent-devex` and
    # `agex-cli` are alias distributions that ship the identical wheel under
    # different names (`agex-cli` is the legacy canonical name, kept published
    # for back-compat). Whichever one is installed, surface its metadata
    # version. As a final fallback for unbuilt source checkouts (no installed
    # dist metadata), read the version directly from the repo's pyproject.toml
    # so the version stays single-sourced from pyproject.toml in every
    # reachable code path.
    for dist in ("devex-cli", "agent-devex", "agex-cli"):
        try:
            return version(dist)
        except PackageNotFoundError:
            continue
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


__version__ = _resolve_version()
