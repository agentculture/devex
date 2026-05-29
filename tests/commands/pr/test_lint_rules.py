from devex.commands.pr.assets.rules.lint_rules import (
    Violation,
    check_alignment_trigger,
    check_files,
)


def _f(path: str, content: str) -> tuple[str, str]:
    return (path, content)


def test_no_violations_on_clean_diff():
    files = [_f("src/foo.py", "print('hi')\n")]
    assert check_files(files) == []


def test_absolute_home_path_is_violation():
    files = [_f("docs/usage.md", "Run /home/spark/bin/foo to test.\n")]
    out: list[Violation] = check_files(files)
    assert len(out) == 1
    assert out[0].rule == "absolute-home-path"
    assert "/home/spark" in out[0].evidence


def test_dotfile_reference_in_doc_is_violation():
    files = [_f("README.md", "Edit ~/.claude/settings.json to enable.\n")]
    out = check_files(files)
    assert len(out) == 1
    assert out[0].rule == "user-dotfile-reference"


def test_dotfile_reference_in_code_is_not_a_violation():
    files = [_f("src/devex/core/paths.py", 'Path("~/.claude").expanduser()\n')]
    assert check_files(files) == []


def test_alignment_trigger_on_claude_md():
    assert check_alignment_trigger(["CLAUDE.md", "src/foo.py"]) is True


def test_alignment_trigger_on_culture_yaml():
    assert check_alignment_trigger(["culture.yaml"]) is True


def test_alignment_trigger_on_skills_dir():
    assert check_alignment_trigger([".claude/skills/foo/SKILL.md"]) is True


def test_no_alignment_trigger_on_unrelated_files():
    assert check_alignment_trigger(["src/foo.py", "tests/test_foo.py"]) is False
