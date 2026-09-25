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

    def issue(self, labels=(), body="", created="2026-09-25T10:00:00Z"):
        return {"number": 64, "labels": [{"name": n} for n in labels], "body": body,
                "created_at": created}

    def test_label_written_as_text_is_reported(self):
        stall = watchdog.check_issue(self.issue(body="Do X.\n\nREADY_FOR_CLAUDE_CLOUD"), [],
                                     labeled_at=None, now=NOW)
        self.assertEqual(stall[0], "label-as-text")

    def test_label_as_text_is_fine_once_dispatched(self):
        comments = [comment("ROUTINE_DISPATCHED\n", "2026-09-25T10:01:00Z", ACTIONS)]
        self.assertIsNone(watchdog.check_issue(self.issue(body="READY_FOR_CLAUDE_CLOUD"),
                                               comments, labeled_at=None, now=NOW))

    def test_label_still_present_after_the_wait_is_reported(self):
        stall = watchdog.check_issue(self.issue(labels=["READY_FOR_CLAUDE_CLOUD"]), [],
                                     labeled_at="2026-09-25T11:00:00Z", now=NOW)
        self.assertTrue(stall[0].startswith("label:"))

    def test_fresh_label_is_not_reported(self):
        self.assertIsNone(watchdog.check_issue(self.issue(labels=["READY_FOR_CLAUDE_CLOUD"]), [],
                                               labeled_at="2026-09-25T11:55:00Z", now=NOW))

    def test_ordinary_issue_is_not_reported(self):
        self.assertIsNone(watchdog.check_issue(self.issue(body="notes"), [], labeled_at=None, now=NOW))


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

    def test_dispatched_claude_that_never_pushed_is_reported(self):
        comments = [comment(READY, "2026-09-24T20:31:00Z"),
                    comment(f"ROUTINE_DISPATCHED\n- dispatch round: 0 @ {HEAD}\n",
                            "2026-09-24T20:41:00Z", ACTIONS)]
        stall = self.check(comments, [review("2026-09-24T20:40:00Z")])
        self.assertEqual(stall[0], f"claude:{HEAD}")

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
