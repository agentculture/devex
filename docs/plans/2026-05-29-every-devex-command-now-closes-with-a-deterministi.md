# Build Plan — Every devex command now closes with a deterministic, per-backend Next step micro-prompt telling the running agent exactly how to continue — the pr namespace footer convention becomes a cross-command guarantee.

slug: `every-devex-command-now-closes-with-a-deterministi` · status: `exported` · from frame: `every-devex-command-now-closes-with-a-deterministi`

> Every devex command now closes with a deterministic, per-backend Next step micro-prompt telling the running agent exactly how to continue — the pr namespace footer convention becomes a cross-command guarantee.

## Tasks

### t1 — Promote the footer-rendering machinery from commands/pr into core (pure relocation, no behaviour change)

- covers: c8, h1
- acceptance:
  - A new core module (core/footer.py) exposes render_footer plus hint-loading, and footer.md.j2 moves to a core assets location
  - All pr scripts import the footer renderer from core and pr footer output is byte-identical to before (snapshot diff empty)
  - The entire existing pr footer test suite passes unchanged

### t2 — Add neutral-default footer resolution to the core renderer for when no backend is supplied

- depends on: t1
- covers: c10, h5
- acceptance:
  - When render_footer is called with no backend it resolves hints from a shared neutral source and returns a valid Next step block
  - Unit test: the neutral path yields a non-empty footer and the backend-specific path is unchanged

### t3 — Add an optional --agent flag to explain and doctor and wire their Next step footers (backend hint when given, neutral when omitted)

- depends on: t2
- covers: c10, h5, c9
- acceptance:
  - devex explain TOPIC and devex doctor accept an optional --agent and existing flagless invocations keep working unchanged
  - With --agent the footer uses that backend per-command hints, without it the neutral footer is emitted, and both paths are covered by tests
  - Each of explain and doctor has a next-step decision function and a hints block (backend yamls plus neutral)

### t4 — Add a Next step footer to learn (menu and topic views) with a decision function and per-backend hints

- depends on: t1
- covers: c9, c3
- acceptance:
  - learn menu and learn TOPIC both end with a Next step footer chosen by a decision function returning a rule_key plus context
  - commands/learn/assets/backends per-backend yaml defines a hint for every rule_key learn can emit, for all four backends
  - Unit tests cover the menu and topic footers for at least one backend

### t5 — Add a Next step footer to overview with a decision function and per-backend hints

- depends on: t1
- covers: c9, c3
- acceptance:
  - overview ends with a Next step footer chosen by a decision function returning a rule_key plus context
  - commands/overview/assets/backends per-backend yaml defines a hint for every rule_key overview can emit, for all four backends
  - A unit test asserts the overview footer for at least one backend

### t6 — Replace gamify ad-hoc Next line with the structured Next step footer for install and uninstall

- depends on: t1
- covers: c9, c3
- acceptance:
  - gamify install and uninstall end with the structured footer and the old ad-hoc Next line is removed
  - commands/gamify/assets/backends per-backend yaml defines a hint for every rule_key gamify can emit, for all four backends
  - Unit tests cover the install and uninstall footers for at least one backend

### t7 — Add a Next step footer to hook read while keeping hook write silent

- depends on: t1
- covers: c9, c3
- acceptance:
  - hook read ends with a Next step footer chosen by a decision function, and hook write still emits empty stdout with no footer
  - commands/hook/assets/backends per-backend yaml defines a hint for every rule_key hook read can emit, for all four backends
  - Unit tests assert the hook read footer and that hook write output stays empty

### t8 — Add cross-command footer-guarantee tests: total coverage, determinism, no new side effects, and the pre-change gap

- depends on: t3, t4, t5, t6, t7
- covers: c1, c3, c4, c5, c6, h3, h4, h7, h8, h9
- acceptance:
  - A parametrized test runs every non-silent command and asserts stdout ends with exactly one Next step footer block
  - A determinism test runs each command twice on identical project state and asserts byte-identical footers (no LLM, network, or randomness)
  - A test asserts hook write emits empty stdout and that no command performs network, file-write, or sleep to build its footer
  - A test demonstrates the pre-change gap: with the footer block absent each command body contains no Next step marker

### t9 — Add hint-coverage and hint-form guard tests wired into the existing CI test job

- depends on: t3, t4, t5, t6, t7
- covers: c2, c7, h2, h6, h10
- acceptance:
  - An enumerating test walks every command-backend-rule_key triple and fails if any hint string is missing
  - A hint-form test asserts each hint is an imperative addressed to the agent that names a concrete devex command or move, not human prose
  - Both guard tests run under the existing pytest CI job and fail loudly when a command or rule_key is added without a hint

## Risks

- [unknown_nonblocking] Exact neutral-footer hint phrasing for explain and doctor is unspecified; builder picks concise agent-facing wording (task t3)
- [follow_up] The hint-form check (imperative naming a command) is heuristic and may need tuning to avoid false positives (task t9)
