"""
Offline coverage for .github/scripts/harness_watchdog.py and
.github/workflows/harness-watchdog.yml. Every test uses a fake `gh`; no
subprocess runs and nothing is written to GitHub.
"""

import importlib.util
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

def _repo_root():
    """The repository root: the nearest parent directory holding `.github`
    (this file lives in a different tests/ subfolder in different repos)."""
    here = Path(__file__).resolve()
    return next(p for p in here.parents if (p / ".github").is_dir())


REPO_ROOT = _repo_root()
SCRIPTS = REPO_ROOT / ".github" / "scripts"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "harness-watchdog.yml"

sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("harness_watchdog", SCRIPTS / "harness_watchdog.py")
watchdog = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = watchdog
_spec.loader.exec_module(watchdog)

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
HEAD = "1a1afcc5b4b3f15b5284f78c8699f9f3e21179a5"
OWNER = "zanetaseiler"
CODEX = "chatgpt-codex-connector[bot]"
ACTIONS = "github-actions[bot]"


def comment(body, at, user=OWNER):
    return {"body": body, "created_at": at, "user": {"login": user}}


def pr(head=HEAD, draft=False):
    return {"number": 206, "head": {"sha": head}, "draft": draft}


def review(at, commit=HEAD, user=CODEX):
    return {"submitted_at": at, "commit_id": commit, "user": {"login": user}}


READY = f"READY_FOR_SANTIAGO\n- exact head commit SHA: `{HEAD}`"


class TestIssueChecks(unittest.TestCase):

    TASK = "Do X.\n\n## Protocol\n\nMandatory workflow: CONTEXT_RECEIPT -> PR -> READY_FOR_SANTIAGO"

    def issue(self, labels=(), body="", created="2026-09-25T10:00:00Z", title="Task"):
        return {"number": 287, "labels": [{"name": n} for n in labels], "body": body,
                "created_at": created, "title": title}

    def check(self, issue, comments=(), labeled_at=None, linked_prs=()):
        return watchdog.check_issue(issue, list(comments), labeled_at=labeled_at,
                                    linked_prs=list(linked_prs), now=NOW)

    def test_zoe_287_task_issue_never_started_is_reported(self):
        # Real Zoe #287: task Issue opened without the label, no comments, never picked up.
        self.assertEqual(self.check(self.issue(body=self.TASK))[0], "not-started")

    def test_started_task_or_one_with_a_pr_is_fine(self):
        dispatched = [comment("ROUTINE_DISPATCHED\n", "2026-09-25T10:01:00Z", ACTIONS)]
        self.assertIsNone(self.check(self.issue(body=self.TASK), dispatched))
        self.assertIsNone(self.check(self.issue(body=self.TASK), linked_prs=[{"number": 290}]))

    def test_held_old_or_non_task_issues_are_not_reported(self):
        self.assertIsNone(self.check(self.issue(body=self.TASK, title="HOLD: later")))
        self.assertIsNone(self.check(self.issue(body=self.TASK, created="2026-09-01T10:00:00Z")))
        self.assertIsNone(self.check(self.issue(body="just notes")))

    def test_label_still_present_after_the_wait_is_reported(self):
        stall = self.check(self.issue(labels=["READY_FOR_CLAUDE_CLOUD"]),
                           labeled_at="2026-09-25T11:00:00Z")
        self.assertTrue(stall[0].startswith("label:"))

    def test_fresh_label_is_not_reported(self):
        self.assertIsNone(self.check(self.issue(labels=["READY_FOR_CLAUDE_CLOUD"]),
                                     labeled_at="2026-09-25T11:55:00Z"))


class TestSessionChecks(unittest.TestCase):

    def dispatch(self, at, cid=1):
        c = comment("ROUTINE_DISPATCHED\n- session url: https://claude.ai/code/cse_01TKBStW\n", at, ACTIONS)
        c["id"] = cid
        return c

    def check(self, comments, linked=()):
        return watchdog.check_session(list(comments), linked_comments=list(linked), now=NOW)

    def test_zoe_289_session_that_ended_silently_is_reported(self):
        # Real Zoe #289: dispatched 07:42, session idle 07:43, nothing posted anywhere.
        stall = self.check([self.dispatch("2026-09-25T10:42:00Z")])
        self.assertEqual(stall[0], "session:1")
        self.assertIn("https://claude.ai/code/cse_01TKBStW", stall[1])

    def test_handoff_on_the_linked_pr_counts(self):
        linked = [comment(READY, "2026-09-25T11:00:00Z")]
        self.assertIsNone(self.check([self.dispatch("2026-09-25T10:42:00Z")], linked))

    def test_needs_zaneta_counts_as_a_handoff(self):
        comments = [self.dispatch("2026-09-25T10:42:00Z"),
                    comment("NEEDS_ZANETA\n- question", "2026-09-25T10:50:00Z")]
        self.assertIsNone(self.check(comments))

    def receipt(self, at):
        return comment("CONTEXT_RECEIPT\n- current base-branch commit SHA: x", at)

    def test_session_still_running_is_not_reported(self):
        self.assertIsNone(self.check([self.dispatch("2026-09-25T11:30:00Z"),
                                      self.receipt("2026-09-25T11:33:00Z")]))
        self.assertIsNone(self.check([self.dispatch("2026-09-25T11:50:00Z")]))

    def test_trafficdom_221_session_that_never_posted_a_receipt_is_reported_early(self):
        # Real trafficdom PR #221: dispatched 08:04, session lost GitHub access
        # and stopped at 08:05 without posting anything.
        stall = self.check([self.dispatch("2026-09-25T11:44:00Z")])
        self.assertEqual(stall[0], "session:1")
        self.assertIn("CONTEXT_RECEIPT", stall[1])
        self.assertIn("GitHub App", stall[1])

    def test_receipt_on_the_linked_pr_counts(self):
        linked = [self.receipt("2026-09-25T11:33:00Z")]
        self.assertIsNone(self.check([self.dispatch("2026-09-25T11:30:00Z")], linked))

    def test_receipt_then_silence_is_still_reported_after_an_hour(self):
        stall = self.check([self.dispatch("2026-09-25T10:42:00Z"),
                            self.receipt("2026-09-25T10:45:00Z")])
        self.assertEqual(stall[0], "session:1")
        self.assertIn("neither", stall[1])

    def test_zoe_290_decision_that_did_not_restart_claude_is_reported(self):
        # Real Zoe #290: ZANETA_DECISION posted 07:50, nothing started.
        decision = comment("ZANETA_DECISION -- 2026-09-25\n\nKeep the earlier decisions.",
                           "2026-09-25T11:30:00Z")
        decision["id"] = 9
        decision["body"] = "ZANETA_DECISION\n\nKeep the earlier decisions."
        self.assertEqual(self.check([decision])[0], "decision:9")

    def test_decision_followed_by_a_dispatch_is_fine(self):
        decision = comment("ZANETA_DECISION\n\nGo.", "2026-09-25T11:30:00Z")
        decision["id"] = 9
        self.assertIsNone(self.check([decision, self.dispatch("2026-09-25T11:30:30Z", 2),
                                      self.receipt("2026-09-25T11:33:00Z")]))


class TestPrChecks(unittest.TestCase):

    def check(self, comments, reviews=(), head_at="2026-09-24T20:30:00Z", **kw):
        return watchdog.check_pr(pr(**kw), comments, list(reviews), head_committed_at=head_at, now=NOW)

    def test_pr_206_dropped_handoff_is_reported(self):
        # Real PR #206 state: correction handoff posted, never turned into @codex review.
        comments = [comment("CONTEXT_RECEIPT\n...\n\n" + READY, "2026-09-24T20:30:58Z")]
        self.assertEqual(self.check(comments)[0], f"handoff:{HEAD}")

    def test_unanswered_codex_request_is_reported(self):
        comments = [comment(READY, "2026-09-24T20:31:00Z"),
                    comment("@codex review", "2026-09-24T20:31:10Z")]
        self.assertEqual(self.check(comments)[0], f"codex:{HEAD}")

    def test_codex_review_not_requeued_is_reported(self):
        comments = [comment(READY, "2026-09-24T20:31:00Z"),
                    comment("@codex review", "2026-09-24T20:31:10Z")]
        stall = self.check(comments, [review("2026-09-24T20:40:00Z")])
        self.assertEqual(stall[0], f"requeue:{HEAD}")

    def test_older_bridge_dispatch_without_a_sha_counts_by_time(self):
        comments = [comment(READY, "2026-09-25T11:00:00Z"),
                    comment("ROUTINE_DISPATCHED\n- item: Pull Request #206\n",
                            "2026-09-25T11:30:00Z", ACTIONS)]
        self.assertIsNone(self.check(comments, [review("2026-09-25T11:29:00Z")],
                                     head_at="2026-09-25T10:50:00Z"))

    def test_recent_dispatch_is_not_reported(self):
        comments = [comment(READY, "2026-09-25T11:00:00Z"),
                    comment(f"ROUTINE_DISPATCHED\n- dispatch round: 0 @ {HEAD}\n",
                            "2026-09-25T11:30:00Z", ACTIONS)]
        self.assertIsNone(self.check(comments, [review("2026-09-25T11:29:00Z")],
                                     head_at="2026-09-25T10:50:00Z"))

    def test_verified_head_is_not_reported(self):
        comments = [comment(READY, "2026-09-24T20:31:00Z"),
                    comment(f"VERIFIED\n- marker: VERIFIED:{HEAD}", "2026-09-24T20:50:00Z", ACTIONS)]
        self.assertIsNone(self.check(comments))

    def test_needs_zaneta_is_not_reported(self):
        comments = [comment(READY, "2026-09-24T20:31:00Z"),
                    comment("NEEDS_ZANETA\n- question", "2026-09-24T20:50:00Z")]
        self.assertIsNone(self.check(comments))

    def test_pr_outside_the_loop_or_draft_is_not_reported(self):
        self.assertIsNone(self.check([comment("hello", "2026-09-24T20:31:00Z")]))
        self.assertIsNone(self.check([comment(READY, "2026-09-24T20:31:00Z")], draft=True))

    def test_fresh_head_is_not_reported(self):
        self.assertIsNone(self.check([comment(READY, "2026-09-25T11:50:00Z")],
                                     head_at="2026-09-25T11:45:00Z"))


class TestSweep(unittest.TestCase):

    def fake_gh(self, calls, existing_comments):
        issue = {"number": 206, "labels": [], "pull_request": {}, "body": "",
                 "created_at": "2026-09-24T20:11:00Z"}

        def gh(argv):
            calls.append(argv)
            path = argv[-1] if "--method" not in argv else None
            if path is None:
                return "{}"
            if "issues?state=open" in path:
                return json.dumps([issue])
            if path.endswith("/comments?per_page=100"):
                return json.dumps(existing_comments)
            if "/reviews" in path:
                return "[]"
            if "/commits/" in path:
                return json.dumps({"commit": {"committer": {"date": "2026-09-24T20:30:00Z"}}})
            if "/pulls/" in path:
                return json.dumps(pr())
            raise AssertionError(path)
        return gh

    def test_reports_once_then_stays_quiet(self):
        calls = []
        comments = [comment(READY, "2026-09-24T20:30:58Z")]
        reported = watchdog.sweep("z/t", gh=self.fake_gh(calls, comments), now=NOW)
        self.assertEqual(reported, [(206, f"handoff:{HEAD}")])
        post = [c for c in calls if "--method" in c][0]
        self.assertIn(watchdog.MARKER.format(f"handoff:{HEAD}"), post[-1])

        calls = []
        comments.append(comment(post[-1][len("body="):], "2026-09-25T12:00:00Z", ACTIONS))
        self.assertEqual(watchdog.sweep("z/t", gh=self.fake_gh(calls, comments), now=NOW), [])
        self.assertFalse([c for c in calls if "--method" in c])

    def test_dry_run_writes_nothing(self):
        calls = []
        watchdog.sweep("z/t", gh=self.fake_gh(calls, [comment(READY, "2026-09-24T20:30:58Z")]),
                       now=NOW, dry_run=True)
        self.assertFalse([c for c in calls if "--method" in c])


class TestWorkflow(unittest.TestCase):

    def setUp(self):
        self.text = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_comment_only_minimal_permissions(self):
        self.assertNotIn("actions:", self.text)
        self.assertNotIn("contents: write", self.text)
        self.assertNotIn("secrets.", self.text)

    def test_never_labels_wakes_or_fires(self):
        script = (SCRIPTS / "harness_watchdog.py").read_text(encoding="utf-8")
        for forbidden in ("/labels", "claude_cloud_bridge", "fire_once", "body=@codex"):
            self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()
