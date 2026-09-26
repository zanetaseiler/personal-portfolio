# Harness template (copy this to every repo)

One page for running the Claude ↔ Santiago/Codex loop in any repository.
`AGENTS.md` and `docs/AGENT_WORKFLOW.md` define the Block protocol, and
`docs/HARNESS_GOLDEN_PATH.md` (where present) covers label lifecycle. This page covers
what to install, what each role must post, and how to find where a Block
is stuck.

## The loop

```
Santiago opens a task Issue (label optional)
  → requeue/bridge fires Claude         → ROUTINE_DISPATCHED comment (github-actions)
  → Claude: CONTEXT_RECEIPT, code, PR, READY_FOR_SANTIAGO comment on the PR
  → handoff workflow posts "@codex review"
  → Codex reviews the exact head
       findings → Claude re-dispatched  → ROUTINE_DISPATCHED comment → correction → READY_FOR_SANTIAGO …
       clean    → VERIFIED comment      → harness merges automatically → MERGED comment
  Claude needs a decision → NEEDS_ZANETA → Žaneta answers ZANETA_DECISION → Claude restarted automatically
```

**One Block, one Claude session.** A Block is an Issue plus its open PR
(the PR that says `Closes #N`). Once the PR exists, Claude always runs on the
PR: a label put on the Issue is moved there. While a Claude session is still
working (started less than 60 minutes ago, no `READY_FOR_SANTIAGO` or
`NEEDS_ZANETA` since), no second session starts for the Block; a
`HANDOFF_IGNORED` comment names the running session instead. This stops two
sessions from pushing the same branch at once (Zoe #297/#298).

No human ever adds or re-adds a label. Every step leaves a comment, and
the watchdog posts `HARNESS_STALLED` (saying which step stopped and the fix)
when a step does not happen: a task never started, a Claude session that
ended without a handoff (after 60 minutes), a decision that did not restart
Claude, a handoff never posted, or Codex never answering.

## Shared kit: identical in every repo

Copy these files verbatim. When one changes, change it in
`zanetaseiler/trafficdom-growth-engine` first, then copy it everywhere.

| Path | Job |
| --- | --- |
| `.github/scripts/harness_handoff.py` | Decides whether a `READY_FOR_SANTIAGO` comment is a valid handoff; posts `HANDOFF_IGNORED` when not |
| `.github/scripts/harness_guard.py` (called by the bridge workflow and `codex-feedback-to-claude.yml`) | One Claude session per Block: routes an Issue's label to its open PR, refuses a second session while one is working |
| `.github/workflows/santiago-ready-label-trigger.yml` | Claude → `@codex review` (Handoff 2)* |
| `.github/workflows/codex-feedback-to-claude.yml` | Codex findings → re-start Claude (Handoff 3) |
| `.github/workflows/codex-clean-verified.yml` + `.github/scripts/harness_automerge.py` | Clean Codex review → `VERIFIED` → automatic merge of that exact head once its checks pass |
| `.github/workflows/harness-requeue.yml` + `.github/scripts/harness_requeue.py` | New task Issue → start Claude; `ZANETA_DECISION` → restart Claude. No manual label |
| `.github/workflows/harness-watchdog.yml` + `.github/scripts/harness_watchdog.py` | Reports silent stalls |
| `docs/HARNESS_TEMPLATE.md` (this file) and the "Harness handoff rules" block in `CLAUDE.md` | The rules |
| `test_harness_handoff.py`, `test_harness_requeue.py`, `test_harness_watchdog.py` (in the repo's tests folder) | Offline tests; they find the repo root themselves |

\* Zoe keeps its own richer trigger (Issue→PR relay, wake markers,
`santiago-wake-reconciler.yml`), but it calls `harness_handoff.py
--check-only` for the parsing, so the handoff rules are the same.

## Repo-specific (may differ, same contract)

- `scripts/claude_cloud_bridge.py` + `.github/workflows/claude-cloud-routine-bridge.yml`
  (Handoff 1). Every version takes `--repo` and `--issue`/`--pr`, removes
  `READY_FOR_CLAUDE_CLOUD` on success and posts `ROUTINE_DISPATCHED`, or
  posts `ROUTINE_FIRE_FAILED` on failure. That contract is what the rest of
  the kit relies on. The workflow's `jobs:` section (`route`, then `fire` under a
  per-Block lock with `harness_guard.py check` before the bridge) is the
  same in every repo; only its header comment differs.
- Label cleanup on closed items (`harness-label-close-cleanup.yml` /
  `harness-label-reconciler.yml`) where a repo has it.
- `santiago-changes-requested-requeue.yml` (a human `CHANGES_REQUESTED`
  comment re-queues Claude) where a repo has it; Zoe deliberately does not.
- Retired everywhere: `controller-claude-label-bridge.yml` and every
  `controller:*` label. Apply `READY_FOR_CLAUDE_CLOUD` directly.

## One-time human setup per repo

1. Secrets: `CLAUDE_ROUTINE_FIRE_URL`, `CLAUDE_ROUTINE_FIRE_TOKEN` (the
   Claude Routine for this repo), and `SANTIAGO_CODEX_BRIDGE_TOKEN` (a token
   for the repo owner's account; Codex only answers `@codex review` from a
   real user).
2. Labels: `READY_FOR_CLAUDE_CLOUD`, `READY_FOR_SANTIAGO`, `VERIFIED`.
   Optional repository variable `HARNESS_HUMAN_LOGIN`: the one GitHub login
   allowed to post `READY_FOR_SANTIAGO` (default `zanetaseiler`). The
   repository owner is never used, since for an organization repo such as
   `bonafide-nitro/bonafide-website` that is the organization, not a person.
3. Codex GitHub connector enabled for the repo.
4. Test it: open a tiny Issue with the label. Within 2 minutes you should see
   `ROUTINE_DISPATCHED`.

## Rules for each role

**Santiago (creating work)**
- Every task Issue contains the line `Mandatory workflow: CONTEXT_RECEIPT →
  Claude Code implementation → PR → READY_FOR_SANTIAGO exact SHA → Santiago
  review → Žaneta merge/deploy approval`. That line is what starts Claude
  automatically when the Issue is opened; the label is optional.
- Put `HOLD` in the title for an Issue that must not start yet.
- Once a Block has a PR, work happens on the PR. You never need to re-label
  anything; a label on the Issue is moved to the PR, and a second start
  while Claude is still working is refused.
- Never open a duplicate: a second Issue with the same title within 30
  minutes is not started and gets `HANDOFF_IGNORED`.
- Put every decision the task depends on into the Issue. If one is still
  open, ask Žaneta before creating it.
- Within 2 minutes, a `ROUTINE_DISPATCHED` comment appears. If
  `ROUTINE_FIRE_FAILED` appears instead, read its error.

**Žaneta**
- Answer a `NEEDS_ZANETA` with a comment whose first line is
  `ZANETA_DECISION` (anything may follow on that line, e.g. a date). That
  restarts Claude; nothing else is needed.
- Nothing to merge: a `VERIFIED` PR merges automatically (standing decision,
  2026-09-25) and gets a `MERGED` comment. If `AUTO_MERGE_SKIPPED` appears
  instead, it says why (a check this PR broke, a conflict, a push after
  VERIFIED) and what to do.
- To keep a PR from merging on its own, put `HOLD` in its title or add the
  label `NO_AUTO_MERGE`.

**Claude (every session)**
- Before any edit: a `CONTEXT_RECEIPT` comment (its own comment).
- After the last push: a separate comment on the **PR**:

  ```
  READY_FOR_SANTIAGO

  - Block number: #<issue>
  - exact head commit SHA: <paste `git rev-parse HEAD` output, after pushing>
  - implemented: …
  - deliberately not implemented: …
  - files changed: …
  - tests and results: …
  - live/external effects: none
  - scope deviations: none
  - any required human setup: none
  ```

- `READY_FOR_SANTIAGO` goes on the first line. Push nothing after posting
  it, and never post `@codex review` yourself.
- **Never end a session without `READY_FOR_SANTIAGO` or `NEEDS_ZANETA` on
  GitHub.** Nobody reads the session chat; a question left only there stops
  the work silently. The same rule belongs in the Claude Routine's own
  prompt (configured in claude.ai, not in the repo).

**Codex** needs no special behavior. Findings can be inline or P0–P3 in the
summary; both re-start Claude.

## What each automatic comment means

| Comment (author) | Meaning | You do |
| --- | --- | --- |
| `ROUTINE_DISPATCHED` (github-actions) | Claude started | nothing |
| `ROUTINE_FIRE_FAILED` (github-actions) | Claude could not be started | read the error, re-add the label |
| `@codex review` right after `READY_FOR_SANTIAGO` | Handoff accepted | nothing |
| `HANDOFF_IGNORED` (github-actions) | Handoff rejected; reason inside | do what the reason says |
| `VERIFIED` (github-actions) | Codex found nothing on this head | nothing; it merges automatically |
| `MERGED` (github-actions) | The VERIFIED head was merged | nothing |
| `AUTO_MERGE_SKIPPED` (github-actions) | VERIFIED, but not merged; reason inside | do what the reason says |
| `HARNESS_SETUP_PROBLEM` (github-actions) | A step could not run because the `SANTIAGO_CODEX_BRIDGE_TOKEN` secret is missing or GitHub refused it; GitHub's own error is inside | fix the secret as it says, then re-run the failed run |
| `HARNESS_STALLED` (github-actions) | A step silently stopped; the step and fix are inside | do the one fix it names |
| `NEEDS_ZANETA` (Claude) | A human decision is needed | reply `ZANETA_DECISION …` |

## Where is it stuck?

On the Issue/PR, find the last automatic comment in the table above. The
next step in "The loop" is the one that did not happen. The watchdog checks
the same thing every 15 minutes and names it for you.
