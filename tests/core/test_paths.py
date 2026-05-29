from devex.core.paths import config_path, data_dir, ensure_init, state_dir


def test_state_dir_uses_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert state_dir() == tmp_path / ".devex"


def test_state_dir_falls_back_to_legacy_agex(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".agex").mkdir()
    # A pre-existing legacy `.agex/` (and no `.devex/`) is read transparently.
    assert state_dir() == tmp_path / ".agex"


def test_state_dir_prefers_devex_when_both_exist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".agex").mkdir()
    (tmp_path / ".devex").mkdir()
    assert state_dir() == tmp_path / ".devex"


def test_ensure_init_creates_dir_and_gitignore(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_init()
    assert (tmp_path / ".devex").is_dir()
    assert (tmp_path / ".devex" / "data").is_dir()
    gi = tmp_path / ".devex" / ".gitignore"
    assert gi.exists()
    assert "data/" in gi.read_text(encoding="utf-8")


def test_ensure_init_migrates_legacy_agex_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    legacy = tmp_path / ".agex"
    (legacy / "data").mkdir(parents=True)
    (legacy / "config.toml").write_text('agex_version = "0.0.0"\n', encoding="utf-8")
    ensure_init()
    # Legacy dir is relocated to the canonical name, contents preserved.
    assert not legacy.exists()
    assert (tmp_path / ".devex" / "config.toml").read_text(encoding="utf-8") == (
        'agex_version = "0.0.0"\n'
    )
    assert (tmp_path / ".devex" / "data").is_dir()


def test_ensure_init_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_init()
    (tmp_path / ".devex" / "existing.txt").write_text("keep me", encoding="utf-8")
    ensure_init()
    assert (tmp_path / ".devex" / "existing.txt").read_text(encoding="utf-8") == "keep me"


def test_config_path_and_data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_init()
    assert config_path() == tmp_path / ".devex" / "config.toml"
    assert data_dir() == tmp_path / ".devex" / "data"
