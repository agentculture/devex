from pathlib import Path

import yaml

import agent_experience.cli as cli


def _setup_skills_local(tmp_path: Path, siblings: list[Path]) -> None:
    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / ".claude" / "skills.local.yaml").write_text(
        yaml.safe_dump({"sibling_projects": [str(s) for s in siblings]}), encoding="utf-8"
    )


def _make_sibling(root: Path, name: str, claude_md: str | None, culture: dict | None) -> Path:
    p = root / name
    p.mkdir()
    if claude_md is not None:
        (p / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    if culture is not None:
        (p / "culture.yaml").write_text(yaml.safe_dump(culture), encoding="utf-8")
    return p


def test_delta_dumps_each_sibling(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    s1 = _make_sibling(tmp_path, "sibling-a", "Line 1\nLine 2\n", {"agents": [{"name": "a"}]})
    s2 = _make_sibling(tmp_path, "sibling-b", "Other content\n", None)
    _setup_skills_local(tmp_path, [s1, s2])
    code = cli.main(["pr", "delta", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "sibling-a" in captured.out
    assert "Line 1" in captured.out
    assert "sibling-b" in captured.out
    assert "Other content" in captured.out
    assert "alignment drifted" in captured.out


def test_delta_missing_skills_local(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    code = cli.main(["pr", "delta", "--agent", "claude-code"])
    captured = capsys.readouterr()
    assert code == 0
    assert "skills.local.yaml" in captured.out
    assert "skills.local.yaml.example" in captured.err


def test_pr_delta_handles_gh_runtime_error_propagation(monkeypatch, tmp_path, capsys):
    # delta doesn't call gh today, but the cli handler should still be
    # defensive in case future implementations do.
    monkeypatch.chdir(tmp_path)
    # No skills.local.yaml — exits 0 via the existing path. Verify the
    # cli wrapper wires through correctly.
    code = cli.main(["pr", "delta", "--agent", "claude-code"])
    capsys.readouterr()
    assert code == 0
