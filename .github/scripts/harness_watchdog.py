"""
Harness watchdog: find Issues/PRs where the Claude <-> Codex loop has
silently stopped, and say so once on the item with a `HARNESS_STALLED`
comment naming the stuck step and the fix.

Run by `.github/workflows/harness-watchdog.yml` every 15 minutes. See
`docs/HARNESS_TEMPLATE.md` for the loop and each stall.

Comment-only by design. It never adds or removes a label, never posts
`@codex review`, never fires the Claude Routine, and never re-runs anything
(the retired `claude-stall-watchdog.yml` did re-dispatch, which is why it was
removed -- see docs/HARNESS_GOLDEN_PATH.md). A human reads the comment and
does the one step it names. Comments are posted with the workflow's own
`GITHUB_TOKEN`, which cannot trigger another workflow, and each stall is
reported at most once per item and head commit (an HTML marker in the
comment is the dedupe key).

Stalls detected, in loop order:

1. `READY_FOR_CLAUDE_CLOUD` written as text on an Issue, never applied as a
   label (so the bridge never fired).
2. `READY_FOR_CLAUDE_CLOUD` label still present after 15 minutes (the
   bridge removes it on a successful dispatch, so it fired and failed, or
   never ran).
3. A PR head nobody has asked Codex to review (the READY_FOR_SANTIAGO
   handoff was never posted, or was rejected).
4. `@codex review` posted on the current head but Codex never answered.
5. Codex reviewed the current head but Claude was never re-dispatched.
6. Claude was dispatched for the current head but never pushed a new commit.

Only PRs that have taken part in the loop (at least one READY_FOR_SANTIAGO
line, or a Routine dispatch) are checked, and never a draft PR or a head
already marked `VERIFIED:<sha>`.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import harness_handoff  # noqa: E402

CODEX_BOT = "chatgpt-codex-connector[bot]"
CLAUDE_LABEL = "READY_FOR_CLAUDE_CLOUD"
DISPATCH_WAIT = timedelta(minutes=15)
HANDOFF_WAIT = timedelta(minutes=30)
CODEX_WAIT = timedelta(minutes=30)
CLAUDE_WAIT = timedelta(minutes=90)
MARKER = "<!-- harness-watchdog:{} -->"


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _login(item):
    return (item.get("user") or {}).get("login", "")


def _is_wake(comment):
    return (comment.get("body") or "").strip().lower().startswith("@codex review")


def _is_dispatch_for(comment, head, since):
    """A bridge dispatch comment for `head`: it names the head (newer bridges
    write `@ <sha>`), or it was posted after the Codex review at `since`
    (older bridges do not name the head)."""
    body = comment.get("body") or ""
    return (_login(comment) == "github-actions[bot]"
            and body.startswith(("ROUTINE_DISPATCHED", "ROUTINE_FIRE_FAILED"))
            and (head in body or parse_time(comment["created_at"]) >= since))


def check_issue(issue, comments, *, labeled_at, now):
    """Return `(key, message)` for a stalled Issue, or None."""
    labels = {label["name"] for label in issue.get("labels", [])}
    if CLAUDE_LABEL in labels:
        if labeled_at and now - parse_time(labeled_at) > DISPATCH_WAIT:
            return (f"label:{labeled_at}",
                    f"`{CLAUDE_LABEL}` has been on this item since {labeled_at} but the "
                    "bridge removes it on a successful dispatch, so Claude was not started. "
                    "Look for a `ROUTINE_FIRE_FAILED` comment or a failed "
                    "`Claude Cloud Routine Bridge` run. Fix: remove the label, then add it "
                    "again.")
        return None
    if "pull_request" in issue:
        return None
    texts = [issue.get("body") or ""] + [c.get("body") or "" for c in comments]
    dispatched = any((c.get("body") or "").startswith("ROUTINE_DISPATCHED") for c in comments)
    if (not dispatched
            and any(harness_handoff.has_keyword_line(t, CLAUDE_LABEL) for t in texts)
            and now - parse_time(issue["created_at"]) > DISPATCH_WAIT):
        return ("label-as-text",
                f"`{CLAUDE_LABEL}` is written as text on this Issue but was never applied "
                "as a label, so Claude was never started. Fix: apply the "
                f"`{CLAUDE_LABEL}` label to this Issue. Do not open a duplicate Issue.")
    return None


def check_pr(pr, comments, reviews, *, head_committed_at, now):
    """Return `(key, message)` for a stalled PR, or None."""
    head = pr["head"]["sha"]
    if pr.get("draft"):
        return None
    if any(f"VERIFIED:{head}" in (c.get("body") or "") for c in comments):
        return None
    in_loop = any(harness_handoff.has_keyword_line(c.get("body") or "") for c in comments) or any(
        (c.get("body") or "").startswith("ROUTINE_DISPATCHED") for c in comments)
    if not in_loop:
        return None

    head_time = parse_time(head_committed_at)
    after_head = [c for c in comments if parse_time(c["created_at"]) >= head_time]
    if any(harness_handoff.has_keyword_line(c.get("body") or "", "NEEDS_ZANETA") for c in after_head):
        return None  # already waiting on a human, loudly
    wakes = [c for c in after_head if _is_wake(c)]
    codex_reviews = [r for r in reviews if _login(r) == CODEX_BOT and r.get("commit_id") == head]
    short = head[:7]

    if codex_reviews:
        review_time = max(parse_time(r["submitted_at"]) for r in codex_reviews)
        later = [c for c in comments if parse_time(c["created_at"]) >= review_time]
        if any((c.get("body") or "").startswith("HANDOFF_IGNORED") for c in later):
            return None
        dispatches = [c for c in comments if _is_dispatch_for(c, head, review_time)]
        if not dispatches:
            if now - review_time > DISPATCH_WAIT:
                return (f"requeue:{head}",
                        f"Codex reviewed head `{short}` but Claude was never re-dispatched. "
                        "Look for a failed `Codex feedback to Claude` run. Fix: remove and "
                        f"re-add the `{CLAUDE_LABEL}` label on this PR.")
            return None
        last_dispatch = max(parse_time(c["created_at"]) for c in dispatches)
        if now - last_dispatch > CLAUDE_WAIT:
            return (f"claude:{head}",
                    f"Claude was dispatched for head `{short}` at {last_dispatch:%Y-%m-%d %H:%M} UTC "
                    "but has not pushed a new commit since. Open the session linked in the "
                    "`ROUTINE_DISPATCHED` comment above to see where it stopped.")
        return None

    if wakes:
        last_wake = max(parse_time(c["created_at"]) for c in wakes)
        answered = any(_login(c) == CODEX_BOT and parse_time(c["created_at"]) >= last_wake
                       for c in comments)
        if not answered and now - last_wake > CODEX_WAIT:
            return (f"codex:{head}",
                    f"`@codex review` was posted for head `{short}` at "
                    f"{last_wake:%Y-%m-%d %H:%M} UTC and Codex has not answered. "
                    "Fix: post `@codex review` again; if it still does not answer, check "
                    "the Codex GitHub connector.")
        return None

    if now - head_time > HANDOFF_WAIT:
        return (f"handoff:{head}",
                f"Nobody has asked Codex to review head `{short}`. The READY_FOR_SANTIAGO "
                "handoff was never posted for this commit, or was rejected (see any "
                "`HANDOFF_IGNORED` comment). Fix: post a comment whose first line is "
                f"`READY_FOR_SANTIAGO` and that contains `exact head commit SHA: {head}`.")
    return None


def stalled_notice(key, message):
    return f"HARNESS_STALLED\n\n{message}\n\n{MARKER.format(key)}\n"


# ---------------------------------------------------------------------------
# gh wiring
# ---------------------------------------------------------------------------

def _real_gh(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def _paginated(raw):
    decoder, values, index, raw = json.JSONDecoder(), [], 0, (raw or "").strip()
    while index < len(raw):
        value, index = decoder.raw_decode(raw, index)
        values.extend(value if isinstance(value, list) else [value])
        while index < len(raw) and raw[index].isspace():
            index += 1
    return values


def _get(gh, path, paginate=False):
    argv = ["gh", "api"] + (["--paginate"] if paginate else []) + [path]
    raw = gh(argv)
    return _paginated(raw) if paginate else json.loads(raw)


def sweep(repo, *, gh=_real_gh, now=None, dry_run=False):
    now = now or datetime.now(timezone.utc)
    reported = []
    for item in _get(gh, f"repos/{repo}/issues?state=open&per_page=100", paginate=True):
        number = item["number"]
        comments = _get(gh, f"repos/{repo}/issues/{number}/comments?per_page=100", paginate=True)
        labeled_at = None
        if any(label["name"] == CLAUDE_LABEL for label in item.get("labels", [])):
            events = _get(gh, f"repos/{repo}/issues/{number}/events?per_page=100", paginate=True)
            times = [e["created_at"] for e in events
                     if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == CLAUDE_LABEL]
            labeled_at = max(times) if times else None
        stall = check_issue(item, comments, labeled_at=labeled_at, now=now)
        if stall is None and "pull_request" in item:
            pr = _get(gh, f"repos/{repo}/pulls/{number}")
            reviews = _get(gh, f"repos/{repo}/pulls/{number}/reviews?per_page=100", paginate=True)
            commit = _get(gh, f"repos/{repo}/commits/{pr['head']['sha']}")
            stall = check_pr(pr, comments, reviews,
                             head_committed_at=commit["commit"]["committer"]["date"], now=now)
        if stall is None:
            continue
        key, message = stall
        if any(MARKER.format(key) in (c.get("body") or "") for c in comments):
            continue
        reported.append((number, key))
        print(f"#{number}: {key}")
        if not dry_run:
            gh(["gh", "api", "--method", "POST", f"repos/{repo}/issues/{number}/comments",
                "-f", f"body={stalled_notice(key, message)}"])
    return reported


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report stalled harness items.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    sweep(args.repo, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
