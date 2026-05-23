#!/usr/bin/env bash
set -euo pipefail

# agex-cli cicd workflow — a thin typing-saver over agex-cli's own
# `agex pr` namespace. Every verb forwards straight to `agex pr <verb>`.
#
# Unlike steward's copy (where this script also carried `status`/`await`
# shell extensions to work around gaps in agex pr), agex-cli *is* the
# upstream of agex pr: `await` is native (gates on Sonar ERROR +
# unresolved threads + CI red), and `read` already surfaces the Sonar
# quality gate + Qodo findings. So there is nothing to wrap — just delegate.
#
# Subcommands:
#   lint                   `agex pr lint --exit-on-violation`. Portability +
#                          alignment-trigger check on the working diff.
#   open  [gh-pr flags]    `agex pr open --delayed-read "$@"`. Creates the PR,
#                          then polls for an initial briefing. Body via
#                          --body-file PATH or stdin; --title is required.
#   read  [PR] [--wait N]  `agex pr read "$@"`. One-shot briefing (CI checks,
#                          SonarCloud gate + new issues, Qodo findings, all
#                          comments, next-step footer). --wait N polls for
#                          reviewer readiness.
#   reply <PR>             `agex pr reply <PR>` (JSONL on stdin). agex
#                          auto-signs from culture.yaml + resolves threads.
#   delta                  `agex pr delta`. Sibling alignment dump.
#   await [PR] [--max-wait N]
#                          `agex pr await "$@"`. The "wake me when this PR is
#                          triage-able" verb: readiness poll → CI → Sonar gate
#                          → briefing, non-zero exit on Sonar ERROR / unresolved
#                          threads / CI failure.
#   help                   print this message

# Backend selection follows agex's own contract — we deliberately do NOT
# inject a default `--agent`. Design invariant #3 forbids backend
# defaulting / auto-detection; agex's `resolve_backend()` already provides
# the sanctioned no-flag path: an explicit --agent wins, else it reads
# `backend:` from this repo's culture.yaml (here `claude` → claude-code),
# else it fails fast. So leave AGEX_PR_AGENT unset to let culture.yaml
# decide; set it to force a backend (e.g. codex / copilot / acp).
AGENT_ARGS=()
if [ -n "${AGEX_PR_AGENT:-}" ]; then
    AGENT_ARGS=(--agent "$AGEX_PR_AGENT")
fi

require_agex() {
    if ! command -v agex >/dev/null 2>&1; then
        echo "✗ agex not on PATH." >&2
        echo "  This repo *is* agex-cli — run 'uv run agex …' from the repo," >&2
        echo "  or install it: 'uv pip install -e .' / 'uv tool install agex-cli'." >&2
        exit 2
    fi
}

cmd="${1:-help}"
shift || true

# Safe expansion of a possibly-empty array under `set -u` (portable to the
# bash 3.2 that ships on macOS).
agex_pr() { exec agex pr "$1" "${AGENT_ARGS[@]+"${AGENT_ARGS[@]}"}" "${@:2}"; }

case "$cmd" in
    lint)
        require_agex
        agex_pr lint --exit-on-violation "$@"
        ;;
    open)
        require_agex
        agex_pr open --delayed-read "$@"
        ;;
    read)
        require_agex
        agex_pr read "$@"
        ;;
    reply)
        require_agex
        PR="${1:?Usage: workflow.sh reply <PR>  (JSONL on stdin)}"
        agex_pr reply "$PR"
        ;;
    delta)
        require_agex
        agex_pr delta "$@"
        ;;
    await)
        require_agex
        agex_pr await "$@"
        ;;
    help|--help|-h)
        sed -n '13,31p' "${BASH_SOURCE[0]}" | sed 's/^# *//;s/^#$//'
        ;;
    *)
        echo "unknown subcommand: $cmd" >&2
        echo "run '$(basename "$0") help' for usage." >&2
        exit 2
        ;;
esac
