"""
Offline coverage for .github/scripts/harness_guard.py -- one Claude session
per Block. The fixtures replay Zoe Issue #297 / PR #298 (2026-09-25), where a
ZANETA_DECISION on the PR and Santiago's label on the Issue started two
Claude sessions on one branch within six seconds.
"""

import importlib.util
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
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("harness_guard", SCRIPTS / "harness_guard.py")
guard = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = guard
_spec.loader.exec_module(guard)

BOT = "github-actions[bot]"
HUMAN = "zanetaseiler"
PR_298 = {"number": 298, "updated_at": "2026-09-25T10:21:00Z",
          "title": "MOLOSOC TikTok: route through canonical tiktok-app scheduler (Issue #297)",
          "body": "Closes #297.\n\nThe abandoned attempt from #289 is not resurrected."}


def comment(body, at, user=HUMAN):
    return {"body": body, "created_at": at, "user": {"login": user}}


def dispatch(at, session="cse_01UsWskwrTyMQAP8NtTBsJt5"):
    return comment(f"ROUTINE_DISPATCHED\n\n- item: Pull Request #298\n"
                   f"- session url: https://claude.ai/code/{session}\n", at, BOT)


def at(hhmmss):
    return datetime.fromisoformat(f"2026-09-25T{hhmmss}+00:00").astimezone(timezone.utc)


class TestBlockLinks(unittest.TestCase):

    def test_issue_297_belongs_to_pr_298(self):
        self.assertEqual(guard.block_pr(297, [PR_298])["number"], 298)
        self.assertEqual(guard.linked_issues(PR_298), [297])

    def test_a_passing_mention_does_not_link(self):
        # PR #298's body mentions #289 only in passing; #289 is not its Block.
        self.assertIsNone(guard.block_pr(289, [PR_298]))

    def test_closing_keywords_link(self):
        for body in ("Fixes #12", "resolves: #12", "Closes #12 and more"):
            with self.subTest(body=body):
                self.assertTrue(guard.links_issue({"title": "x", "body": body}, 12))
        self.assertFalse(guard.links_issue({"title": "x", "body": "Closes #123"}, 12))


class TestSessionState(unittest.TestCase):

    NEEDS = comment("NEEDS_ZANETA\n\n- question", "2026-09-25T09:57:04Z")

    def test_zoe_297_second_start_is_refused(self):
        # 10:16:38 the PR session started; the Issue label arrived right after.
        comments = [dispatch("2026-09-25T09:51:26Z"), self.NEEDS,
                    comment("ZANETA_DECISION — 2026-09-25\n\n(b)", "2026-09-25T10:16:16Z"),
                    dispatch("2026-09-25T10:16:38Z")]
        state, running = guard.session_state(comments, now=at("10:16:44"))
        self.assertEqual(state, guard.BUSY)
        self.assertEqual(running["created_at"], "2026-09-25T10:16:38Z")

    def test_decision_after_needs_zaneta_starts_claude(self):
        comments = [dispatch("2026-09-25T09:51:26Z"), self.NEEDS]
        self.assertEqual(guard.session_state(comments, now=at("10:16:20"))[0], guard.FREE)

    def test_handoff_frees_the_block_for_the_codex_correction_round(self):
        comments = [dispatch("2026-09-25T10:16:38Z"),
                    comment("READY_FOR_SANTIAGO\n- exact head commit SHA: `4a2cc1b`",
                            "2026-09-25T10:21:06Z")]
        self.assertEqual(guard.session_state(comments, now=at("10:40:00"))[0], guard.FREE)

    def test_mid_session_codex_review_does_not_start_a_second_session(self):
        comments = [dispatch("2026-09-25T10:16:38Z"),
                    comment("CONTEXT_RECEIPT\n...", "2026-09-25T10:19:09Z")]
        self.assertEqual(guard.session_state(comments, now=at("10:30:00"))[0], guard.BUSY)

    def test_lock_expires_when_the_watchdog_would_report_the_session(self):
        comments = [dispatch("2026-09-25T09:00:00Z")]
        self.assertEqual(guard.session_state(comments, now=at("09:59:59"))[0], guard.BUSY)
        self.assertEqual(guard.session_state(comments, now=at("10:00:00"))[0], guard.FREE)

    def test_no_dispatch_yet_is_free(self):
        self.assertEqual(guard.session_state([], now=at("10:00:00"))[0], guard.FREE)

    def test_a_human_quoting_the_word_is_not_a_dispatch(self):
        comments = [comment("ROUTINE_DISPATCHED looked odd", "2026-09-25T10:00:00Z")]
        self.assertEqual(guard.session_state(comments, now=at("10:01:00"))[0], guard.FREE)


class TestNotice(unittest.TestCase):

    def test_names_the_running_session_and_when_the_watchdog_takes_over(self):
        notice = guard.busy_notice(dispatch("2026-09-25T10:16:38Z"), now=at("10:20:00"))
        self.assertTrue(notice.startswith("HANDOFF_IGNORED"))
        self.assertIn("https://claude.ai/code/cse_01UsWskwrTyMQAP8NtTBsJt5", notice)
        self.assertIn("11:16", notice)
        self.assertFalse(guard.harness_handoff.has_keyword_line(notice, "READY_FOR_SANTIAGO"))
        self.assertFalse(guard.harness_handoff.has_keyword_line(notice, "NEEDS_ZANETA"))

    def test_duplicate_delivery_within_two_minutes_stays_quiet(self):
        running = dispatch("2026-09-25T10:16:38Z")
        self.assertTrue(guard.is_quiet_duplicate(running, now=at("10:16:44")))
        self.assertFalse(guard.is_quiet_duplicate(running, now=at("10:20:00")))


class TestWorkflows(unittest.TestCase):

    def test_bridge_routes_then_checks_inside_a_per_block_lock(self):
        text = (WORKFLOWS / "claude-cloud-routine-bridge.yml").read_text(encoding="utf-8")
        self.assertIn("harness_guard.py route", text)
        self.assertIn("harness_guard.py check", text)
        self.assertIn("group: claude-block-${{ needs.route.outputs.target }}", text)
        self.assertIn("if: steps.guard.outputs.go == 'true'", text)
        self.assertLess(text.index("harness_guard.py check"), text.rindex("claude_cloud_bridge.py"))

    def test_codex_feedback_checks_before_firing_directly(self):
        text = (WORKFLOWS / "codex-feedback-to-claude.yml").read_text(encoding="utf-8")
        self.assertIn("harness_guard.py check", text)
        self.assertIn("steps.guard.outputs.go == 'true'", text)
        self.assertLess(text.index("harness_guard.py check"), text.rindex("claude_cloud_bridge.py"))


if __name__ == "__main__":
    unittest.main()
