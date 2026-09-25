"""
Offline coverage for .github/scripts/harness_handoff.py and
.github/workflows/santiago-ready-label-trigger.yml -- the Claude -> Santiago
handoff. The fixtures replay the real PR #204/#206 comments the previous
first-line-only parser dropped silently.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

def _repo_root():
    """The repository root: the nearest parent directory holding `.github`
    (this file lives in a different tests/ subfolder in different repos)."""
    here = Path(__file__).resolve()
    return next(p for p in here.parents if (p / ".github").is_dir())


REPO_ROOT = _repo_root()
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "harness_handoff.py"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "santiago-ready-label-trigger.yml"

_spec = importlib.util.spec_from_file_location("harness_handoff", SCRIPT_PATH)
handoff = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = handoff
_spec.loader.exec_module(handoff)

HEAD = "4511b503a98f5b917eba4caf531872e207ff99a5"
OWNER = "zanetaseiler"

# PR #206, 2026-09-24T20:30:58Z: correction-round format, CONTEXT_RECEIPT first.
CORRECTION_COMMENT = f"""CONTEXT_RECEIPT

- current base-branch commit SHA (PR head at receipt time): `e6ef1eb6d2f96c089abbca6222dccb96da1c4699`
- unresolved questions: none

Corrections made: see below. Affected tests run: see below.

---

READY_FOR_SANTIAGO

- Block number: Issue #205
- exact head commit SHA: `{HEAD}`

STOP -- waiting for Santiago's review.
"""


def evaluate(body, *, author=OWNER, is_pr=True, head=HEAD):
    return handoff.evaluate(body=body, author=author, owner=OWNER, is_pr=is_pr, current_head=head)


class TestKeywordLine(unittest.TestCase):

    def test_keyword_later_in_a_correction_comment_is_a_handoff(self):
        self.assertEqual(evaluate(CORRECTION_COMMENT)[0], handoff.HANDOFF)

    def test_keyword_first_line_still_works(self):
        body = f"READY_FOR_SANTIAGO\n\n- exact head commit SHA: `{HEAD}`\n"
        self.assertEqual(evaluate(body)[0], handoff.HANDOFF)

    def test_markdown_decoration_is_tolerated(self):
        for line in ("## READY_FOR_SANTIAGO", "**READY_FOR_SANTIAGO**",
                     "  READY_FOR_SANTIAGO:  ", "`READY_FOR_SANTIAGO`"):
            with self.subTest(line=line):
                self.assertEqual(evaluate(f"{line}\n\nHead SHA: {HEAD[:7]}")[0], handoff.HANDOFF)

    def test_keyword_followed_by_a_dash_and_date_counts(self):
        self.assertTrue(handoff.has_keyword_line("ZANETA_DECISION \u2014 2026-09-25\n\nGo.",
                                                 "ZANETA_DECISION"))
        self.assertEqual(evaluate(f"READY_FOR_SANTIAGO \u2014 round 3\n{HEAD}")[0], handoff.HANDOFF)

    def test_longer_word_is_not_the_keyword(self):
        self.assertFalse(handoff.has_keyword_line("READY_FOR_SANTIAGO_LATER\n" + HEAD))

    def test_inline_mention_is_not_a_handoff(self):
        body = f"No live publish -- this Block stops at `READY_FOR_SANTIAGO` ({HEAD})."
        self.assertEqual(evaluate(body), (handoff.NOT_A_HANDOFF, ""))

    def test_keyword_inside_a_code_fence_is_not_a_handoff(self):
        body = f"Format:\n```\nREADY_FOR_SANTIAGO\n- exact head commit SHA: {HEAD}\n```\n"
        self.assertEqual(evaluate(body)[0], handoff.NOT_A_HANDOFF)


class TestHeadMatching(unittest.TestCase):

    def test_short_sha_is_enough(self):
        self.assertEqual(evaluate(f"READY_FOR_SANTIAGO\nhead: {HEAD[:7]}")[0], handoff.HANDOFF)

    def test_right_short_sha_with_a_mistyped_tail_is_accepted(self):
        # PR #204, 2026-09-23T12:56:13Z: real head e723773da062..., comment claimed e7237736ab2f...
        body = "READY_FOR_SANTIAGO\n- exact head commit SHA: `e7237736ab2f1e07eab6c3ec8fc6d54a4dc0c62d`"
        self.assertEqual(evaluate(body, head="e723773da06227cac7bf5052e50c13a41a3b22f6")[0],
                         handoff.HANDOFF)

    def test_any_sha_line_wording_is_accepted(self):
        # PR #204, 2026-09-24T18:13:57Z: "authoritative PR #204 head verified from git"
        body = ("READY_FOR_SANTIAGO\n\n- authoritative PR #204 head verified from git "
                "(`git rev-parse HEAD` on the pushed branch): `ce93325bfd729f076cd94adad36e6f6cec471bcd`")
        self.assertEqual(evaluate(body, head="ce93325bfd729f076cd94adad36e6f6cec471bcd")[0],
                         handoff.HANDOFF)

    def test_only_an_older_sha_is_ignored_loudly(self):
        body = "READY_FOR_SANTIAGO\n- exact head commit SHA: `e6ef1eb6d2f96c089abbca6222dccb96da1c4699`"
        decision, reason = evaluate(body)
        self.assertEqual(decision, handoff.IGNORED)
        self.assertIn(HEAD, reason)

    def test_missing_sha_is_ignored_loudly(self):
        decision, reason = evaluate("READY_FOR_SANTIAGO\n\nAll done.")
        self.assertEqual(decision, handoff.IGNORED)
        self.assertIn("no commit SHA", reason)


class TestWhereAndWho(unittest.TestCase):

    def test_handoff_on_an_issue_is_ignored_loudly(self):
        decision, reason = evaluate(CORRECTION_COMMENT, is_pr=False, head="")
        self.assertEqual(decision, handoff.IGNORED)
        self.assertIn("PR", reason)

    def test_handoff_from_another_account_is_ignored_loudly(self):
        decision, reason = evaluate(CORRECTION_COMMENT, author="claude[bot]")
        self.assertEqual(decision, handoff.IGNORED)
        self.assertIn("claude[bot]", reason)


class TestNotices(unittest.TestCase):

    def test_notice_never_contains_a_keyword_line_of_its_own(self):
        notice = handoff.ignored_notice("x")
        self.assertTrue(notice.startswith("HANDOFF_IGNORED"))
        self.assertFalse(handoff.has_keyword_line(notice))


class TestCheckOnlyMode(unittest.TestCase):

    def run_check(self, body, head=HEAD):
        import io, json, os, tempfile
        from contextlib import redirect_stdout
        event = {"comment": {"body": body, "user": {"login": OWNER}},
                 "repository": {"owner": {"login": OWNER}}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(event, handle)
        old = os.environ.get("GITHUB_EVENT_PATH")
        os.environ["GITHUB_EVENT_PATH"] = handle.name
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                self.assertEqual(handoff.main(["--human", OWNER, "--repo", "o/r", "--number", "1",
                                               "--check-only", head]), 0)
        finally:
            os.unlink(handle.name)
            if old is None:
                del os.environ["GITHUB_EVENT_PATH"]
            else:
                os.environ["GITHUB_EVENT_PATH"] = old
        return out.getvalue().rstrip("\n").split("\t", 1)

    def test_prints_the_decision_without_needing_a_token_or_network(self):
        self.assertEqual(self.run_check(CORRECTION_COMMENT)[0], handoff.HANDOFF)
        decision, reason = self.run_check("READY_FOR_SANTIAGO\nno sha")
        self.assertEqual(decision, handoff.IGNORED)
        self.assertIn("no commit SHA", reason)


class TestWorkflow(unittest.TestCase):

    def setUp(self):
        self.text = WORKFLOW_PATH.read_text(encoding="utf-8")
        if "harness_handoff.py" not in self.text:
            self.fail("santiago-ready-label-trigger.yml must run .github/scripts/harness_handoff.py")
        if "--check-only" in self.text:
            self.skipTest("this repo's own workflow wakes Codex; only the shared parser is used")

    def test_runs_the_trusted_default_branch_script(self):
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", self.text)
        self.assertIn("python3 .github/scripts/harness_handoff.py", self.text)

    def test_any_comment_mentioning_the_keyword_reaches_the_script(self):
        self.assertIn("contains(github.event.comment.body, 'READY_FOR_SANTIAGO')", self.text)
        self.assertNotIn("startsWith(github.event.comment.body", self.text)

    def test_codex_is_woken_with_the_owner_token_and_notices_use_github_token(self):
        self.assertIn("CODEX_WAKE_TOKEN: ${{ secrets.SANTIAGO_CODEX_BRIDGE_TOKEN }}", self.text)
        self.assertIn("GH_TOKEN: ${{ github.token }}", self.text)

    def test_authorized_human_is_a_person_not_the_repository_owner(self):
        self.assertNotIn("github.repository_owner", self.text)
        self.assertIn("AUTHORIZED_HUMAN: ${{ vars.HARNESS_HUMAN_LOGIN }}", self.text)
        self.assertIn('--human "${AUTHORIZED_HUMAN:-zanetaseiler}"', self.text)

    def test_no_schedule_or_actions_scope(self):
        self.assertNotIn("schedule:", self.text)
        self.assertNotIn("actions:", self.text)


if __name__ == "__main__":
    unittest.main()
