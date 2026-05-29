from devex import __version__
from devex.core.config import Config, load, save
from devex.core.paths import ensure_init


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_init()
    cfg = load()
    assert cfg.agex_version == __version__
    assert cfg.installed == {}
    assert cfg.preferences == {}


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_init()
    cfg = Config(agex_version=__version__)
    cfg.installed["gamify"] = {
        "at": "2026-04-18T10:00:00Z",
        "hook_fragment_ids": ["agex:post-tool-use"],
    }
    save(cfg)
    reloaded = load()
    assert reloaded.installed["gamify"]["hook_fragment_ids"] == ["agex:post-tool-use"]


def test_pr_section_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_init()
    cfg = load()
    assert cfg.pr == {}
    cfg.pr = {"wait_default": 240, "required_reviewers": ["qodo"]}
    save(cfg)

    loaded = load()
    assert loaded.pr == {"wait_default": 240, "required_reviewers": ["qodo"]}
