from importlib.metadata import PackageNotFoundError, version


def _resolve_version() -> str:
    # `agex-cli` is the canonical PyPI distribution name; `agent-devex` and
    # `devex-cli` are alias distributions that ship the identical wheel under
    # different names. Whichever one is installed, surface its metadata
    # version. As a final fallback for unbuilt source checkouts (no installed
    # dist metadata), read the version directly from the repo's pyproject.toml
    # so the version stays single-sourced from pyproject.toml in every
    # reachable code path.
    for dist in ("agex-cli", "agent-devex", "devex-cli"):
        try:
            return version(dist)
        except PackageNotFoundError:
            continue
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


__version__ = _resolve_version()
