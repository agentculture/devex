# devex now turns a push into continuous PR management: when you push commits to a branch that already has an open PR, devex automatically enters the same review-readiness wait a new PR gets (the ~3-minute poll), so follow-up commits get triaged without a manual step — and a push to a branch with no PR stays an ordinary push.

> devex now turns a push into continuous PR management: when you push commits to a branch that already has an open PR, devex automatically enters the same review-readiness wait a new PR gets (the ~3-minute poll), so follow-up commits get triaged without a manual step — and a push to a branch with no PR stays an ordinary push.

## Audience

- An agent (or human via an agent) running devex inside a repo mid-PR, who has just committed follow-up changes on a branch that already has an open PR and wants CI/review feedback picked up automatically.

## Before → After

- Before: Today there is no push command. After pushing, the agent must remember to manually run 'pr await' / 'pr read --wait' to re-enter triage — easy to forget, so continuous PR management silently breaks.
- After: Pushing follow-up commits to a branch with an open PR automatically enters the same review-readiness wait a new PR gets (~3-minute poll), with no separate manual 'pr await' / 'pr read --wait' step.

## Why it matters

- Continuous PR management: every push, like every new PR, deterministically lands the agent back in the triage loop instead of leaving fresh CI/Sonar/review feedback unwatched.

## Requirements

- The command must detect whether the current branch has an open PR (via gh) BEFORE deciding whether to enter the wait — the PR-management path is gated on PR existence, never auto-detected away from the user's branch.
  - honesty: Open-PR detection is a single 'gh pr view --json' style call on the current branch; no PR => exit 0 with a plain-push (or notice) path, never an error.
- The default post-push wait is ~180s (3 minutes), matching 'pr open --delayed-read' (pr read --wait 180), not pr await's 1800s default — overridable via a flag.
  - honesty: The 180s default is exposed as an overridable flag (e.g. --max-wait) and documented as matching the new-PR delayed read.
- Performing 'git push' of the current branch is a NEW class of side effect for devex (push-only; no commit); it requires an explicit carve-out added to design-invariant #4, alongside the existing pr-namespace network/sleep exceptions.
  - honesty: design-invariant #4 in CLAUDE.md is amended to name 'git push' as an allowed side effect of 'devex push', with the same explicitness as the existing gh/sleep carve-out — otherwise the feature violates a non-negotiable invariant.

## Honesty conditions

- Shipped behavior is exactly: push current branch; if it has an open PR, enter the new-PR-style ~180s readiness wait and render the delta; else plain push + a notice.
- The primary caller is an agent in an automated PR loop; the command needs no interactive input to choose the managed-vs-plain path.
- Post-push triage takes zero extra commands: the wait + delta render are part of the single 'devex push' invocation.
- Verified today: 'devex pr' has no push subcommand and no top-level push exists; re-entering triage requires a manual 'pr await' / 'pr read --wait'.
- Determinism: identical branch/PR state always routes to the same path (managed vs plain); no backend or branch auto-detection.
- Observable: one 'devex push' on a PR branch ends with the post-push CI/Sonar/threads delta on stdout, exit code reflecting the quality gate.
- Scope cap: the only git mutation devex performs is 'git push' of the current branch — no rebase/merge/stash/branch/commit.

## Success signals

- After a push on a PR branch, the agent ends up holding the post-push review delta (CI + Sonar + threads) without issuing a second command.

## Scope / boundaries

- Not a general git porcelain: the push path is the minimum to land commits on the remote; devex does not grow into a git front-end (no rebase/merge/stash/branch management).

## Non-goals

- When the branch has no open PR, devex does NOT open one — that stays an explicit 'pr open'. The push case with no PR is out of the PR-management path.

## Assumptions

- It reuses the existing readiness machinery — pr await --detach/--check and/or pr read --wait — rather than introducing a second poller implementation.

## Decisions

- Top-level 'devex push' (not 'devex pr push'): reads naturally for the no-PR 'just push' case and conditionally enters PR management when an open PR exists.
- Push-only: pushes already-committed work; devex does NOT stage or commit. Commit-push is out of scope for v0.1.
- After-push wait is BLOCKING ~180s (mirrors 'pr open --delayed-read' = 'pr read --wait 180'), not detached; --max-wait overrides. Resolves q2.

## Hard questions

- Does the command also 'git commit' (commit-push) or only 'git push' already-committed work? The user is unsure ('commit-pushing / just pushing').
- Is the wait blocking the agent session (like --delayed-read) or detached (like --detached-await/await --detach)? Continuous management argues for detached + later --check.
- risk: Naming as 'pr push' is odd when no PR exists (you'd 'pr push' a branch that has no PR) — top-level 'devex push' may read better for the plain-push case.

## Open / follow-up

- RESOLVED (push-only, c15): commit-push (stage+commit) is out of scope for v0.1; 'devex push' strictly pushes already-committed work.
