import importlib

import pytest


@pytest.fixture
def reload_agent_experience():
    """Reload `agent_experience` cleanly after a test that monkeypatched its
    version-resolution path, so other tests in the same worker see the real
    installed version rather than the patched one."""
    yield
    importlib.reload(importlib.import_module("agent_experience"))


@pytest.mark.parametrize(
    "installed_dist",
    ["agex-cli", "agent-devex", "devex-cli"],
)
def test_version_resolves_for_any_dist_name(
    monkeypatch, reload_agent_experience, installed_dist
):
    """`agent_experience.__version__` must resolve whichever of the three
    distribution names the wheel was installed as: `agex-cli` (canonical),
    `agent-devex`, or `devex-cli` (aliases)."""
    from importlib.metadata import PackageNotFoundError

    real_version = importlib.import_module("importlib.metadata").version

    def fake_version(dist):
        if dist == installed_dist:
            return "9.9.9"
        if dist in {"agex-cli", "agent-devex", "devex-cli"}:
            raise PackageNotFoundError(dist)
        return real_version(dist)

    monkeypatch.setattr("importlib.metadata.version", fake_version)
    module = importlib.reload(importlib.import_module("agent_experience"))
    assert module.__version__ == "9.9.9"


def test_version_falls_back_to_pyproject_when_no_dist_found(
    monkeypatch, reload_agent_experience
):
    """If neither distribution is installed (rare: running from an unbuilt
    source checkout), `__version__` is read directly from pyproject.toml so
    the version is still single-sourced from pyproject.toml."""
    import tomllib
    from importlib.metadata import PackageNotFoundError
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    expected = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]

    def always_missing(dist):
        raise PackageNotFoundError(dist)

    monkeypatch.setattr("importlib.metadata.version", always_missing)
    module = importlib.reload(importlib.import_module("agent_experience"))
    assert module.__version__ == expected


def test_real_install_resolves_to_pyproject_version():
    """Smoke test: in the actual test environment, `__version__` resolves
    to the version declared in pyproject.toml (sanity check that the
    fallback chain didn't accidentally hide a real install)."""
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    expected = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]

    from agent_experience import __version__

    assert __version__ == expected
