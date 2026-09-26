"""
Offline coverage for .github/scripts/harness_automerge.py and the merge step
of .github/workflows/codex-clean-verified.yml. No network, no subprocess.
"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path


def _repo_root():
    """The repository root: the nearest parent directory holding `.github`
    (this file lives in a different tests/ subfolder in different repos)."""
    here = Path(__file__).resolve()
    return next(p for p in here.parents if (p / ".github").is_dir())


REPO_ROOT = _repo_root()
SCRIPTS = REPO_ROOT / ".github" / "scripts"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "codex-clean-verified.yml"

_spec = importlib.util.spec_from_file_location("harness_automerge", SCRIPTS / "harness_automerge.py")
automerge = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = automerge
_spec.loader.exec_module(automerge)

HEAD = "4a2cc1be6dab4e82caebf15525040d98fddaa685"
CLOUDFLARE = "Workers Builds: zoe-tiktok-oauth"


def pr(**overrides):
    base = {"number": 298, "state": "open", "merged": False, "draft": False,
            "title": "MOLOSOC TikTok: route through canonical scheduler (Issue #297)",
            "labels": [{"name": "VERIFIED"}], "head": {"sha": HEAD},
            "base": {"ref": "main"}, "mergeable": True, "mergeable_state": "clean"}
    base.update(overrides)
    return base


def decide(item, failed=(), pending=(), base_failed=()):
    return automerge.decide(item, verified_head=HEAD, head_checks=(set(failed), set(pending)),
                            base_failed=set(base_failed))


class TestDecide(unittest.TestCase):

    def test_clean_verified_head_merges(self):
        self.assertEqual(decide(pr())[0], automerge.MERGE)

    def test_zoe_cloudflare_build_failing_on_main_too_does_not_block(self):
        # Real Zoe state 2026-09-25: this check fails on every commit of main.
        decision, _, ignored = decide(pr(), failed=[CLOUDFLARE], base_failed=[CLOUDFLARE])
        self.assertEqual(decision, automerge.MERGE)
        self.assertEqual(ignored, {CLOUDFLARE})

    def test_a_check_this_pr_broke_blocks(self):
        decision, reason, _ = decide(pr(), failed=["test"], base_failed=[CLOUDFLARE])
        self.assertEqual(decision, automerge.SKIP)
        self.assertIn("test", reason)

    def test_running_checks_are_waited_for(self):
        self.assertEqual(decide(pr(), pending=["isolation"])[0], automerge.WAIT)

    def test_a_push_after_verified_is_never_merged(self):
        decision, reason, _ = decide(pr(head={"sha": "b" * 40}))
        self.assertEqual(decision, automerge.SKIP)
        self.assertIn("pushed after VERIFIED", reason)

    def test_hold_draft_conflict_and_closed_are_skipped(self):
        for item, word in ((pr(title="HOLD: wait for launch"), "HOLD"),
                           (pr(labels=[{"name": "NO_AUTO_MERGE"}]), "NO_AUTO_MERGE"),
                           (pr(draft=True), "draft"),
                           (pr(mergeable=False, mergeable_state="dirty"), "conflict"),
                           (pr(state="closed"), "no longer open")):
            with self.subTest(word=word):
                decision, reason, _ = decide(item)
                self.assertEqual(decision, automerge.SKIP)
                self.assertIn(word, reason)

    def test_threshold_is_not_a_word_hold(self):
        self.assertEqual(decide(pr(title="Raise threshold for holdout"))[0], automerge.MERGE)


class TestCheckFailures(unittest.TestCase):

    def test_skipped_and_neutral_runs_are_fine(self):
        runs = [{"name": "fire", "status": "completed", "conclusion": "skipped"},
                {"name": "claude", "status": "completed", "conclusion": "neutral"},
                {"name": "test", "status": "completed", "conclusion": "success"},
                {"name": CLOUDFLARE, "status": "completed", "conclusion": "failure"},
                {"name": "isolation", "status": "in_progress", "conclusion": None}]
        statuses = [{"context": "ci/legacy", "state": "error"}]
        failed, pending = automerge.check_failures(runs, statuses)
        self.assertEqual(failed, {CLOUDFLARE, "ci/legacy"})
        self.assertEqual(pending, {"isolation"})


class FakeGitHub:
    def __init__(self, pulls, head_runs, base_runs=()):
        self.pulls = list(pulls)
        self.head_runs = list(head_runs)
        self.base_runs = list(base_runs)
        self.calls = []

    def __call__(self, argv, token=None):
        self.calls.append((argv, token))
        path = next(a for a in argv if a.startswith("repos/"))
        if "--method" in argv:
            return json.dumps({"sha": "m" * 40}) if path.endswith("/merge") else "{}"
        if path.endswith("pulls/298"):
            return json.dumps(self.pulls.pop(0) if len(self.pulls) > 1 else self.pulls[0])
        if "branches/" in path:
            return json.dumps({"commit": {"sha": "base"}})
        if path.endswith("/status"):
            return json.dumps({"statuses": []})
        if "commits/base/" in path:
            return json.dumps({"check_runs": self.base_runs})
        runs = self.head_runs.pop(0) if len(self.head_runs) > 1 else self.head_runs[0]
        return json.dumps({"check_runs": runs})

    def posts(self):
        return [(argv, token) for argv, token in self.calls if "--method" in argv]


class TestRun(unittest.TestCase):

    def run_with(self, fake, token="owner-token"):
        clock = [0.0]
        original = automerge._gh
        automerge._gh = fake
        automerge.os.environ["MERGE_TOKEN"] = token
        try:
            automerge.run("z/zoe", 298, HEAD, sleep=lambda s: clock.__setitem__(0, clock[0] + s),
                          now=lambda: clock[0])
        finally:
            automerge._gh = original
            del automerge.os.environ["MERGE_TOKEN"]
        return fake.posts()

    def test_waits_for_checks_then_merges_the_pinned_head_with_the_owner_token(self):
        running = [{"name": "test", "status": "in_progress", "conclusion": None}]
        done = [{"name": "test", "status": "completed", "conclusion": "success"}]
        posts = self.run_with(FakeGitHub([pr()], [running, running, done]))
        merge, comment = posts
        self.assertIn(f"sha={HEAD}", merge[0])
        self.assertEqual(merge[1], "owner-token")
        self.assertTrue(comment[0][-1].startswith("body=MERGED"))

    def test_checks_that_never_finish_skip_with_a_notice(self):
        running = [{"name": "test", "status": "queued", "conclusion": None}]
        posts = self.run_with(FakeGitHub([pr()], [running]))
        self.assertEqual(len(posts), 1)
        self.assertIn("AUTO_MERGE_SKIPPED", posts[0][0][-1])
        self.assertIn("after 20 minutes", posts[0][0][-1])

    def test_refused_merge_names_the_missing_permission(self):
        class Refusing(FakeGitHub):
            def __call__(self, argv, token=None):
                path = next(a for a in argv if a.startswith("repos/"))
                if path.endswith("/merge"):
                    self.calls.append((argv, token))
                    raise automerge.harness_handoff.GhError(
                        "`gh api --method PUT` failed: gh: Resource not accessible by personal "
                        "access token (HTTP 403)")
                if "/files" in path:
                    self.calls.append((argv, token))
                    return json.dumps([{"filename": ".github/workflows/x.yml"}])
                return super().__call__(argv, token)
        posts = self.run_with(Refusing([pr()], [[]]))
        notice = posts[-1][0][-1]
        self.assertIn("AUTO_MERGE_SKIPPED", notice)
        self.assertIn("Workflows: Read and write", notice)

    def test_missing_owner_token_never_merges(self):
        posts = self.run_with(FakeGitHub([pr()], [[]]), token="")
        self.assertEqual(len(posts), 1)
        self.assertIn("SANTIAGO_CODEX_BRIDGE_TOKEN", posts[0][0][-1])


class TestMergeRefusal(unittest.TestCase):

    def test_trafficdom_220_workflow_change_names_the_workflows_permission(self):
        error = "`gh api --method PUT` failed: gh: Resource not accessible by personal access token (HTTP 403)"
        reason = automerge.merge_refusal_reason(
            error, [".github/workflows/molosoc-finance-packeta-dry-run.yml", "tests/x.py"])
        self.assertIn("Workflows: Read and write", reason)
        self.assertIn("molosoc-finance-packeta-dry-run.yml", reason)
        self.assertIn("Contents: Read and write", reason)

    def test_trafficdom_213_code_change_names_contents(self):
        reason = automerge.merge_refusal_reason("HTTP 403: Resource not accessible", ["a.py"])
        self.assertIn("Contents: Read and write", reason)
        self.assertNotIn("Workflows", reason)

    def test_other_refusals_are_passed_through(self):
        reason = automerge.merge_refusal_reason("HTTP 405: Base branch was modified", [])
        self.assertIn("Base branch was modified", reason)
        self.assertNotIn("token needs", reason)


class TestNotices(unittest.TestCase):

    def test_notices_carry_no_handoff_keyword_line(self):
        sys.path.insert(0, str(SCRIPTS))
        import harness_handoff
        for text in (automerge.skipped_notice("x", HEAD), automerge.merged_notice(HEAD, "m", {"c"})):
            for keyword in ("READY_FOR_SANTIAGO", "NEEDS_ZANETA", "VERIFIED", "ZANETA_DECISION"):
                self.assertFalse(harness_handoff.has_keyword_line(text, keyword), (keyword, text))


class TestWorkflow(unittest.TestCase):

    def setUp(self):
        self.text = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_merge_runs_only_after_verified_with_the_owner_token(self):
        self.assertLess(self.text.index("name: Record VERIFIED"),
                        self.text.index("harness_automerge.py"))
        self.assertIn("MERGE_TOKEN: ${{ secrets.SANTIAGO_CODEX_BRIDGE_TOKEN }}", self.text)
        self.assertIn('--head "$HEAD_SHA"', self.text)
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", self.text)

    def test_a_rerun_retries_the_merge_of_an_open_verified_pr(self):
        # trafficdom #213/#220: after the token was fixed, re-running the failed
        # run stopped at "VERIFIED marker already exists" and never merged.
        self.assertIn('pr.state === "open" && !pr.merged', self.text)
        self.assertEqual(self.text.count("if: steps.validate.outputs.merge == 'true'"), 2)
        self.assertEqual(self.text.count("if: steps.validate.outputs.valid == 'true'"), 1)

    def test_job_can_wait_for_checks(self):
        self.assertIn("timeout-minutes: 30", self.text)


if __name__ == "__main__":
    unittest.main()
