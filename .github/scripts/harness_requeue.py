"""
Start or restart Claude without anyone touching a label.

Run by `.github/workflows/harness-requeue.yml`. See `docs/HARNESS_TEMPLATE.md`.

Two events used to leave work sitting forever (Zoe #287, Zoe #290,
2026-09-25):

* A task Issue opened without the `READY_FOR_CLAUDE_CLOUD` label. The bridge
  only fires on that label, so the Issue was never picked up.
* Žaneta answering a `NEEDS_ZANETA` with a `ZANETA_DECISION` comment. No
  workflow listened for it, so Claude never resumed.

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

CLAUDE_LABEL = "READY_FOR_CLAUDE_CLOUD"
DECISION = "ZANETA_DECISION"
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


def evaluate_comment(comment, *, human):
    """Return `(decision, reason)` for a new comment."""
    body = comment.get("body") or ""
    if not harness_handoff.has_keyword_line(body, DECISION):
        return SKIP, "no ZANETA_DECISION line"
    author = (comment.get("user") or {}).get("login", "")
    if author != human:
        return IGNORED, (f"ZANETA_DECISION was posted by `{author}`, not the authorized human "
                         f"`{human}`, so Claude was not restarted.")
    return START, "decision recorded; restarting Claude"


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _gh(argv, token=None):
    env = dict(os.environ)
    if token:
        env["GH_TOKEN"] = token
    return subprocess.run(["gh", *argv], check=True, capture_output=True,
                          text=True, env=env).stdout


def requeue(repo, number, token):
    """Remove then re-add the label with a real user's token, so the bridge's
    `labeled` trigger fires even if a stale label was already present."""
    subprocess.run(["gh", "api", "--method", "DELETE",
                    f"repos/{repo}/issues/{number}/labels/{CLAUDE_LABEL}"],
                   capture_output=True, text=True, env={**os.environ, "GH_TOKEN": token})
    _gh(["api", "--method", "POST", f"repos/{repo}/issues/{number}/labels",
         "-f", f"labels[]={CLAUDE_LABEL}"], token=token)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start or restart Claude without a manual label.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--human", required=True)
    args = parser.parse_args(argv)

    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    number = event["issue"]["number"]

    if "comment" in event:
        decision, reason = evaluate_comment(event["comment"], human=args.human)
    else:
        open_issues = json.loads(_gh(["api", f"repos/{args.repo}/issues?state=open&per_page=100"]))
        decision, reason = evaluate_opened(event["issue"], human=args.human, open_issues=open_issues)

    print(f"{decision}: {reason}")
    if decision == IGNORED:
        _gh(["api", "--method", "POST", f"repos/{args.repo}/issues/{number}/comments",
             "-f", "body=" + harness_handoff.ignored_notice(
                 reason, effect="Claude was NOT started or restarted by this.")])
    elif decision == START:
        token = os.environ.get("HUMAN_TOKEN", "")
        if not token:
            print("SANTIAGO_CODEX_BRIDGE_TOKEN is not configured", file=sys.stderr)
            return 1
        requeue(args.repo, number, token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
