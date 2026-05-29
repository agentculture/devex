# Every devex command now closes with a deterministic, per-backend Next step micro-prompt telling the running agent exactly how to continue — the pr namespace footer convention becomes a cross-command guarantee.

> Every devex command now closes with a deterministic, per-backend Next step micro-prompt telling the running agent exactly how to continue — the pr namespace footer convention becomes a cross-command guarantee.

## Audience

- Autonomous coding agents (claude-code, codex, copilot, acp backends) that invoke devex commands non-interactively and must pick their next move without an LLM in the loop.

## Before → After

- Before: Today only the pr namespace ends with a Next step footer. explain, learn, overview, doctor and hook read end at EOF; gamify install has a one-off ad-hoc Next line. After every other command the agent must guess the next move.
- After: Every non-silent devex command (explain, learn, overview, doctor, gamify, hook read, plus the existing pr namespace) ends its markdown with a Next step footer naming a concrete next move, so the agent never has to infer what to run next.

## Why it matters

- devex exists to give autonomous agents deterministic guidance. A command that ends without a next-move prompt leaves a decision gap the agent fills by guessing — non-deterministic behaviour in a tool whose whole premise is determinism. A closing micro-prompt makes the command surface self-chaining.

## Requirements

- The footer-rendering machinery now under commands/pr (the _footer renderer, the rule_key plus context decision pattern, and footer.md.j2) is promoted to core so every command shares one implementation.
  - honesty: After the machinery moves to core, the pr namespace footers are byte-identical and every existing pr footer test passes unchanged (pure relocation, no behaviour change).
- Each non-pr command gains a small next-step decision function returning rule_key plus context, and a hints block in its per-command assets/backends/backend.yaml, mirroring how the pr namespace is structured.
  - honesty: One enumerating test walks every (command, backend, reachable rule_key) triple and fails if any hint string is missing, proving coverage rather than assuming it.
- Backend-agnostic commands that do not take --agent today (explain, doctor) must still end with a coherent Next step footer.
  - honesty: With --agent provided, explain/doctor render that backend's hint; with it omitted they render a neutral hint from a shared default; both paths are test-covered so the optional flag never yields a missing or empty footer.

## Honesty conditions

- Every command path that reaches stdout terminates in exactly one Next step footer block — the guarantee is total, not best-effort — verified by a test that runs every non-silent command and asserts a trailing footer.
- Every footer hint is phrased as an actionable instruction to the running agent (an imperative naming a concrete next command/move), never human-facing prose — asserted by a test/lint on hint form.
- For each non-silent command there is a deterministic mapping from its observable end-state to exactly one rule_key, so the footer is reproducible across identical inputs.
- A snapshot test of current non-pr command output confirms none emits a Next step footer today, so the gap this feature closes is demonstrated, not assumed.
- The footer is fully determined by command inputs plus project state with zero LLM/network/random input — identical inputs always yield an identical footer, asserted by a reproducibility test.
- After the change hook write still emits empty stdout and no command gains a new network/file-write/sleep side effect from the footer — verified by the existing side-effect/invariant tests staying green.
- Both guard tests (every-command-ends-with-a-footer; every reachable rule_key has a hint) exist, run in CI, and fail loudly when a command or rule_key is added without a hint.

## Success signals

- A test asserts every non-silent command stdout ends with the footer block, and that each backend YAML defines a hint for every rule key its command can emit, so there is no missing-hint KeyError at runtime.

## Scope / boundaries

- Out of scope: rewriting command body content; LLM-generated footers; adding a footer to deliberately-silent commands such as hook write which emits empty stdout; and auto-executing the suggested command — the footer is a prompt, not an action, so no new side effects are introduced.

## Non-goals

- This is not a generalized workflow or command-graph engine; the footer suggests a single sensible next move, it does not model, validate or enforce a sequence of commands.

## Decisions

- Reuse the existing mechanism unchanged — rule_key plus context resolved against a per-backend hints YAML and rendered through footer.md.j2 as a Next step block under a horizontal rule — rather than inventing a new footer format.
- explain and doctor gain an OPTIONAL --agent flag: when provided the footer uses that backend's hints YAML, when omitted a backend-neutral footer is emitted from a shared default. Existing flagless calls keep working unchanged (non-breaking). [resolves q1, user choice]

## Hard questions

- How do explain and doctor (no --agent flag today) emit a per-backend Next step footer? (a) add optional --agent, neutral footer when omitted; (b) stay agnostic, emit one neutral footer with no per-backend phrasing; (c) make --agent required on them too, breaking their agnostic contract.
