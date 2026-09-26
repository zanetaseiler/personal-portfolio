"""
Merge a PR automatically once Santiago/Codex has VERIFIED its exact head.

Run by `.github/workflows/codex-clean-verified.yml` right after it posts
`VERIFIED` (a comment posted with GITHUB_TOKEN triggers no other workflow,
so this cannot be a separate listener). See `docs/HARNESS_TEMPLATE.md`.

Žaneta's standing decision (2026-09-25): a VERIFIED PR is merged without
waiting for her, in every repository that runs this harness. No agent
merges; this workflow does, and only when all of these hold:

* the PR is open, not a draft, and its head is still the VERIFIED commit
  (the merge call pins that SHA, so a later push can never be merged);
* neither the title nor a label says `HOLD` (or the label `NO_AUTO_MERGE`);
* every check on the head has finished (waiting up to `WAIT_MINUTES`) and
  none failed -- except a check that is failing on the base branch too,
  which this PR did not break (Zoe's Cloudflare Workers build, for one, fails
  on every commit of `main`);
* GitHub reports no merge conflict.

Anything else leaves the PR open with an `AUTO_MERGE_SKIPPED` comment that
says why and what to do. The merge uses the owner's token, not
GITHUB_TOKEN, so workflows that run on a push to the base branch still run.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_handoff  # noqa: E402

# What the workflow's GITHUB_TOKEN needs for the calls below (branches,
# check-runs, commit status, the PR, comments); the merge itself uses
# MERGE_TOKEN. tests/.../test_harness_permissions.py checks every workflow
# running this script grants it (bonafide PR #14: a missing `checks: read`
# made the check-runs read fail with HTTP 403 and skipped the merge).
GITHUB_TOKEN_PERMISSIONS = {"contents": "read", "checks": "read", "statuses": "read",
                           "pull-requests": "read", "issues": "write"}

WAIT_MINUTES = 20
POLL_SECONDS = 30
BAD = {"failure", "timed_out", "cancelled", "action_required", "startup_failure", "stale"}
HOLD_LABELS = {"HOLD", "NO_AUTO_MERGE"}

MERGE = "merge"
SKIP = "skip"
WAIT = "wait"


def hold_reason(pr):
    if re.search(r"\bHOLD\b", pr.get("title") or ""):
        return "the PR title says HOLD"
    labels = {label["name"] for label in pr.get("labels", [])}
    if labels & HOLD_LABELS:
        return f"the PR has the label {sorted(labels & HOLD_LABELS)[0]}"
    return None


def check_failures(runs, statuses):
    """`(failed_names, pending_names)` for one commit's check runs and statuses."""
    failed, pending = set(), set()
    for run in runs:
        if run.get("status") != "completed":
            pending.add(run["name"])
        elif run.get("conclusion") in BAD:
            failed.add(run["name"])
    for status in statuses:
        if status.get("state") == "pending":
            pending.add(status["context"])
        elif status.get("state") in {"failure", "error"}:
            failed.add(status["context"])
    return failed, pending


def decide(pr, *, verified_head, head_checks, base_failed):
    """`(MERGE | SKIP | WAIT, reason, ignored_failures)` for one PR."""
    head = pr["head"]["sha"].lower()
    if pr.get("state") != "open" or pr.get("merged"):
        return SKIP, "the PR is no longer open", set()
    if head != verified_head.lower():
        return SKIP, (f"a commit was pushed after VERIFIED (`{verified_head[:7]}` -> "
                      f"`{head[:7]}`); the new head needs its own review"), set()
    if pr.get("draft"):
        return SKIP, "the PR is a draft", set()
    held = hold_reason(pr)
    if held:
        return SKIP, held, set()
    failed, pending = head_checks
    if pending:
        return WAIT, f"checks still running: {', '.join(sorted(pending))}", set()
    new = failed - base_failed
    if new:
        return SKIP, (f"checks failed on this head: {', '.join(sorted(new))} "
                      "(they pass on the base branch, so this PR broke them)"), set()
    if pr.get("mergeable") is False or pr.get("mergeable_state") == "dirty":
        return SKIP, "the PR has a merge conflict with its base branch", set()
    return MERGE, "", failed & base_failed


def skipped_notice(reason, head):
    return (
        "AUTO_MERGE_SKIPPED\n\n"
        f"- exact head commit SHA: `{head}`\n"
        f"- reason: {reason}\n"
        "- effect: the PR stays open and VERIFIED; nothing was merged.\n"
        "- to merge: fix the reason and merge it yourself, or post `@codex review` after a "
        "new push to get a fresh VERIFIED.\n")


def merged_notice(head, merge_sha, ignored):
    lines = ["MERGED", "",
             f"- exact head commit SHA: `{head}`",
             f"- merge commit: `{merge_sha}`",
             "- merged automatically after VERIFIED (Žaneta's standing auto-merge decision)"]
    if ignored:
        lines.append(f"- ignored checks that also fail on the base branch: {', '.join(sorted(ignored))}")
    return "\n".join(lines) + "\n"


# --- GitHub plumbing -------------------------------------------------------

def _gh(argv, token=None):
    return harness_handoff.run_gh(argv, token=token)


def _get(repo, path):
    return json.loads(_gh(["api", f"repos/{repo}/{path}"]))


def _checks(repo, sha):
    runs = _get(repo, f"commits/{sha}/check-runs?per_page=100").get("check_runs", [])
    statuses = _get(repo, f"commits/{sha}/status").get("statuses", [])
    return check_failures(runs, statuses)


def _comment(repo, number, body):
    _gh(["api", "--method", "POST", f"repos/{repo}/issues/{number}/comments", "-f", f"body={body}"])


def run(repo, number, verified_head, *, sleep=time.sleep, now=time.monotonic):
    merge_token = os.environ.get("MERGE_TOKEN", "")
    deadline = now() + WAIT_MINUTES * 60
    while True:
        pr = _get(repo, f"pulls/{number}")
        if pr.get("mergeable") is None and now() < deadline:
            sleep(5)  # GitHub computes mergeability lazily after the first read
            pr = _get(repo, f"pulls/{number}")
        base_sha = _get(repo, f"branches/{pr['base']['ref']}")["commit"]["sha"]
        base_failed, _ = _checks(repo, base_sha)
        decision, reason, ignored = decide(pr, verified_head=verified_head,
                                           head_checks=_checks(repo, verified_head),
                                           base_failed=base_failed)
        if decision != WAIT or now() >= deadline:
            break
        print(f"Waiting: {reason}")
        sleep(POLL_SECONDS)

    if decision == WAIT:
        decision, reason = SKIP, f"{reason} after {WAIT_MINUTES} minutes"
    if decision == SKIP:
        print(f"Not merging: {reason}")
        if "no longer open" not in reason:
            _comment(repo, number, skipped_notice(reason, verified_head))
        return 0
    if not merge_token:
        _comment(repo, number, skipped_notice(
            "the SANTIAGO_CODEX_BRIDGE_TOKEN secret is not configured, so the harness cannot "
            "merge as the repository owner", verified_head))
        return 1
    result = json.loads(_gh(["api", "--method", "PUT", f"repos/{repo}/pulls/{number}/merge",
                             "-f", f"sha={verified_head}", "-f", "merge_method=merge"],
                            token=merge_token))
    _comment(repo, number, merged_notice(verified_head, result.get("sha", "?"), ignored))
    print(f"Merged PR #{number} at {verified_head}.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Merge a VERIFIED PR automatically.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--number", required=True, type=int)
    parser.add_argument("--head", required=True, help="the exact head SHA that was VERIFIED")
    args = parser.parse_args(argv)
    try:
        return run(args.repo, args.number, args.head)
    except harness_handoff.GhError as error:
        print(f"::error::{error}", file=sys.stderr)
        _comment(args.repo, args.number, skipped_notice(
            f"GitHub refused a step of the merge: {error}. If it names the token, the "
            f"repository secret `{harness_handoff.SECRET}` must be able to write Contents and "
            "Pull requests in this repository", args.head))
        return 1


if __name__ == "__main__":
    sys.exit(main())
