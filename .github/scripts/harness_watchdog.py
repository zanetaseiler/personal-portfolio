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

1. A task Issue (see `harness_requeue.is_claude_task`) that Claude never
   picked up.
2. `READY_FOR_CLAUDE_CLOUD` label still present after 15 minutes (the
   bridge removes it on a successful dispatch, so it fired and failed, or
   never ran).
3. A `ZANETA_DECISION` that did not restart Claude.
4. A Claude session that ended without posting `READY_FOR_SANTIAGO` or
   `NEEDS_ZANETA` -- on the item itself or, for an Issue, on an open PR that
   references it (Zoe #289 / #294, 2026-09-25: sessions went idle with
   nothing on GitHub).
5. A PR head nobody has asked Codex to review (the READY_FOR_SANTIAGO
   handoff was never posted, or was rejected).
6. `@codex review` posted on the current head but Codex never answered.
7. Codex reviewed the current head but Claude was never re-dispatched.

Only activity from the last 7 days is considered, so old history is never
re-reported. PR checks skip drafts and heads already marked
`VERIFIED:<sha>`.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import harness_handoff  # noqa: E402
import harness_requeue  # noqa: E402

# What the workflow's GITHUB_TOKEN needs for this script's API calls;
# test_harness_permissions.py checks every workflow running it grants it.
GITHUB_TOKEN_PERMISSIONS = {"contents": "read", "pull-requests": "read", "issues": "write"}

CODEX_BOT = "chatgpt-codex-connector[bot]"
CLAUDE_LABEL = "READY_FOR_CLAUDE_CLOUD"
DISPATCH_WAIT = timedelta(minutes=15)
HANDOFF_WAIT = timedelta(minutes=30)
CODEX_WAIT = timedelta(minutes=30)
SESSION_WAIT = timedelta(minutes=60)
RECEIPT_WAIT = timedelta(minutes=15)
RECENT = timedelta(days=7)
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


def _keyword(comment, keyword):
    return harness_handoff.has_keyword_line(comment.get("body") or "", keyword)


def _bridge(comment, prefix="ROUTINE_"):
    return (_login(comment) == "github-actions[bot]"
            and (comment.get("body") or "").startswith(prefix))


def _handed_off(comment):
    return _keyword(comment, "READY_FOR_SANTIAGO") or _keyword(comment, "NEEDS_ZANETA")


def check_issue(issue, comments, *, labeled_at, linked_prs, now):
    """Return `(key, message)` for a stalled Issue (or PR queue label), or None."""
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
    created = parse_time(issue["created_at"])
    if (harness_requeue.is_claude_task(issue.get("title"), issue.get("body"))
            and not any(_bridge(c) for c in comments)
            and not linked_prs
            and DISPATCH_WAIT < now - created < RECENT):
        return ("not-started",
                "This task Issue was never picked up by Claude (no `ROUTINE_DISPATCHED`). "
                "Look for a failed `Harness requeue` run. Fix: apply the "
                f"`{CLAUDE_LABEL}` label to this Issue. Do not open a duplicate Issue.")
    return None


def check_session(comments, *, linked_comments, now):
    """Return `(key, message)` when Claude should be working but is not."""
    decisions = [c for c in comments if _keyword(c, harness_requeue.DECISION)]
    if decisions:
        decision = max(decisions, key=lambda c: c["created_at"])
        at = parse_time(decision["created_at"])
        later = [c for c in comments + linked_comments if parse_time(c["created_at"]) > at]
        if (not any(_bridge(c) or _handed_off(c) for c in later)
                and DISPATCH_WAIT < now - at < RECENT):
            return (f"decision:{decision['id']}",
                    f"A `ZANETA_DECISION` was posted at {at:%Y-%m-%d %H:%M} UTC but Claude was "
                    "not restarted. Look for a failed `Harness requeue` run. Fix: apply the "
                    f"`{CLAUDE_LABEL}` label here.")
    dispatches = [c for c in comments if _bridge(c, "ROUTINE_DISPATCHED")]
    if not dispatches:
        return None
    dispatch = max(dispatches, key=lambda c: c["created_at"])
    at = parse_time(dispatch["created_at"])
    later = [c for c in comments + linked_comments if parse_time(c["created_at"]) >= at]
    if any(_handed_off(c) for c in later) or now - at >= RECENT:
        return None
    session = re.search(r"https://claude\.ai/code/\S+", dispatch.get("body") or "")
    where = session.group(0) if session else "the session linked above"
    # A working session posts CONTEXT_RECEIPT within minutes. None after
    # RECEIPT_WAIT means it ended at once -- e.g. trafficdom PR #221
    # (2026-09-26): the session lost GitHub access, stopped after 60 seconds,
    # and could not report that on GitHub itself. Same key as the 60-minute
    # check below, so one silent session is reported once.
    if (not any(_keyword(c, "CONTEXT_RECEIPT") for c in later)
            and RECEIPT_WAIT < now - at):
        return (f"session:{dispatch['id']}",
                f"Claude was started at {at:%Y-%m-%d %H:%M} UTC but has not posted "
                f"`CONTEXT_RECEIPT` within {RECEIPT_WAIT.seconds // 60} minutes, so the session "
                f"most likely ended at once. Open {where} to read its last message (if it says "
                "it could not reach GitHub, check the Claude GitHub App/connector's access to "
                "this repository). Fix: reply with a `ZANETA_DECISION` comment to restart Claude.")
    if not SESSION_WAIT < now - at:
        return None
    return (f"session:{dispatch['id']}",
            f"Claude was started at {at:%Y-%m-%d %H:%M} UTC but has posted neither "
            "`READY_FOR_SANTIAGO` nor `NEEDS_ZANETA` since, so the session most likely ended "
            f"without handing off. Open {where} to read its last message. Fix: reply with a "
            "`ZANETA_DECISION` comment saying how to continue (that restarts Claude).")


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
        return None  # a dispatched-but-silent session is check_session's job

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


def _references(pr, number):
    return re.search(rf"(?<![\w/])#{number}(?!\d)", pr.get("body") or "") is not None


def sweep(repo, *, gh=_real_gh, now=None, dry_run=False):
    now = now or datetime.now(timezone.utc)
    items = _get(gh, f"repos/{repo}/issues?state=open&per_page=100", paginate=True)
    comments = {item["number"]: _get(gh, f"repos/{repo}/issues/{item['number']}/comments?per_page=100",
                                     paginate=True)
                for item in items}
    prs = [item for item in items if "pull_request" in item]
    reported = []
    for item in items:
        number = item["number"]
        linked = [pr for pr in prs if pr["number"] != number and _references(pr, number)]
        linked_comments = [c for pr in linked for c in comments[pr["number"]]]
        labeled_at = None
        if any(label["name"] == CLAUDE_LABEL for label in item.get("labels", [])):
            events = _get(gh, f"repos/{repo}/issues/{number}/events?per_page=100", paginate=True)
            times = [e["created_at"] for e in events
                     if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == CLAUDE_LABEL]
            labeled_at = max(times) if times else None
        stall = (check_issue(item, comments[number], labeled_at=labeled_at, linked_prs=linked, now=now)
                 or check_session(comments[number], linked_comments=linked_comments, now=now))
        if stall is None and "pull_request" in item:
            pr = _get(gh, f"repos/{repo}/pulls/{number}")
            reviews = _get(gh, f"repos/{repo}/pulls/{number}/reviews?per_page=100", paginate=True)
            commit = _get(gh, f"repos/{repo}/commits/{pr['head']['sha']}")
            stall = check_pr(pr, comments[number], reviews,
                             head_committed_at=commit["commit"]["committer"]["date"], now=now)
        if stall is None:
            continue
        key, message = stall
        if any(MARKER.format(key) in (c.get("body") or "") for c in comments[number]):
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
