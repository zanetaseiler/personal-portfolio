"""
Claude -> Santiago handoff: decide whether a PR comment is a valid
`READY_FOR_SANTIAGO` handoff, and if so wake Codex with `@codex review`.

Run by `.github/workflows/santiago-ready-label-trigger.yml`. See
`docs/HARNESS_TEMPLATE.md` for the whole loop.

Why this exists (Issue #203/PR #204 and PR #206, 2026-09-24): the previous
inline parser required `READY_FOR_SANTIAGO` to be the comment's *first*
line and a byte-exact `exact head commit SHA:` phrase carrying the full
40-character SHA. `docs/AGENT_WORKFLOW.md`'s own correction-comment format
puts `CONTEXT_RECEIPT` first and `READY_FOR_SANTIAGO` later, so every
correction-round handoff that followed the protocol exactly was dropped with
a green check and no comment, and the PR sat idle until a human noticed.

The rules are now deliberately forgiving, and every rejection is loud:

* The keyword counts on *any* standalone line (outside a ``` fence), after
  stripping Markdown decoration (`## READY_FOR_SANTIAGO`,
  `**READY_FOR_SANTIAGO**`, trailing colon). This matches the "last
  standalone keyword line" rule `scripts/claude_task_status.py` already
  uses for the rest of the harness.
* The head check looks at every 7-40 character hex token in the comment and
  accepts the handoff if any token's first 7 characters match the PR's
  current head. Seven characters is git's own short-SHA length; it also
  tolerates an agent that got the short SHA right but mistyped the tail.
* If the keyword is present but the handoff cannot be accepted (posted on
  an Issue, wrong author, no SHA, stale SHA), a `HANDOFF_IGNORED` comment
  says exactly why and what to post instead. A comment without the keyword
  line is an ordinary comment and is ignored silently.

`HANDOFF_IGNORED` is posted with the workflow's own `GITHUB_TOKEN`, which
GitHub never lets trigger another workflow run, so it cannot loop.
"""

import argparse
import json
import os
import re
import subprocess
import sys

KEYWORD = "READY_FOR_SANTIAGO"
SHORT_SHA = 7
_HEX_TOKEN = re.compile(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])")

HANDOFF = "handoff"
IGNORED = "ignored"
NOT_A_HANDOFF = "not_a_handoff"


def has_keyword_line(body, keyword=KEYWORD):
    """True when a line outside a ``` fence starts with `keyword`, ignoring
    Markdown decoration before it (`## `, `**`, `` ` ``, `> `) and allowing
    anything after it that is not part of a longer word -- so
    `ZANETA_DECISION — 2026-09-25` and `**READY_FOR_SANTIAGO**` count, but
    `READY_FOR_SANTIAGO_X` and a mid-sentence mention do not."""
    pattern = re.compile(rf"{re.escape(keyword)}(?!\w)")
    in_fence = False
    for line in (body or "").splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and pattern.match(line.strip().lstrip("#*`> \t")):
            return True
    return False


def sha_tokens(body):
    """Every 7-40 character lowercase-hex token in `body`, in order."""
    return _HEX_TOKEN.findall((body or "").lower())


def evaluate(*, body, author, owner, is_pr, current_head):
    # `owner` is the one human login allowed to hand off (the --human
    # argument: vars.HARNESS_HUMAN_LOGIN, else zanetaseiler). It is never
    # the repository owner, which for an organization repo is not a person.
    """Return `(decision, reason)` for one comment.

    `decision` is `HANDOFF` (wake Codex), `IGNORED` (keyword present but the
    handoff is not valid -- `reason` says why) or `NOT_A_HANDOFF` (no
    keyword line; stay silent)."""
    if not has_keyword_line(body):
        return NOT_A_HANDOFF, ""
    if not is_pr:
        return IGNORED, (
            "READY_FOR_SANTIAGO was posted on an Issue. Codex reviews PRs only -- "
            "post the handoff on the Block's PR instead.")
    if author != owner:
        return IGNORED, (
            f"READY_FOR_SANTIAGO was posted by `{author}`, not the authorized human "
            f"`{owner}` (repository variable HARNESS_HUMAN_LOGIN). Only that account "
            "can hand off to Santiago.")
    head = (current_head or "").lower()
    tokens = sha_tokens(body)
    if not tokens:
        return IGNORED, (
            "READY_FOR_SANTIAGO has no commit SHA in it. Add the line "
            f"`exact head commit SHA: {head}`.")
    if any(head.startswith(token[:SHORT_SHA]) for token in tokens):
        return HANDOFF, f"handoff accepted for head {head}"
    return IGNORED, (
        f"no SHA in this READY_FOR_SANTIAGO matches the PR's current head `{head}` "
        "(a commit was probably pushed after the comment was written). Post a new "
        f"READY_FOR_SANTIAGO with `exact head commit SHA: {head}`.")


def ignored_notice(reason, effect=("Codex was NOT asked to review. Nothing will happen on "
                                    "this PR until a valid handoff is posted.")):
    return (
        "HANDOFF_IGNORED\n\n"
        f"- reason: {reason}\n"
        f"- effect: {effect}\n"
        "- format: see `docs/HARNESS_TEMPLATE.md`.\n")


class GhError(RuntimeError):
    """A `gh` call GitHub refused; the message is GitHub's own error text."""


def run_gh(argv, token=None):
    """Run `gh`; on failure raise GhError carrying GitHub's error message
    (a bare CalledProcessError hides it -- bonafide PR #14, 2026-09-25)."""
    env = dict(os.environ)
    if token:
        env["GH_TOKEN"] = token
    result = subprocess.run(["gh", *argv], capture_output=True, text=True, env=env)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[:500] or f"exit status {result.returncode}"
        raise GhError(f"`gh {' '.join(argv[:3])}` failed: {detail}")
    return result.stdout


_gh = run_gh

SECRET = "SANTIAGO_CODEX_BRIDGE_TOKEN"


def setup_problem_notice(step, problem, human):
    """Comment for a harness step that could not run because of repository
    setup (a missing or refused token), not because of anything on the PR."""
    return (
        "HARNESS_SETUP_PROBLEM\n\n"
        f"- step that did not happen: {step}\n"
        f"- problem: {problem}\n"
        f"- fix: the repository secret `{SECRET}` must hold a token of `{human}` that can "
        "write Issues, Pull requests and Contents in THIS repository (Settings -> Secrets "
        "and variables -> Actions). For a repository owned by an organization, create the "
        "token with the organization as its resource owner and approve it there if asked.\n"
        "- then: re-run the failed run in the Actions tab; nothing else is needed.\n")


def report_setup_problem(repo, number, step, problem, human):
    """Print the problem and post it on the item with GITHUB_TOKEN. Never raises."""
    print(f"::error::{step}: {problem}", file=sys.stderr)
    try:
        _comment(repo, number, setup_problem_notice(step, problem, human))
    except GhError as error:
        print(f"Could not post HARNESS_SETUP_PROBLEM either: {error}", file=sys.stderr)


def _comment(repo, number, body, token=None):
    _gh(["api", "--method", "POST", f"repos/{repo}/issues/{number}/comments",
         "-f", f"body={body}"], token=token)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--number", required=True, type=int)
    parser.add_argument("--human", required=True,
                        help="the one login allowed to hand off (vars.HARNESS_HUMAN_LOGIN)")
    parser.add_argument("--label-event", action="store_true",
                        help="READY_FOR_SANTIAGO label applied to a PR: wake Codex directly")
    parser.add_argument("--check-only", metavar="HEAD_SHA",
                        help="only evaluate the comment in GITHUB_EVENT_PATH against HEAD_SHA "
                             "(treated as a PR handoff) and print '<decision>\\t<reason>'; "
                             "for repos whose own workflow does the waking")
    args = parser.parse_args(argv)

    if args.check_only:
        with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
            event = json.load(handle)
        decision, reason = evaluate(
            body=event["comment"].get("body") or "",
            author=(event["comment"].get("user") or {}).get("login", ""),
            owner=args.human,
            is_pr=True,
            current_head=args.check_only,
        )
        print(f"{decision}\t{reason}")
        return 0

    step = "posting `@codex review` to wake Santiago/Codex"
    wake_token = os.environ.get("CODEX_WAKE_TOKEN", "")
    if not wake_token:
        report_setup_problem(args.repo, args.number, step,
                             f"the secret `{SECRET}` is empty or not visible to this repository",
                             args.human)
        return 1

    def wake():
        try:
            _comment(args.repo, args.number, "@codex review", token=wake_token)
        except GhError as error:
            report_setup_problem(args.repo, args.number, step,
                                 f"GitHub refused the `{SECRET}` token: {error}", args.human)
            return False
        return True

    if args.label_event:
        if not wake():
            return 1
        print(f"Label handoff: posted @codex review on #{args.number}.")
        return 0

    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    is_pr = bool(event["issue"].get("pull_request"))
    current_head = ""
    if is_pr:
        current_head = json.loads(_gh(["api", f"repos/{args.repo}/pulls/{args.number}"]))["head"]["sha"]

    decision, reason = evaluate(
        body=event["comment"].get("body") or "",
        author=(event["comment"].get("user") or {}).get("login", ""),
        owner=args.human,
        is_pr=is_pr,
        current_head=current_head,
    )
    print(f"{decision}: {reason}")
    if decision == HANDOFF:
        if not wake():
            return 1
    elif decision == IGNORED:
        _comment(args.repo, args.number, ignored_notice(reason))
    return 0


if __name__ == "__main__":
    sys.exit(main())
