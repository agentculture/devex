import os
from pathlib import Path

import pytest

import devex.cli as cli
from devex import __version__
from devex.commands.doctor.scripts.next_step import doctor_next_step
from devex.core.paths import GITIGNORE_CONTENT


@pytest.fixture
def in_tmp_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Run each test in an isolated cwd so `.devex/` lookups don't leak."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _init_devex(root: Path, *, agex_version: str = __version__) -> None:
    agex = root / ".devex"
    agex.mkdir()
    (agex / "data").mkdir()
    (agex / ".gitignore").write_text(GITIGNORE_CONTENT, encoding="utf-8")
    (agex / "config.toml").write_text(f'agex_version = "{agex_version}"\n', encoding="utf-8")


def test_doctor_runs_with_no_args_and_exits_zero(in_tmp_cwd: Path, capsys) -> None:
    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0, captured.out
    assert "# devex doctor" in captured.out
    assert "## Install" in captured.out
    assert "## Project state" in captured.out
    assert "## Internal consistency" in captured.out
    assert "## Operator verification" in captured.out
    assert "## Summary" in captured.out


def test_doctor_reports_uninitialized_agex_dir_as_info(in_tmp_cwd: Path, capsys) -> None:
    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0
    assert "not initialized" in captured.out
    # No hard failure markers in any check row.
    assert "✗" not in captured.out or "✗ fail | 0" in captured.out


def test_doctor_does_not_create_agex_dir(in_tmp_cwd: Path) -> None:
    cli.main(["doctor"])
    assert not (in_tmp_cwd / ".devex").exists(), "doctor must remain read-only"


def test_doctor_with_initialized_agex_dir_reports_ok(in_tmp_cwd: Path, capsys) -> None:
    _init_devex(in_tmp_cwd)
    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0
    assert "✓ **`.devex/` directory**" in captured.out
    assert "✓ **`.devex/config.toml`**" in captured.out
    assert "✓ **`.devex/.gitignore`**" in captured.out
    assert "✓ **`.devex/data/`**" in captured.out


def test_doctor_detects_invalid_config_toml(in_tmp_cwd: Path, capsys) -> None:
    agex = in_tmp_cwd / ".devex"
    agex.mkdir()
    (agex / "data").mkdir()
    (agex / ".gitignore").write_text(GITIGNORE_CONTENT, encoding="utf-8")
    (agex / "config.toml").write_text("invalid = = toml", encoding="utf-8")

    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 1
    assert "✗ **`.devex/config.toml`**" in captured.out
    assert "devex: error:" in captured.err
    assert "health check" in captured.err


def test_doctor_detects_version_mismatch_as_warning(in_tmp_cwd: Path, capsys) -> None:
    _init_devex(in_tmp_cwd, agex_version="0.0.0-old")
    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0
    assert "⚠️ **`.devex/config.toml`**" in captured.out
    assert "0.0.0-old" in captured.out


def test_doctor_detects_drifted_gitignore(in_tmp_cwd: Path, capsys) -> None:
    _init_devex(in_tmp_cwd)
    (in_tmp_cwd / ".devex" / ".gitignore").write_text("# hand-edited\n", encoding="utf-8")
    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0
    assert "⚠️ **`.devex/.gitignore`**" in captured.out
    assert "drifted" in captured.out


def test_doctor_detects_missing_gitignore(in_tmp_cwd: Path, capsys) -> None:
    _init_devex(in_tmp_cwd)
    (in_tmp_cwd / ".devex" / ".gitignore").unlink()
    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0
    assert "⚠️ **`.devex/.gitignore`**" in captured.out
    assert "missing" in captured.out


def test_doctor_detects_unwritable_data_dir(in_tmp_cwd: Path, capsys) -> None:
    _init_devex(in_tmp_cwd)
    data = in_tmp_cwd / ".devex" / "data"
    original_mode = data.stat().st_mode
    os.chmod(data, 0o500)  # readable + executable, not writable
    try:
        code = cli.main(["doctor"])
        captured = capsys.readouterr()
        # Skip on platforms that ignore chmod (e.g. some Windows + WSL combos).
        if os.access(data, os.W_OK):
            pytest.skip("filesystem ignores chmod; cannot exercise unwritable case")
        assert code == 1
        assert "✗ **`.devex/data/`**" in captured.out
    finally:
        os.chmod(data, original_mode)


def test_doctor_internal_consistency_passes(in_tmp_cwd: Path, capsys) -> None:
    """Sanity: every shipped SKILL.md and capability YAML must parse."""
    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0
    assert "✓ **Shipped SKILL.md frontmatter**" in captured.out
    assert "✓ **Backend capability YAML**" in captured.out


def test_doctor_summary_table_appears(in_tmp_cwd: Path, capsys) -> None:
    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0
    assert "| ✓ ok |" in captured.out
    assert "| ⚠️ warn |" in captured.out
    assert "| ✗ fail |" in captured.out
    assert "| · info |" in captured.out


def test_doctor_unknown_role_exits_2(in_tmp_cwd: Path, capsys) -> None:
    code = cli.main(["doctor", "--role", "no-such-role"])
    captured = capsys.readouterr()
    assert code == 2
    assert "unknown role" in captured.err


def test_doctor_rejects_role_path_traversal(in_tmp_cwd: Path, capsys) -> None:
    for bad in ("../../../etc/passwd", "/etc/passwd", "..", "a/b", "PrRev"):
        code = cli.main(["doctor", "--role", bad])
        capsys.readouterr()
        assert code == 2, f"expected exit 2 for role={bad!r}"


def test_doctor_role_renders_extra_section(
    in_tmp_cwd: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Ship a temporary role file via monkeypatch and confirm it renders."""
    from devex.commands.doctor.scripts import doctor as doctor_module

    fake_section = "Custom role check: confirm credentials are present."

    class _FakeTraversable:
        def is_file(self) -> bool:
            return True

        def read_text(self, encoding: str = "utf-8") -> str:
            return fake_section

    def _fake_resolve(role: str):
        return _FakeTraversable() if role == "pr-review" else None

    monkeypatch.setattr(doctor_module, "_resolve_role", _fake_resolve)

    code = cli.main(["doctor", "--role", "pr-review"])
    captured = capsys.readouterr()
    assert code == 0, captured.out
    assert "## Role: `pr-review`" in captured.out
    assert fake_section in captured.out


# ---------------------------------------------------------------------------
# Optional --agent + 'Next step:' footer (t3)
# ---------------------------------------------------------------------------


def _write_broken_config(root: Path) -> None:
    """Create a `.devex/` whose config.toml is malformed → a hard `fail` row."""
    agex = root / ".devex"
    agex.mkdir()
    (agex / "data").mkdir()
    (agex / ".gitignore").write_text(GITIGNORE_CONTENT, encoding="utf-8")
    (agex / "config.toml").write_text("invalid = = toml", encoding="utf-8")


def _footer_line(out: str) -> str:
    """Return the trailing 'Next step:' footer block of a doctor report."""
    marker = "---\n**Next step:**"
    assert marker in out, "no Next step footer found"
    return out[out.rindex(marker) :]


def test_doctor_clean_emits_neutral_footer_without_agent(in_tmp_cwd: Path, capsys) -> None:
    """Flagless doctor still exits 0 and now ends with a clean neutral footer."""
    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 0
    footer = _footer_line(captured.out)
    assert "Setup is healthy" in footer
    # Neutral phrasing — no concrete backend baked into the footer.
    assert "--agent <backend>" in footer
    assert "--agent claude-code" not in footer


def test_doctor_clean_emits_backend_footer_with_agent(in_tmp_cwd: Path, capsys) -> None:
    """With --agent the clean footer uses that backend's doctor hints."""
    code = cli.main(["doctor", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    footer = _footer_line(captured.out)
    assert "Setup is healthy" in footer
    assert "--agent claude-code" in footer
    assert "--agent <backend>" not in footer


def test_doctor_failures_emit_neutral_footer_and_keep_exit_1(in_tmp_cwd: Path, capsys) -> None:
    """A hard failure → fix-and-rerun neutral footer, still exit 1."""
    _write_broken_config(in_tmp_cwd)
    code = cli.main(["doctor"])
    captured = capsys.readouterr()
    assert code == 1
    assert "failing check(s) above" in captured.out
    assert "rerun `devex doctor`" in captured.out
    # Exit code is unchanged by the footer.
    assert "devex: error:" in captured.err


def test_doctor_failures_emit_backend_footer_and_keep_exit_1(in_tmp_cwd: Path, capsys) -> None:
    """A hard failure with --agent → backend fix-and-rerun footer, still exit 1."""
    _write_broken_config(in_tmp_cwd)
    code = cli.main(["doctor", "--agent", "codex"])
    captured = capsys.readouterr()
    assert code == 1
    assert "failing check(s) above" in captured.out
    assert "rerun `devex doctor --agent codex`" in captured.out


def test_doctor_footer_reports_fail_count(in_tmp_cwd: Path, capsys) -> None:
    """The failure footer names how many checks need fixing."""
    _write_broken_config(in_tmp_cwd)
    cli.main(["doctor", "--agent", "acp"])
    captured = capsys.readouterr()
    assert "Fix the 1 failing check(s)" in captured.out


def test_doctor_invalid_agent_exits_2(in_tmp_cwd: Path, capsys) -> None:
    """An explicit but bogus --agent value is rejected with exit 2."""
    code = cli.main(["doctor", "--agent", "bogus"])
    captured = capsys.readouterr()
    assert code == 2
    assert "unknown backend" in captured.err


def test_doctor_agent_does_not_create_agex_dir(in_tmp_cwd: Path) -> None:
    """doctor stays read-only even with --agent."""
    cli.main(["doctor", "--agent", "claude-code"])
    assert not (in_tmp_cwd / ".devex").exists()


def test_doctor_next_step_decision_fn() -> None:
    """The decision fn maps fail counts to the two rule keys + context."""
    assert doctor_next_step(0) == ("doctor_clean", {})
    assert doctor_next_step(1) == ("doctor_failures", {"fail_count": 1})
    assert doctor_next_step(5) == ("doctor_failures", {"fail_count": 5})
