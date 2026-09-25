# CLAUDE.md

Claude Code entry point for this repository. The Claude <-> Santiago/Codex
harness is described in `docs/HARNESS_TEMPLATE.md`.

## Harness handoff rules (same in every repo)

These come from `docs/HARNESS_TEMPLATE.md` ("Rules for each role"), which is
identical in every repository that runs the Claude <-> Santiago/Codex loop.

1. Before any edit, post `CONTEXT_RECEIPT` as its own comment (on the PR once
   one exists).
2. After the last `git push`, post a **separate** comment on the **PR** whose
   first line is exactly `READY_FOR_SANTIAGO` and which contains
   `- exact head commit SHA: <sha>`, with `<sha>` copied from
   `git rev-parse HEAD`, never typed.
3. Push nothing after that comment, and never post `@codex review` yourself.
   A correction round repeats steps 1-2.
4. If a `HANDOFF_IGNORED` or `HARNESS_STALLED` comment appears, do exactly
   what it says.
