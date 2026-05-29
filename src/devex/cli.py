"""devex CLI — stdlib argparse front end.

No third-party CLI framework: this module routes `devex <command> [args]`
through `argparse` only, mirroring the skeleton used by the sibling Culture
repos (steward, devague). Business logic stays in `commands/<name>/scripts/`,
which return ``(stdout, exit_code, stderr)`` tuples; this module just parses
arguments and echoes those tuples. Adding a backend or command never touches
the parsing core beyond a `register_*` call.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from devex import __version__
from devex.commands.doctor.scripts import doctor as doctor_script
from devex.commands.explain.scripts import explain as explain_script
from devex.commands.gamify.scripts import install as gamify_script
from devex.commands.hook.scripts import read as hook_read_script
from devex.commands.hook.scripts import write as hook_write_script
from devex.commands.learn.scripts import learn as learn_script
from devex.commands.overview.scripts import overview as overview_script
from devex.commands.pr.scripts import await_ as pr_await_script
from devex.commands.pr.scripts import delta as pr_delta_script
from devex.commands.pr.scripts import lint as pr_lint_script
from devex.commands.pr.scripts import open_ as pr_open_script
from devex.commands.pr.scripts import read as pr_read_script
from devex.commands.pr.scripts import reply as pr_reply_script
from devex.commands.pr.scripts import review as pr_review_script
from devex.core.backend import parse_backend
from devex.core.prog import prog_name

_AGENT_HELP = "Backend: claude-code, codex, copilot, or acp."


def _gh_rerun_hint() -> str:
    """``<prog>: rerun once network is reachable`` — phrased with the invoked name."""
    return f"{prog_name()}: rerun once network is reachable (gh failed)"


class _AgexArgumentParser(argparse.ArgumentParser):
    """ArgumentParser used everywhere via ``parser_class=``.

    argparse's native ``error()`` already prints usage to stderr and exits
    with code 2 — which matches devex's existing bad-argument behavior — so no
    override is required. The subclass exists only so nested subparsers inherit
    it and to give a single place for any future tweak.
    """


# ---------------------------------------------------------------------------
# Output helpers — preserve the exact newline behavior of the old typer.echo
# calls. ``typer.echo(x, nl=False)`` wrote x verbatim; ``typer.echo(x)`` added
# a newline; ``err=True`` selected stderr.
# ---------------------------------------------------------------------------


def _emit(stdout: str, stderr: str, *, stderr_newline: bool = True) -> None:
    """Write a command's stdout/stderr the way the old CLI did."""
    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        if stderr_newline:
            print(stderr, file=sys.stderr)
        else:
            sys.stderr.write(stderr)


def _parse_backend_or_report(agent: Optional[str]):
    """Parse ``--agent`` into a Backend.

    Returns ``(backend, None)`` on success, or ``(None, 2)`` after printing the
    canonical ``agex: error: <msg>`` to stderr — letting the caller ``return``
    the exit code without exception gymnastics.
    """
    try:
        return parse_backend(agent), None
    except ValueError as exc:
        print(f"{prog_name()}: error: {exc}", file=sys.stderr)
        return None, 2


# ---------------------------------------------------------------------------
# Top-level command handlers
# ---------------------------------------------------------------------------


def _cmd_explain(args: argparse.Namespace) -> int:
    stdout, exit_code, stderr = explain_script.run(args.topic)
    _emit(stdout, stderr)
    return exit_code


def _cmd_doctor(args: argparse.Namespace) -> int:
    stdout, exit_code, stderr = doctor_script.run(args.role)
    _emit(stdout, stderr)
    return exit_code


def _cmd_learn(args: argparse.Namespace) -> int:
    backend, err = _parse_backend_or_report(args.agent)
    if err is not None:
        return err
    if args.topic is None:
        stdout, exit_code, stderr = learn_script.run_menu(backend)
    else:
        stdout, exit_code, stderr = learn_script.run_topic(args.topic, backend)
    _emit(stdout, stderr)
    return exit_code


def _cmd_gamify(args: argparse.Namespace) -> int:
    backend, err = _parse_backend_or_report(args.agent)
    if err is not None:
        return err
    if args.uninstall:
        stdout, exit_code, stderr = gamify_script.uninstall(backend)
    else:
        stdout, exit_code, stderr = gamify_script.install(backend)
    _emit(stdout, stderr)
    return exit_code


def _cmd_overview(args: argparse.Namespace) -> int:
    backend, err = _parse_backend_or_report(args.agent)
    if err is not None:
        return err
    stdout, exit_code, stderr = overview_script.run(backend)
    _emit(stdout, stderr)
    return exit_code


# ---------------------------------------------------------------------------
# hook subcommands
# ---------------------------------------------------------------------------


def _cmd_hook_write(args: argparse.Namespace) -> int:
    _, exit_code, stderr = hook_write_script.run(args.event, args.args or [])
    _emit("", stderr)
    return exit_code


def _cmd_hook_read(args: argparse.Namespace) -> int:
    backend, err = _parse_backend_or_report(args.agent)
    if err is not None:
        return err
    stdout, exit_code, stderr = hook_read_script.run(backend)
    _emit(stdout, stderr)
    return exit_code


# ---------------------------------------------------------------------------
# pr subcommands
# ---------------------------------------------------------------------------


def _cmd_pr_lint(args: argparse.Namespace) -> int:
    try:
        stdout, exit_code, stderr = pr_lint_script.run(
            agent=args.agent, project_dir=Path.cwd(), exit_on_violation=args.exit_on_violation
        )
    except ValueError as exc:
        print(f"{prog_name()}: {exc}", file=sys.stderr)
        return 2
    _emit(stdout, stderr)
    return exit_code


def _cmd_pr_open(args: argparse.Namespace) -> int:
    try:
        stdout, exit_code, stderr = pr_open_script.run(
            agent=args.agent,
            project_dir=Path.cwd(),
            title=args.title,
            body_file=args.body_file,
            draft=args.draft,
            delayed_read=args.delayed_read,
            detached_await=args.detached_await,
        )
    except ValueError as exc:
        print(f"{prog_name()}: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        prog = prog_name()
        print(str(exc), file=sys.stderr)
        print(f"{prog}: rerun '{prog} pr open ...' once network is reachable", file=sys.stderr)
        return 1
    _emit(stdout, stderr)
    return exit_code


def _cmd_pr_reply(args: argparse.Namespace) -> int:
    try:
        stdout, exit_code, stderr = pr_reply_script.run(
            agent=args.agent, project_dir=Path.cwd(), pr=args.pr
        )
    except ValueError as exc:
        print(f"{prog_name()}: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        print(_gh_rerun_hint(), file=sys.stderr)
        return 1
    _emit(stdout, stderr, stderr_newline=False)
    return exit_code


def _cmd_pr_read(args: argparse.Namespace) -> int:
    try:
        stdout, exit_code, stderr = pr_read_script.run(
            agent=args.agent, project_dir=Path.cwd(), pr=args.pr, wait=args.wait
        )
    except ValueError as exc:
        print(f"{prog_name()}: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        print(_gh_rerun_hint(), file=sys.stderr)
        return 1
    _emit(stdout, stderr)
    return exit_code


def _cmd_pr_await(args: argparse.Namespace) -> int:
    try:
        if args.check:
            stdout, exit_code, stderr = pr_await_script.check(
                agent=args.agent, project_dir=Path.cwd(), pr=args.pr
            )
        elif args.detach:
            stdout, exit_code, stderr = pr_await_script.detach(
                agent=args.agent, project_dir=Path.cwd(), pr=args.pr, max_wait=args.max_wait
            )
        else:
            stdout, exit_code, stderr = pr_await_script.run(
                agent=args.agent, project_dir=Path.cwd(), pr=args.pr, max_wait=args.max_wait
            )
    except ValueError as exc:
        print(f"{prog_name()}: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        print(_gh_rerun_hint(), file=sys.stderr)
        return 1
    _emit(stdout, stderr)
    return exit_code


def _cmd_pr_review(args: argparse.Namespace) -> int:
    try:
        stdout, exit_code, stderr = pr_review_script.run(
            agent=args.agent, project_dir=Path.cwd(), pr=args.pr
        )
    except ValueError as exc:
        print(f"{prog_name()}: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        print(_gh_rerun_hint(), file=sys.stderr)
        return 1
    _emit(stdout, stderr)
    return exit_code


def _cmd_pr_delta(args: argparse.Namespace) -> int:
    try:
        stdout, exit_code, stderr = pr_delta_script.run(agent=args.agent, project_dir=Path.cwd())
    except ValueError as exc:
        print(f"{prog_name()}: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        print(_gh_rerun_hint(), file=sys.stderr)
        return 1
    _emit(stdout, stderr, stderr_newline=False)
    return exit_code


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def _add_agent_option(parser: argparse.ArgumentParser, *, required: bool, help_text: str) -> None:
    parser.add_argument("--agent", required=required, default=None, help=help_text)


def _group_help(parser: argparse.ArgumentParser):
    """Return a handler that prints a group's help to stderr and exits 2.

    Mirrors Typer's ``no_args_is_help`` for ``devex hook`` / ``devex pr`` invoked
    with no subcommand.
    """

    def _handle(_args: argparse.Namespace) -> int:
        parser.print_help(sys.stderr)
        return 2

    return _handle


def _build_parser() -> argparse.ArgumentParser:
    parser = _AgexArgumentParser(
        prog=prog_name(),
        description="Agent-operated developer-experience CLI.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", parser_class=_AgexArgumentParser)

    # explain
    p_explain = sub.add_parser("explain", help="Describe a command or concept.")
    p_explain.add_argument("topic", help="Topic to explain.")
    p_explain.set_defaults(func=_cmd_explain)

    # doctor
    p_doctor = sub.add_parser("doctor", help="Diagnose the project's devex setup.")
    p_doctor.add_argument(
        "--role", default=None, help="Render a role-specific check section (e.g., pr-review)."
    )
    p_doctor.set_defaults(func=_cmd_doctor)

    # learn
    p_learn = sub.add_parser("learn", help="Teach a lesson topic (or show the menu).")
    p_learn.add_argument("topic", nargs="?", default=None, help="Lesson topic (omit for menu).")
    _add_agent_option(p_learn, required=True, help_text=_AGENT_HELP)
    p_learn.set_defaults(func=_cmd_learn)

    # gamify
    p_gamify = sub.add_parser("gamify", help="Install (or uninstall) gamification.")
    _add_agent_option(p_gamify, required=True, help_text=_AGENT_HELP)
    p_gamify.add_argument("--uninstall", action="store_true", help="Reverse gamify.")
    p_gamify.set_defaults(func=_cmd_gamify)

    # overview
    p_overview = sub.add_parser("overview", help="Render the per-backend overview briefing.")
    _add_agent_option(p_overview, required=True, help_text=_AGENT_HELP)
    p_overview.set_defaults(func=_cmd_overview)

    _register_hook(sub)
    _register_pr(sub)

    return parser


def _register_hook(sub: argparse._SubParsersAction) -> None:
    hook_p = sub.add_parser("hook", help="Write and read devex tracking events.")
    hook_sub = hook_p.add_subparsers(dest="hook_command", parser_class=_AgexArgumentParser)

    p_write = hook_sub.add_parser("write", help="Append a tracking event.")
    p_write.add_argument("event", help="Event name (e.g., post-tool-use).")
    p_write.add_argument("args", nargs="*", help="Additional key=value pairs.")
    p_write.set_defaults(func=_cmd_hook_write)

    p_read = hook_sub.add_parser("read", help="Render tracked events for a backend.")
    _add_agent_option(p_read, required=True, help_text=_AGENT_HELP)
    p_read.set_defaults(func=_cmd_hook_read)

    hook_p.set_defaults(func=_group_help(hook_p))


def _register_pr(sub: argparse._SubParsersAction) -> None:
    pr_p = sub.add_parser("pr", help="GitHub PR lifecycle commands.")
    pr_sub = pr_p.add_subparsers(dest="pr_command", parser_class=_AgexArgumentParser)

    p_lint = pr_sub.add_parser("lint", help="Lint the PR branch state.")
    _add_agent_option(
        p_lint,
        required=False,
        help_text="Backend (claude-code|codex|copilot|acp); falls back to culture.yaml.",
    )
    p_lint.add_argument(
        "--exit-on-violation",
        action="store_true",
        help="Exit 1 when violations are found (CI mode).",
    )
    p_lint.set_defaults(func=_cmd_pr_lint)

    p_open = pr_sub.add_parser("open", help="Open a PR.")
    p_open.add_argument("--title", required=True)
    p_open.add_argument("--body-file", type=Path, default=None)
    p_open.add_argument("--draft", action="store_true", default=False)
    _add_agent_option(p_open, required=False, help_text=_AGENT_HELP)
    open_wait_group = p_open.add_mutually_exclusive_group()
    open_wait_group.add_argument(
        "--delayed-read",
        action="store_true",
        default=False,
        help="After create, immediately run `pr read --wait 180` (blocks this session).",
    )
    open_wait_group.add_argument(
        "--detached-await",
        action="store_true",
        default=False,
        help="After create, fork a detached `pr await` poller; return now (read with --check).",
    )
    p_open.set_defaults(func=_cmd_pr_open)

    p_reply = pr_sub.add_parser("reply", help="Reply to PR review threads.")
    p_reply.add_argument("pr", type=int)
    _add_agent_option(p_reply, required=False, help_text=_AGENT_HELP)
    p_reply.set_defaults(func=_cmd_pr_reply)

    p_read = pr_sub.add_parser("read", help="Read PR review state.")
    p_read.add_argument("pr", type=int, nargs="?", default=None)
    p_read.add_argument(
        "--wait",
        type=int,
        default=None,
        help=(
            "Upper bound in seconds to poll for required-reviewer readiness; "
            "returns early (down to waited=0s) once satisfied."
        ),
    )
    _add_agent_option(p_read, required=False, help_text=_AGENT_HELP)
    p_read.set_defaults(func=_cmd_pr_read)

    p_await = pr_sub.add_parser(
        "await",
        help="Wake-me-when-triage-able combo verb.",
        description=(
            "Polls readiness, runs CI + Sonar gate, renders briefing. Exits "
            "non-zero on quality-gate ERROR or unresolved review threads."
        ),
    )
    p_await.add_argument("pr", type=int, nargs="?", default=None)
    p_await.add_argument(
        "--max-wait",
        type=int,
        default=1800,
        help=(
            "Upper bound in seconds to poll for required-reviewer readiness; "
            "returns early (down to waited=0s) once satisfied (default 1800)."
        ),
    )
    detach_group = p_await.add_mutually_exclusive_group()
    detach_group.add_argument(
        "--detach",
        action="store_true",
        default=False,
        help=(
            "Fork a background poller that writes the verdict to a marker and "
            "return immediately (no in-session sleep). Read it later with --check."
        ),
    )
    detach_group.add_argument(
        "--check",
        action="store_true",
        default=False,
        help="Read a --detach run's marker without sleeping; print the verdict (or still-polling).",
    )
    _add_agent_option(p_await, required=False, help_text=_AGENT_HELP)
    p_await.set_defaults(func=_cmd_pr_await)

    p_review = pr_sub.add_parser(
        "review",
        help="Post the Qodo agentic-review trigger (/agentic_review) on a PR.",
    )
    p_review.add_argument("pr", type=int, nargs="?", default=None)
    _add_agent_option(p_review, required=False, help_text=_AGENT_HELP)
    p_review.set_defaults(func=_cmd_pr_review)

    p_delta = pr_sub.add_parser("delta", help="Show the delta since the last PR read.")
    _add_agent_option(p_delta, required=False, help_text=_AGENT_HELP)
    p_delta.set_defaults(func=_cmd_pr_delta)

    pr_p.set_defaults(func=_group_help(pr_p))


# ---------------------------------------------------------------------------
# Dispatch + entrypoint
# ---------------------------------------------------------------------------


def _dispatch(args: argparse.Namespace) -> int:
    rc = args.func(args)
    return rc if rc is not None else 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        # No top-level command given — mirror Typer's no_args_is_help (exit 2).
        parser.print_help(sys.stderr)
        return 2
    return _dispatch(args)


# Keep in sync with the sub.add_parser registrations above.
# If a new top-level command is added, extend this set so _main_entrypoint
# stops routing it to the unknown-command fallback page.
_KNOWN_COMMANDS = {"explain", "overview", "learn", "gamify", "hook", "doctor", "pr"}


def _main_entrypoint() -> None:
    """CLI entry point that routes unknown subcommands to ``devex explain devex``.

    When the first positional argument is not a known command (and is not a
    flag), print the ``devex explain devex`` page to stdout and the canonical
    error message to stderr, then exit with code 2.  All other invocations —
    known commands, ``--version``, ``--help``, zero-arg help — fall through to
    the normal ``main()`` dispatch unchanged.
    """
    argv = sys.argv[1:]
    if argv and not argv[0].startswith("-") and argv[0] not in _KNOWN_COMMANDS:
        print(f"{prog_name()}: error: unknown command '{argv[0]}'", file=sys.stderr)
        # `devex` here is the explain-topic identifier (topics/devex.md), not the
        # invoked command name — the canonical "what is this tool" page.
        stdout, _, _ = explain_script.run("devex")
        sys.stdout.write(stdout)
        sys.exit(2)
    sys.exit(main())


if __name__ == "__main__":
    _main_entrypoint()
