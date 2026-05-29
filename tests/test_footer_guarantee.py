"""Cross-command footer-guarantee tests (t8).

Coverage targets:
  h4 / c1 / c3  — total footer coverage: every non-silent command emits exactly
                  one '**Next step:**' block.
  h8 / c5 / h3  — determinism: identical stdout on two runs of the same command.
  h9 / c6       — no new side-effects: hook write stays silent; read-only commands
                  don't sleep or call the network on the footer path.
  h7 / c4       — pre-change gap: body templates (non-footer .md.j2 files) contain
                  no literal 'Next step:' text, confirming the footer is the sole
                  source.

PR-namespace commands are NOT invoked (they require `gh` and live network); instead
the test asserts statically that every pr result template contains '{{ footer }}'.
"""

from __future__ import annotations

import shutil
import socket as _socket
import time as _time
from importlib.resources import files
from pathlib import Path
from typing import Callable

import pytest

import devex.cli as cli

# ---------------------------------------------------------------------------
# Helpers shared LOCALLY in this file (not added to conftest)
# ---------------------------------------------------------------------------

_FOOTER_MARKER = "**Next step:**"
_FOOTER_BLOCK_PREFIX = "---\n**Next step:**"
_BACKENDS = ("claude-code", "codex", "copilot", "acp")

# Absolute path to the fixtures tree used by the overview tests
_FIXTURES = Path(__file__).parent / "fixtures" / "claude-code"


def _copy_fixture(name: str, tmp_path: Path) -> Path:
    """Copy a named claude-code fixture into tmp_path and return its root."""
    dest = tmp_path / "project"
    shutil.copytree(_FIXTURES / name, dest)
    return dest


def _assert_exactly_one_footer(out: str, label: str = "") -> None:
    """Fail unless stdout contains exactly one '**Next step:**' occurrence."""
    count = out.count(_FOOTER_MARKER)
    assert count == 1, (
        f"Expected exactly 1 footer marker in output{' (' + label + ')' if label else ''}; "
        f"found {count}. Output tail:\n{out[-300:]}"
    )
    # The single marker must sit inside a '---\n**Next step:**...' block.
    suffix = f" ({label})" if label else ""
    assert (
        _FOOTER_BLOCK_PREFIX in out
    ), f"Footer marker present but not preceded by '---' separator{suffix}."


# ---------------------------------------------------------------------------
# 1. Total footer coverage — parametrized over every non-silent command
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv,setup",
    [
        # explain (no --agent → neutral footer)
        pytest.param(
            ["explain", "explain"],
            None,
            id="explain-command-neutral",
        ),
        pytest.param(
            ["explain", "explain", "--agent", "claude-code"],
            None,
            id="explain-command-backend",
        ),
        pytest.param(
            ["explain", "devex"],
            None,
            id="explain-concept-neutral",
        ),
        # learn menu
        pytest.param(
            ["learn", "--agent", "claude-code"],
            None,
            id="learn-menu-claude-code",
        ),
        pytest.param(
            ["learn", "--agent", "codex"],
            None,
            id="learn-menu-codex",
        ),
        pytest.param(
            ["learn", "--agent", "copilot"],
            None,
            id="learn-menu-copilot",
        ),
        pytest.param(
            ["learn", "--agent", "acp"],
            None,
            id="learn-menu-acp",
        ),
        # learn topic
        pytest.param(
            ["learn", "introspect", "--agent", "claude-code"],
            None,
            id="learn-topic-claude-code",
        ),
        pytest.param(
            ["learn", "introspect", "--agent", "codex"],
            None,
            id="learn-topic-codex",
        ),
        pytest.param(
            ["learn", "introspect", "--agent", "copilot"],
            None,
            id="learn-topic-copilot",
        ),
        pytest.param(
            ["learn", "introspect", "--agent", "acp"],
            None,
            id="learn-topic-acp",
        ),
        # doctor (no --agent → neutral footer)
        pytest.param(
            ["doctor"],
            None,
            id="doctor-neutral",
        ),
        pytest.param(
            ["doctor", "--agent", "claude-code"],
            None,
            id="doctor-backend",
        ),
    ],
)
def test_footer_present_once__no_project_dir(
    argv: list[str],
    setup: Callable | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Commands that don't require a project directory emit exactly one footer."""
    monkeypatch.chdir(tmp_path)
    if setup is not None:
        setup(tmp_path)
    code = cli.main(argv)
    captured = capsys.readouterr()
    assert code == 0, f"Unexpected exit code {code} for {argv}. stderr: {captured.err}"
    _assert_exactly_one_footer(captured.out, label=" ".join(argv))


@pytest.mark.parametrize(
    "argv_factory,fixture_name",
    [
        (
            lambda: ["overview", "--agent", "claude-code"],
            "typical",
        ),
        (
            lambda: ["overview", "--agent", "codex"],
            "typical",
        ),
        (
            lambda: ["overview", "--agent", "copilot"],
            "typical",
        ),
        (
            lambda: ["overview", "--agent", "acp"],
            "typical",
        ),
        (
            lambda: ["overview", "--agent", "claude-code"],
            "empty",
        ),
    ],
)
def test_footer_present_once__overview(
    argv_factory: Callable[[], list[str]],
    fixture_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """overview emits exactly one footer for each backend and fixture."""
    project = _copy_fixture(fixture_name, tmp_path)
    monkeypatch.chdir(project)
    argv = argv_factory()
    code = cli.main(argv)
    captured = capsys.readouterr()
    assert code == 0, f"Exit {code} for {argv} / fixture={fixture_name}. stderr: {captured.err}"
    _assert_exactly_one_footer(captured.out, label=" ".join(argv))


# gamify only supports claude-code; codex / copilot / acp emit an unsupported
# notice without a footer — that gap is tracked as a known bug in
# test_gamify_unsupported_backends_missing_footer below.
_GAMIFY_SUPPORTED_BACKENDS = ("claude-code",)
_GAMIFY_UNSUPPORTED_BACKENDS = ("codex", "copilot", "acp")


@pytest.mark.parametrize("backend", _GAMIFY_SUPPORTED_BACKENDS)
def test_footer_present_once__gamify_install(
    backend: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """gamify install on supported backends emits exactly one footer."""
    monkeypatch.chdir(tmp_path)
    code = cli.main(["gamify", "--agent", backend])
    captured = capsys.readouterr()
    assert code == 0, f"Exit {code} for gamify --agent {backend}. stderr: {captured.err}"
    _assert_exactly_one_footer(captured.out, label=f"gamify install --agent {backend}")


@pytest.mark.parametrize("backend", _GAMIFY_SUPPORTED_BACKENDS)
def test_footer_present_once__gamify_uninstall(
    backend: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """gamify uninstall on supported backends emits exactly one footer."""
    monkeypatch.chdir(tmp_path)
    # Do a fresh uninstall (nothing installed yet) — this exercises the
    # 'nothing_to_remove' path for every backend.
    code = cli.main(["gamify", "--uninstall", "--agent", backend])
    captured = capsys.readouterr()
    assert code == 0, f"Exit {code} for gamify uninstall --agent {backend}. stderr: {captured.err}"
    _assert_exactly_one_footer(captured.out, label=f"gamify uninstall --agent {backend}")


@pytest.mark.xfail(
    reason=(
        "BUG: gamify unsupported-backend notice lacks a footer. "
        "The _unsupported_notice() helper in install.py returns a plain string "
        "with no render_footer() call. Fix: inject a neutral footer into "
        "_unsupported_notice() or call render_neutral_footer() before returning."
    ),
    strict=True,
)
@pytest.mark.parametrize("backend", _GAMIFY_UNSUPPORTED_BACKENDS)
def test_gamify_unsupported_backends_missing_footer(
    backend: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Tracks the known gap: gamify unsupported-backend notices have no footer.

    This test is expected to FAIL until the bug is fixed.  When fixed, the
    xfail mark should be removed and these backends should be added back to
    test_footer_present_once__gamify_install / test_footer_present_once__gamify_uninstall.
    """
    monkeypatch.chdir(tmp_path)
    code = cli.main(["gamify", "--agent", backend])
    captured = capsys.readouterr()
    assert code == 0
    # This assertion is expected to fail (xfail) because the unsupported notice
    # is returned without a footer.
    _assert_exactly_one_footer(captured.out, label=f"gamify unsupported --agent {backend}")


@pytest.mark.parametrize("backend", _BACKENDS)
def test_footer_present_once__hook_read_empty(
    backend: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """hook read (no events) emits exactly one footer for every backend."""
    monkeypatch.chdir(tmp_path)
    code = cli.main(["hook", "read", "--agent", backend])
    captured = capsys.readouterr()
    assert code == 0, f"Exit {code} for hook read --agent {backend}. stderr: {captured.err}"
    _assert_exactly_one_footer(captured.out, label=f"hook read empty --agent {backend}")


@pytest.mark.parametrize("backend", _BACKENDS)
def test_footer_present_once__hook_read_with_events(
    backend: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """hook read (with events) emits exactly one footer for every backend."""
    monkeypatch.chdir(tmp_path)
    # Write an event first (hook write is the only way to populate events; it is
    # silent itself and is separately tested for silence below).
    cli.main(["hook", "write", "post-tool-use", "tool=Read"])
    capsys.readouterr()
    code = cli.main(["hook", "read", "--agent", backend])
    captured = capsys.readouterr()
    assert code == 0, f"Exit {code} for hook read --agent {backend}. stderr: {captured.err}"
    _assert_exactly_one_footer(captured.out, label=f"hook read with events --agent {backend}")


# ---------------------------------------------------------------------------
# PR namespace: static assertion that every result template carries {{ footer }}
# ---------------------------------------------------------------------------


def test_pr_result_templates_contain_footer_variable() -> None:
    """Every pr result template (.md.j2) must contain '{{ footer }}' so the
    footer is injected at render time.  This is a static guarantee that does
    not invoke gh or the network."""
    templates_pkg = files("devex.commands.pr.assets.templates")
    # All .md.j2 files under the templates package that represent command
    # results (all except any __init__ shims).
    found: list[str] = []
    missing: list[str] = []
    for name in (
        "delta.md.j2",
        "lint_result.md.j2",
        "pr_await_detached.md.j2",
        "pr_briefing.md.j2",
        "pr_open_result.md.j2",
        "pr_reply_result.md.j2",
        "pr_review_result.md.j2",
    ):
        node = templates_pkg.joinpath(name)
        assert node.is_file(), f"Expected template {name} to exist in the package"
        content = node.read_text(encoding="utf-8")
        found.append(name)
        if "{{ footer }}" not in content:
            missing.append(name)

    assert len(found) > 0, "No pr result templates located — package path may be wrong"
    assert missing == [], f"PR result template(s) missing '{{{{ footer }}}}' injection: {missing}"


# ---------------------------------------------------------------------------
# 2. Determinism — byte-identical stdout on two identical runs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["explain", "explain"],
        ["explain", "explain", "--agent", "claude-code"],
        ["explain", "devex", "--agent", "codex"],
        ["learn", "--agent", "claude-code"],
        ["learn", "introspect", "--agent", "acp"],
        ["doctor"],
        ["doctor", "--agent", "copilot"],
    ],
)
def test_footer_deterministic__no_project_dir(
    argv: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Running the same command twice on identical state produces byte-identical stdout."""
    monkeypatch.chdir(tmp_path)
    cli.main(argv)
    first = capsys.readouterr().out
    cli.main(argv)
    second = capsys.readouterr().out
    assert first == second, (
        f"Non-deterministic output for {argv}. "
        f"First tail: {first[-200:]!r}, Second tail: {second[-200:]!r}"
    )


def test_footer_deterministic__overview(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """overview --agent claude-code is byte-identical across two runs on the same fixture."""
    project = _copy_fixture("typical", tmp_path)
    monkeypatch.chdir(project)
    cli.main(["overview", "--agent", "claude-code"])
    first = capsys.readouterr().out
    cli.main(["overview", "--agent", "claude-code"])
    second = capsys.readouterr().out
    assert first == second, "overview output is non-deterministic"


def test_footer_deterministic__hook_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """hook read is byte-identical across two runs when event state is identical."""
    monkeypatch.chdir(tmp_path)
    cli.main(["hook", "write", "post-tool-use", "tool=Bash"])
    capsys.readouterr()
    cli.main(["hook", "read", "--agent", "claude-code"])
    first = capsys.readouterr().out
    cli.main(["hook", "read", "--agent", "claude-code"])
    second = capsys.readouterr().out
    assert first == second, "hook read output is non-deterministic"


def test_footer_deterministic__gamify_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """gamify install footer is byte-identical on two runs.

    The body text changes between first and second run (added vs already-present),
    but the footer block itself must be identical — the footer is purely determined
    by the backend and rule key, not by install state.
    """
    monkeypatch.chdir(tmp_path)

    def _extract_footer(out: str) -> str:
        assert _FOOTER_BLOCK_PREFIX in out, "No footer found in gamify output"
        return out[out.rindex(_FOOTER_BLOCK_PREFIX) :]

    cli.main(["gamify", "--agent", "claude-code"])
    footer_first = _extract_footer(capsys.readouterr().out)
    cli.main(["gamify", "--agent", "claude-code"])
    footer_second = _extract_footer(capsys.readouterr().out)
    assert footer_first == footer_second, (
        f"gamify footer is non-deterministic across runs.\n"
        f"Run 1: {footer_first!r}\nRun 2: {footer_second!r}"
    )


# ---------------------------------------------------------------------------
# 3. No new side effects + hook write silence
# ---------------------------------------------------------------------------


def test_hook_write_emits_empty_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """hook write MUST emit empty stdout — it is the one designated silent command."""
    monkeypatch.chdir(tmp_path)
    code = cli.main(["hook", "write", "post-tool-use", "tool=Bash"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "", f"hook write must stay silent; got {captured.out[:200]!r}"
    assert _FOOTER_MARKER not in captured.out


def test_hook_write_multiple_events_each_silent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """hook write remains silent across all supported event types."""
    monkeypatch.chdir(tmp_path)
    for event in ("post-tool-use", "user-prompt", "stop"):
        code = cli.main(["hook", "write", event])
        captured = capsys.readouterr()
        assert code == 0, f"hook write {event} exit {code}"
        assert captured.out == "", f"hook write {event} emitted output: {captured.out[:200]!r}"


def test_readonly_commands_do_not_sleep(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Read-only commands (overview, explain) must not call time.sleep.

    The footer path must be purely computational.  If any sleep is introduced
    in the footer render chain this test will catch it.
    """
    sleep_calls: list[float] = []

    def _capturing_sleep(secs: float) -> None:
        sleep_calls.append(secs)

    monkeypatch.setattr(_time, "sleep", _capturing_sleep)

    monkeypatch.chdir(tmp_path)

    # overview (needs a project dir)
    project = _copy_fixture("typical", tmp_path)
    monkeypatch.chdir(project)
    cli.main(["overview", "--agent", "claude-code"])
    capsys.readouterr()
    assert sleep_calls == [], f"overview called time.sleep: {sleep_calls}"

    # explain
    monkeypatch.chdir(tmp_path)
    cli.main(["explain", "explain", "--agent", "claude-code"])
    capsys.readouterr()
    assert sleep_calls == [], f"explain called time.sleep: {sleep_calls}"


def test_readonly_commands_do_not_open_network_connections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Read-only commands (doctor, hook read) must not open any network sockets.

    If the footer machinery ever accidentally resolves a hostname or dials out,
    this test will catch it.
    """
    connection_attempts: list[tuple] = []

    _original_connect = _socket.socket.connect

    def _spy_connect(self, address):  # type: ignore[no-untyped-def]
        connection_attempts.append(address)
        return _original_connect(self, address)

    monkeypatch.setattr(_socket.socket, "connect", _spy_connect)

    monkeypatch.chdir(tmp_path)

    # doctor
    cli.main(["doctor"])
    capsys.readouterr()
    assert connection_attempts == [], f"doctor opened network connection(s): {connection_attempts}"

    # hook read (empty)
    cli.main(["hook", "read", "--agent", "claude-code"])
    capsys.readouterr()
    assert (
        connection_attempts == []
    ), f"hook read opened network connection(s): {connection_attempts}"


# ---------------------------------------------------------------------------
# 4. Pre-change gap: body templates contain no literal 'Next step:' text
# ---------------------------------------------------------------------------


def _collect_body_templates() -> list[Path]:
    """Return all .md.j2 body templates, excluding the footer template and
    the pr/assets/templates/ folder (which legitimately renders {{ footer }}).

    We search the shipped package tree via importlib.resources so this works
    regardless of whether the package is installed from source or as a wheel.
    """
    # Walk the installed package tree looking for .md.j2 files.
    src_root = Path(__file__).parent.parent / "src" / "devex"
    if not src_root.is_dir():
        # Installed from wheel — fall back to the importlib path.
        import devex  # noqa: PLC0415

        src_root = Path(devex.__file__).parent

    results: list[Path] = []
    for path in src_root.rglob("*.md.j2"):
        # Skip the footer template itself (it's supposed to contain 'Next step:')
        if path.name == "footer.md.j2":
            continue
        # Skip pr result templates (they contain '{{ footer }}' which EXPANDS to 'Next step:')
        if "pr" in path.parts and "templates" in path.parts:
            continue
        results.append(path)
    return results


def test_body_templates_contain_no_literal_next_step() -> None:
    """Body templates must contain no hard-coded 'Next step:' text.

    Before the footer machinery existed, 'Next step:' simply didn't appear in
    rendered output.  This test pins that invariant: the footer block is the
    ONLY source of the next-step line, and it lives in footer.md.j2, not in
    the per-command body templates.
    """
    body_templates = _collect_body_templates()
    assert len(body_templates) > 0, (
        "No body templates found — check the source tree path in " "_collect_body_templates()."
    )

    offenders: list[str] = []
    for path in sorted(body_templates):
        content = path.read_text(encoding="utf-8")
        if "Next step:" in content:
            offenders.append(str(path))

    assert offenders == [], (
        "The following body templates contain a hard-coded 'Next step:' string "
        "(the footer is the sole permitted source):\n" + "\n".join(f"  {p}" for p in offenders)
    )


def test_footer_template_is_the_only_source_of_next_step_block() -> None:
    """footer.md.j2 must contain the '**Next step:**' pattern; every other
    .md.j2 template must NOT — confirming the structural isolation."""
    src_root = Path(__file__).parent.parent / "src" / "devex"
    if not src_root.is_dir():
        import devex  # noqa: PLC0415

        src_root = Path(devex.__file__).parent

    footer_path = src_root / "core" / "assets" / "footer.md.j2"
    assert footer_path.is_file(), f"footer.md.j2 not found at {footer_path}"
    footer_content = footer_path.read_text(encoding="utf-8")
    assert (
        "**Next step:**" in footer_content
    ), "footer.md.j2 does not contain '**Next step:**' — the template appears broken."

    # All other .md.j2 files must not contain the literal marker
    # (pr result templates expand it via {{ footer }}, but don't have it literally)
    offenders: list[str] = []
    for path in sorted(src_root.rglob("*.md.j2")):
        if path == footer_path:
            continue
        content = path.read_text(encoding="utf-8")
        if "**Next step:**" in content:
            offenders.append(str(path))

    assert offenders == [], (
        "These non-footer templates contain a literal '**Next step:**' string "
        "(should only ever appear via {{ footer }} injection):\n"
        + "\n".join(f"  {p}" for p in offenders)
    )
