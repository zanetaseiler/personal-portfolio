"""
One Claude session per Block at a time.

Run by `.github/workflows/claude-cloud-routine-bridge.yml` (and by
`codex-feedback-to-claude.yml` before it fires Claude directly). See
`docs/HARNESS_TEMPLATE.md` for the whole loop.

Why this exists (Zoe Issue #297 / PR #298, 2026-09-25): Žaneta's
`ZANETA_DECISION` on PR #298 restarted Claude on the PR, and six seconds
earlier Santiago also put `READY_FOR_CLAUDE_CLOUD` on Issue #297. The bridge
fired both, so two Claude sessions worked on the same branch at the same
time. One did the work; the other ended silently. Two sessions pushing one
branch can also overwrite each other.

A Block is an Issue plus its open PR (the PR that says `Closes #N` or names
`#N` in its title). The rules:

1. `route`: a label on an Issue that already has an open PR is moved to
   that PR, so the Block has one place where Claude runs.
2. `check` (run inside a per-Block lock): Claude is not started while a
   session for the Block is still working -- a `ROUTINE_DISPATCHED` less
   than `LOCK_MINUTES` old with no `READY_FOR_SANTIAGO` / `NEEDS_ZANETA`
   after it, anywhere in the Block. The duplicate label is removed and,
   unless it is an obvious duplicate delivery (under two minutes), a
   `HANDOFF_IGNORED` comment says a session is already running. The lock
   ends at the same age the watchdog reports a silent session, so a stuck
   session never blocks the Block for longer than that.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_handoff  # noqa: E402

LABEL = "READY_FOR_CLAUDE_CLOUD"
BOT = "github-actions[bot]"
LOCK_MINUTES = 60
QUIET_MINUTES = 2

FREE = "free"
BUSY = "busy"


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def links_issue(pr, number):
    """True when `pr` belongs to Issue `number`: `Closes/Fixes/Resolves #N`
    in the body, or `#N` in the title. A passing mention in the body (e.g.
    "not the abandoned attempt from #289") does not link."""
    closing = rf"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+#{number}(?!\d)"
    title = rf"(?<![\w/])#{number}(?!\d)"
    return bool(re.search(closing, pr.get("body") or "")
                or re.search(title, pr.get("title") or ""))


def linked_issues(pr):
    text = f"{pr.get('title') or ''}\n{pr.get('body') or ''}"
    return sorted({int(n) for n in re.findall(r"(?<![\w/])#(\d+)", text)
                   if links_issue(pr, int(n))})


def block_pr(issue_number, open_prs):
    """The open PR of Issue `issue_number`'s Block (most recently updated), or None."""
    prs = [p for p in open_prs if p["number"] != issue_number and links_issue(p, issue_number)]
    return max(prs, key=lambda p: p.get("updated_at") or "", default=None)


def _is_dispatch(comment):
    return ((comment.get("user") or {}).get("login") == BOT
            and (comment.get("body") or "").startswith("ROUTINE_DISPATCHED"))


def _is_handoff(comment):
    body = comment.get("body") or ""
    return (harness_handoff.has_keyword_line(body, "READY_FOR_SANTIAGO")
            or harness_handoff.has_keyword_line(body, "NEEDS_ZANETA"))


def session_state(comments, *, now):
    """`(FREE, None)` or `(BUSY, dispatch_comment)` for all of a Block's comments."""
    dispatches = [c for c in comments if _is_dispatch(c)]
    if not dispatches:
        return FREE, None
    last = max(dispatches, key=lambda c: parse_time(c["created_at"]))
    at = parse_time(last["created_at"])
    if now - at >= timedelta(minutes=LOCK_MINUTES):
        return FREE, None
    if any(_is_handoff(c) and parse_time(c["created_at"]) > at for c in comments):
        return FREE, None
    return BUSY, last


def busy_notice(dispatch, *, now):
    at = parse_time(dispatch["created_at"])
    session = re.search(r"https://claude\.ai/code/\S+", dispatch.get("body") or "")
    where = session.group(0) if session else "see the ROUTINE_DISPATCHED comment"
    return harness_handoff.ignored_notice(
        f"Claude is already working on this Block (started {at:%H:%M} UTC: {where}). "
        "A second session on the same branch would collide with it.",
        effect=("No second Claude session was started; the READY_FOR_CLAUDE_CLOUD label was "
                "removed. The running session ends with READY_FOR_SANTIAGO or NEEDS_ZANETA. If "
                f"it posts neither, the watchdog reports it after {at + timedelta(minutes=LOCK_MINUTES):%H:%M} "
                "UTC, and a ZANETA_DECISION comment then restarts Claude."))


def is_quiet_duplicate(dispatch, *, now):
    return now - parse_time(dispatch["created_at"]) < timedelta(minutes=QUIET_MINUTES)


# --- GitHub plumbing -------------------------------------------------------

def _gh(argv):
    return harness_handoff.run_gh(argv)


def _get(repo, path):
    return json.loads(_gh(["api", f"repos/{repo}/{path}"]))


def _open_prs(repo):
    return _get(repo, "pulls?state=open&per_page=100")


def _comments(repo, number):
    return json.loads(_gh(["api", "--paginate", "--slurp",
                           f"repos/{repo}/issues/{number}/comments?per_page=100"]) or "[]")


def _flatten(pages):
    return [c for page in pages for c in (page if isinstance(page, list) else [page])]


def _remove_label(repo, number):
    subprocess.run(["gh", "api", "--method", "DELETE",
                    f"repos/{repo}/issues/{number}/labels/{LABEL}"],
                   capture_output=True, text=True)


def _output(**values):
    path = os.environ.get("GITHUB_OUTPUT")
    lines = "".join(f"{k}={v}\n" for k, v in values.items())
    print(lines, end="")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(lines)


def route(repo, number, kind):
    """Pick where Claude runs for this label: the Issue's open PR if it has one."""
    if kind == "issue":
        pr = block_pr(number, _open_prs(repo))
        if pr:
            # Labels added with GITHUB_TOKEN trigger nothing, so this move
            # cannot start a second bridge run by itself.
            _gh(["api", "--method", "POST", f"repos/{repo}/issues/{pr['number']}/labels",
                 "-f", f"labels[]={LABEL}"])
            _remove_label(repo, number)
            print(f"Issue #{number} has open PR #{pr['number']}: Claude runs on the PR.")
            _output(target=pr["number"], flag="--pr")
            return 0
    _output(target=number, flag=f"--{kind}")
    return 0


def check(repo, number, kind, *, notice_on=None, now=None):
    now = now or datetime.now(timezone.utc)
    items = {number}
    if kind == "pr":
        items.update(linked_issues(_get(repo, f"pulls/{number}")))
    else:
        pr = block_pr(number, _open_prs(repo))
        if pr:
            items.add(pr["number"])
    comments = [c for item in sorted(items) for c in _flatten(_comments(repo, item))]
    state, dispatch = session_state(comments, now=now)
    if state == FREE:
        _output(go="true")
        return 0
    _remove_label(repo, number)
    if not is_quiet_duplicate(dispatch, now=now):
        _gh(["api", "--method", "POST", f"repos/{repo}/issues/{notice_on or number}/comments",
             "-f", "body=" + busy_notice(dispatch, now=now)])
    print(f"Block of #{number} already has a running Claude session; not starting another.")
    _output(go="false")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="One Claude session per Block at a time.")
    parser.add_argument("mode", choices=["route", "check"])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--number", required=True, type=int)
    parser.add_argument("--kind", required=True, choices=["issue", "pr"])
    parser.add_argument("--notice-on", type=int,
                        help="item to post the 'already running' notice on (default: --number)")
    args = parser.parse_args(argv)
    if args.mode == "route":
        return route(args.repo, args.number, args.kind)
    return check(args.repo, args.number, args.kind, notice_on=args.notice_on)


if __name__ == "__main__":
    sys.exit(main())
