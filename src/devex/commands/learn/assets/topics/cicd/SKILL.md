---
name: cicd
description: How to use `devex pr` to ship a PR end-to-end — lint, open with auto-signature, fetch the unified briefing (status + comments + readiness), batch-reply with thread resolution, and run alignment-delta when needed.
type: lesson
---

# Lesson — CI/CD with `devex pr` for {{ backend }}

The full PR loop boils down to six commands. Each one ends with a
**Next step:** footer that names the right next command — chain it.

## Standard happy path

```bash
git checkout -b feat/<desc>
# ... edit ...
devex pr lint --agent {{ backend }}            # portability + alignment
git commit -am "..." && git push -u origin <branch>

devex pr open --agent {{ backend }} \
    --title "..." --body-file ./body.md \
    --delayed-read                          # creates PR + waits 180s + briefing

# briefing arrived; triage and prepare replies.jsonl, then:
devex pr reply <PR> --agent {{ backend }} < replies.jsonl

# fix anything, push, then:
devex pr read <PR> --agent {{ backend }} --wait 180
# repeat until reviewers quiet + CI green
# wait for human merge — never merge yourself
```

## `read --wait` vs. `await`

Both poll the same readiness loop. They differ on what they do with
the result:

- `devex pr read <PR> --wait 180` — always exits 0. Renders the briefing
  and lets the agent decide. Use when you want the unified view.
- `devex pr await <PR>` — exits **1** on SonarCloud gate `ERROR`,
  unresolved review threads, or failing CI checks; **0** otherwise
  (clean state or timeout). Use when you want to gate the next command
  on PR health (e.g., in a shell loop that should fail if Sonar or CI
  is red).

## When CLAUDE.md / culture.yaml / .claude/skills change

`devex pr lint` flags this and points you at:

```bash
devex pr delta --agent {{ backend }}
```

Read each sibling's CLAUDE.md head + culture.yaml, decide whether each
needs a follow-up PR, and mention any drift in your reply.

## JSONL reply shape

Each line of stdin to `devex pr reply <PR>`:

```json
{"in_reply_to": 123456, "thread_id": "T_kw...", "body": "Fixed in <commit>."}
```

- `in_reply_to` is the inline review-comment id. Omit for top-level conversation comments.
- `thread_id` triggers `resolveReviewThread` after the post.
- `body` is auto-signed with `- <nick> (Claude)` if the signature is missing. `<nick>` comes from the first agent's `suffix` in `culture.yaml`, falling back to the repo basename.

## Side effects

Network: every command except `lint` and `delta` talks to GitHub via `gh`.
Disk: `pr open`, `pr read`, and `pr reply` append events to
`.devex/data/pr/events.jsonl` for retrospective tooling.

## When something goes wrong

- `gh` not installed → `agex: install gh — https://cli.github.com/ — then rerun`
- `gh` not authenticated → `agex: run 'gh auth login' then rerun`
- `pr reply` partial failure → stderr names the line slice to resubmit; the
  command stops at the first failure to keep recovery surgical.
- `pr read --wait` / `pr await` timeout → exit 0 with a "Still waiting on:
  <reviewers>" banner; rerun the same command to keep waiting.

## Long waits (5-minute cache TTL)

Anthropic's prompt cache has a 5-minute TTL. If you expect to wait
longer than that — for example, polling a slow CI gate with
`devex pr read <PR> --wait 600` or `devex pr await <PR> --max-wait 1800`
— run the wait inside a subagent and triage the result when it fires.
The parent session keeps its cache warm; only the subagent pays the
per-iteration cost.

Pattern (Claude Code): spawn an `Agent(..., run_in_background=true)`
that runs the command and echoes the final headline + exit code.
Continue with unrelated work; act on the notification when it
arrives. This is exactly how steward's `cicd` workflow handles its
`workflow.sh await <PR>` chains.

## Reply etiquette

Every comment gets a reply — no silent fixes. Always include a
`thread_id` so the thread closes automatically. Reference the fix-up
commit SHA in the reply body where relevant.
