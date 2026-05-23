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

# agex's `--agent` accepts claude-code|codex|copilot|acp (plus a `claude`
# alias added in #46). We default to the canonical `claude-code` because it
# is accepted by *every* agex version — the `claude` alias is absent from
# older installs (e.g. a globally pinned 0.18.0). resolve_backend() would
# also fall back to culture.yaml when --agent is omitted, but passing it
# explicitly keeps the wrapper robust across versions. Override via
# AGEX_PR_AGENT to run under codex/copilot/acp.
AGEX_AGENT="${AGEX_PR_AGENT:-claude-code}"

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

case "$cmd" in
    lint)
        require_agex
        exec agex pr lint --agent "$AGEX_AGENT" --exit-on-violation "$@"
        ;;
    open)
        require_agex
        exec agex pr open --agent "$AGEX_AGENT" --delayed-read "$@"
        ;;
    read)
        require_agex
        exec agex pr read --agent "$AGEX_AGENT" "$@"
        ;;
    reply)
        require_agex
        PR="${1:?Usage: workflow.sh reply <PR>  (JSONL on stdin)}"
        exec agex pr reply --agent "$AGEX_AGENT" "$PR"
        ;;
    delta)
        require_agex
        exec agex pr delta --agent "$AGEX_AGENT" "$@"
        ;;
    await)
        require_agex
        exec agex pr await --agent "$AGEX_AGENT" "$@"
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
