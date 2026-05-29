# Build Plan — devex now turns a push into continuous PR management: when you push commits to a branch that already has an open PR, devex automatically enters the same review-readiness wait a new PR gets (the ~3-minute poll), so follow-up commits get triaged without a manual step — and a push to a branch with no PR stays an ordinary push.

slug: `devex-now-turns-a-push-into-continuous-pr-manageme` · status: `exported` · from frame: `devex-now-turns-a-push-into-continuous-pr-manageme`

> devex now turns a push into continuous PR management: when you push commits to a branch that already has an open PR, devex automatically enters the same review-readiness wait a new PR gets (the ~3-minute poll), so follow-up commits get triaged without a manual step — and a push to a branch with no PR stays an ordinary push.

## Tasks

### t1 — core/github.py: add git_push() and current_branch_pr() primitives (push-only; single gh pr view for PR detection)

- covers: c9, h1, c7, h10, c13
- acceptance:
  - git_push() runs exactly 'git push' of the current branch and nothing else (no commit/rebase/merge/stash/branch); unit test mocks the subprocess, asserts the git argv, and asserts a push failure surfaces as a raised/non-zero error.
  - current_branch_pr() returns the open PR number for the current branch via a single 'gh pr view --json' call, or None when there is no PR — never raises on the no-PR case; unit test mocks gh for both branches.

### t2 — docs: amend design-invariant #4 in CLAUDE.md to allow 'git push' as a 'devex push' side effect

- covers: c13, h3
- acceptance:
  - design-invariant #4 in CLAUDE.md names 'git push' (push-only) as an allowed side effect of 'devex push', listed alongside the existing pr-namespace gh/sleep carve-outs; the side-effects list and the prose are mutually consistent (no other invariant weakened).

### t3 — commands/push/: devex push command — git_push, detect open PR, route to blocking ~180s wait+delta (PR exists) or plain push + notice (no PR)

- depends on: t1
- covers: c1, h4, c3, h6, c5, h8, c6, h9
- acceptance:
  - With an open PR on the current branch, 'devex push' calls git_push then enters the existing pr read/await wait (default 180s) and renders the CI/Sonar/threads delta in ONE invocation; integration test (gh+git mocked) asserts no second command and the delta on stdout.
  - With no open PR, 'devex push' calls git_push then prints the deterministic 'no PR on this branch — open one with devex pr open' notice and exits 0; test asserts exit 0, the notice text, and that NO wait occurs.
  - Routing is deterministic on (current branch, PR-exists) with no backend/branch auto-detection — same inputs always select the same path (test).
  - On the managed path the exit code reflects the post-wait quality gate (non-zero on gate ERROR / unresolved threads), mirroring pr await (test).

### t4 — cli.py: register top-level 'devex push' subcommand with --max-wait (default 180) and --agent

- depends on: t3
- covers: c4, h7, c10, h2, c2, h5
- acceptance:
  - 'devex --help' lists 'push'; 'devex push --help' shows --max-wait (default 180) and --agent; parsing dispatches to the push command entry (test).
  - --max-wait overrides the 180s default and is threaded into the wait; the default equals pr open --delayed-read's 180 (test asserts the value reaches the wait call).
  - The command takes no interactive input — all inputs arrive via argv/flags; runs non-interactively to completion (test).

### t5 — commands/push/assets/backends/{claude-code,codex,copilot,acp}.yaml: per-backend next-step phrasing for the no-PR notice and the post-wait delta

- depends on: t3
- covers: c2, h5
- acceptance:
  - All four backends have a push asset with deterministic next-step phrasing for both the no-PR notice and the post-wait delta; test asserts all four load and render with no StrictUndefined errors (all-backends rule).

## Risks

- [unknown_nonblocking] Reusing pr read/await's wait+delta from the new command (t3) may need a shared helper extracted out of commands/pr/scripts if the logic isn't cleanly importable — could widen t3's file scope into commands/pr. (task t3)
