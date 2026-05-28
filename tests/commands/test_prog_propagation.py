"""Script-level 'output follows invocation' coverage.

`render`'s `prog` injection only covers Jinja-rendered templates/footers. These
tests pin the *plain-string* stdout/stderr paths in command scripts, which build
their `agex`/`devex` references in Python — they must follow the invoked entry
point too (regression guard for agex-cli#61 Qodo finding).
"""

from agent_experience.commands.explain.scripts import explain as explain_script
from agent_experience.commands.learn.scripts import learn as learn_script
from agent_experience.commands.pr.scripts import delta as delta_script
from agent_experience.core.backend import Backend


def test_explain_unknown_topic_error_follows_invocation(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/devex"])
    _, code, stderr = explain_script.run("zzz-no-such-topic")
    assert code == 2
    assert stderr.startswith("devex: error: ")
    assert "agex" not in stderr


def test_learn_unknown_topic_error_follows_invocation(monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/devex"])
    _, code, stderr = learn_script.run_topic("zzz-no-such-topic", Backend.CLAUDE_CODE)
    assert code == 2
    assert stderr.startswith("devex: error: ")
    assert "agex" not in stderr


def test_pr_delta_no_siblings_follows_invocation(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/devex"])
    stdout, code, stderr = delta_script.run(agent="claude-code", project_dir=tmp_path)
    assert code == 0
    assert "# `devex pr delta`" in stdout
    assert stderr.startswith("devex: copy ")
    assert "agex" not in stdout
    assert "agex" not in stderr


def test_pr_delta_no_siblings_defaults_to_agex(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["agex"])
    stdout, _, stderr = delta_script.run(agent="claude-code", project_dir=tmp_path)
    assert "# `agex pr delta`" in stdout
    assert stderr.startswith("agex: copy ")
