"""
Start or restart Claude without anyone touching a label.

Run by `.github/workflows/harness-requeue.yml`. See `docs/HARNESS_TEMPLATE.md`.

Events that used to leave work sitting forever (Zoe #287, Zoe #290,
2026-09-25; trafficdom #221, 2026-09-26):

* A task Issue opened without the `READY_FOR_CLAUDE_CLOUD` label. The bridge
  only fires on that label, so the Issue was never picked up.
* Žaneta answering a `NEEDS_ZANETA` with a `ZANETA_DECISION` comment. No
  workflow listened for it, so Claude never resumed.
* Santiago's `CHANGES_REQUESTED` review on a PR (with `--changes-requested`).

This script handles both by (re-)applying the label with the owner's token
(`HUMAN_TOKEN`, the same `SANTIAGO_CODEX_BRIDGE_TOKEN` used to wake Codex). A
label applied with a real user's token fires the existing
`claude-cloud-routine-bridge.yml` `labeled` trigger exactly as if a human had
clicked it, so the bridge's own claim/idempotency rules still decide whether
a session actually starts. Nothing here calls the Routine directly.

Rules:

* `ZANETA_DECISION` counts only on a standalone line, only from the
  authorized human (`--human`). Anyone else gets a `HANDOFF_IGNORED` reply.
* A new Issue is a Claude task when its body names the protocol (a
  `Mandatory workflow` line, or `CONTEXT_RECEIPT` / `READY_FOR_SANTIAGO` /
  `READY_FOR_CLAUDE_CLOUD`). `HOLD` in the title opts out. An Issue opened
  with the label already on it is left to the bridge.
* Duplicate guard: a new task Issue whose title matches another open Issue
  opened in the previous 30 minutes is not started; it gets a
  `HANDOFF_IGNORED` naming the original.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import harness_handoff  # noqa: E402

# What the workflow's GITHUB_TOKEN needs for this script's API calls;
# test_harness_permissions.py checks every workflow running it grants it.
GITHUB_TOKEN_PERMISSIONS = {"pull-requests": "read", "issues": "write"}

CLAUDE_LABEL = "READY_FOR_CLAUDE_CLOUD"
DECISION = "ZANETA_DECISION"
CHANGES = "CHANGES_REQUESTED"
CLAUDE_KEYWORDS = ("READY_FOR_SANTIAGO", "CONTEXT_RECEIPT", "NEEDS_ZANETA")
DUPLICATE_WINDOW = timedelta(minutes=30)
_TASK_MARKER = re.compile(
    r"Mandatory workflow|CONTEXT_RECEIPT|READY_FOR_SANTIAGO|READY_FOR_CLAUDE_CLOUD")

START = "start"
SKIP = "skip"
IGNORED = "ignored"


def is_claude_task(title, body):
    """A new Issue meant for Claude: it names the protocol and is not held."""
    if re.search(r"\bHOLD\b", title or ""):
        return False
    return bool(_TASK_MARKER.search(body or ""))


def _norm_title(title):
    return re.sub(r"\W+", " ", (title or "").lower()).strip()


def evaluate_opened(issue, *, human, open_issues):
    """Return `(decision, reason)` for a newly opened Issue."""
    if (issue.get("user") or {}).get("login") != human:
        return SKIP, "not opened by the authorized human"
    if "pull_request" in issue:
        return SKIP, "pull request"
    if any(label.get("name") == CLAUDE_LABEL for label in issue.get("labels", [])):
        return SKIP, "label already applied; the bridge handles it"
    if not is_claude_task(issue.get("title"), issue.get("body")):
        return SKIP, "not a Claude task (no protocol marker, or HOLD in the title)"
    opened = _time(issue["created_at"])
    for other in open_issues:
        if (other["number"] != issue["number"] and "pull_request" not in other
                and _norm_title(other.get("title")) == _norm_title(issue.get("title"))
                and timedelta(0) <= opened - _time(other["created_at"]) <= DUPLICATE_WINDOW):
            return IGNORED, (f"this Issue duplicates #{other['number']} (same title, opened "
                             f"{opened - _time(other['created_at'])} earlier), so Claude was not "
                             f"started twice. Work continues on #{other['number']}; close this one.")
    return START, "new Claude task"


def evaluate_comment(comment, *, human, is_pr=False, current_head="", changes_requested=False):
    """Return `(decision, reason)` for a new comment.

    `ZANETA_DECISION` restarts Claude on the Issue or PR it is posted on.
    With `changes_requested`, Santiago's `CHANGES_REQUESTED` review on a PR
    does too, when it names the PR's current head (trafficdom PR #221,
    2026-09-26: the old requeue workflow wanted the bare keyword as the whole
    first line and labeled with GITHUB_TOKEN, so a correct review
    `CHANGES_REQUESTED — Santiago exact-SHA review of <sha>` never restarted
    Claude and said nothing)."""
    body = comment.get("body") or ""
    author = (comment.get("user") or {}).get("login", "")
    # Claude's own comments are posted under the same login; one that quotes
    # a decision or review must never restart Claude (a loop right after its
    # own handoff).
    if any(harness_handoff.has_keyword_line(body, word) for word in CLAUDE_KEYWORDS):
        return SKIP, "a Claude handoff/receipt, not a decision or review"
    if harness_handoff.has_keyword_line(body, DECISION):
        if author != human:
            return IGNORED, (f"ZANETA_DECISION was posted by `{author}`, not the authorized human "
                             f"`{human}`, so Claude was not restarted.")
        return START, "decision recorded; restarting Claude"
    first_line = next((line for line in body.splitlines() if line.strip()), "")
    if not (changes_requested and harness_handoff.has_keyword_line(first_line, CHANGES)):
        return SKIP, "no ZANETA_DECISION or CHANGES_REQUESTED line"
    if author != human:
        return IGNORED, (f"CHANGES_REQUESTED was posted by `{author}`, not the authorized human "
                         f"`{human}`, so Claude was not restarted.")
    if not is_pr:
        return IGNORED, ("CHANGES_REQUESTED was posted on an Issue. Post the review on the "
                         "Block's PR, naming the PR's current head commit.")
    head = (current_head or "").lower()
    if not any(head.startswith(token[:7]) for token in harness_handoff.sha_tokens(body)):
        return IGNORED, (f"this CHANGES_REQUESTED does not name the PR's current head `{head}` "
                         "(a commit was probably pushed after the review), so Claude was not "
                         "restarted. Review the current head and post the review again with it.")
    return START, "changes requested on the current head; restarting Claude"


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


_gh = harness_handoff.run_gh


def requeue(repo, number, token):
    """Remove then re-add the label with a real user's token, so the bridge's
    `labeled` trigger fires even if a stale label was already present."""
    subprocess.run(["gh", "api", "--method", "DELETE",
                    f"repos/{repo}/issues/{number}/labels/{CLAUDE_LABEL}"],
                   capture_output=True, text=True, env={**os.environ, "GH_TOKEN": token})
    _gh(["api", "--method", "POST", f"repos/{repo}/issues/{number}/labels",
         "-f", f"labels[]={CLAUDE_LABEL}"], token=token)


def queue_pr_for_direct_start(repo, number):
    """For a restart on a PR: apply the label with GITHUB_TOKEN (which starts
    no workflow) and hand the PR number to the workflow's next steps, which
    run the one-session guard and the bridge in this same run.

    Why not the owner-token label as for an Issue: GitHub runs no
    `pull_request` workflow on a PR with a merge conflict, so the bridge's
    `labeled` trigger never fires there -- and updating a conflicted branch is
    exactly what the restart is for (trafficdom #221 and #228, 2026-09-26).
    This run was started by the comment itself, which a conflict never blocks."""
    _gh(["api", "--method", "POST", f"repos/{repo}/issues/{number}/labels",
         "-f", f"labels[]={CLAUDE_LABEL}"])
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"start_pr={number}\n")
    print(f"PR #{number}: label applied; the workflow starts Claude directly.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start or restart Claude without a manual label.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--human", required=True)
    parser.add_argument("--changes-requested", action="store_true",
                        help="also restart Claude on Santiago's CHANGES_REQUESTED review of a PR")
    args = parser.parse_args(argv)

    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    number = event["issue"]["number"]

    if "comment" in event:
        is_pr = bool(event["issue"].get("pull_request"))
        head = ""
        if is_pr and args.changes_requested:
            head = json.loads(_gh(["api", f"repos/{args.repo}/pulls/{number}"]))["head"]["sha"]
        decision, reason = evaluate_comment(event["comment"], human=args.human, is_pr=is_pr,
                                            current_head=head,
                                            changes_requested=args.changes_requested)
    else:
        open_issues = json.loads(_gh(["api", f"repos/{args.repo}/issues?state=open&per_page=100"]))
        # Re-read the Issue: Santiago often adds the label seconds after
        # opening it, and re-adding it here would start the bridge twice.
        current = json.loads(_gh(["api", f"repos/{args.repo}/issues/{number}"]))
        decision, reason = evaluate_opened(current, human=args.human, open_issues=open_issues)

    print(f"{decision}: {reason}")
    if decision == IGNORED:
        _gh(["api", "--method", "POST", f"repos/{args.repo}/issues/{number}/comments",
             "-f", "body=" + harness_handoff.ignored_notice(
                 reason, effect="Claude was NOT started or restarted by this.")])
    elif decision == START and event["issue"].get("pull_request"):
        queue_pr_for_direct_start(args.repo, number)
    elif decision == START:
        step = "starting Claude (adding READY_FOR_CLAUDE_CLOUD as the owner)"
        token = os.environ.get("HUMAN_TOKEN", "")
        if not token:
            harness_handoff.report_setup_problem(
                args.repo, number, step,
                f"the secret `{harness_handoff.SECRET}` is empty or not visible to this repository",
                args.human)
            return 1
        try:
            requeue(args.repo, number, token)
        except harness_handoff.GhError as error:
            harness_handoff.report_setup_problem(
                args.repo, number, step,
                f"GitHub refused the `{harness_handoff.SECRET}` token: {error}", args.human)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
