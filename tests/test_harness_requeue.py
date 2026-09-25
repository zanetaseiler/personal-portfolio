"""
Offline coverage for .github/scripts/harness_requeue.py and
.github/workflows/harness-requeue.yml -- starting Claude on a new task
Issue and restarting it on a ZANETA_DECISION, with no manual label. The
fixtures replay Zoe #287/#288/#290/#294 (2026-09-24/25).
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
SCRIPTS = REPO_ROOT / ".github" / "scripts"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "harness-requeue.yml"

sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("harness_requeue", SCRIPTS / "harness_requeue.py")
requeue = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = requeue
_spec.loader.exec_module(requeue)

HUMAN = "zanetaseiler"
TASK_BODY = ("## Goal\n\nDo the thing.\n\n## Protocol\n\n"
             "Mandatory workflow: CONTEXT_RECEIPT -> Claude Code implementation -> PR -> "
             "READY_FOR_SANTIAGO exact SHA -> Santiago review -> Zaneta merge.")


def issue(number, created, *, title="MOLOSOC TikTok - verify approval", body=TASK_BODY,
          labels=(), user=HUMAN):
    return {"number": number, "title": title, "body": body, "created_at": created,
            "labels": [{"name": n} for n in labels], "user": {"login": user}}


def opened(item, others=()):
    return requeue.evaluate_opened(item, human=HUMAN, open_issues=[item, *others])


class TestOpened(unittest.TestCase):

    def test_zoe_294_task_issue_without_a_label_starts_claude(self):
        self.assertEqual(opened(issue(294, "2026-09-25T07:51:11Z"))[0], requeue.START)

    def test_zoe_287_288_duplicate_starts_only_once(self):
        first = issue(287, "2026-09-24T18:17:49Z")
        second = issue(288, "2026-09-24T18:18:14Z")
        self.assertEqual(opened(first, [second])[0], requeue.START)
        decision, reason = opened(second, [first])
        self.assertEqual(decision, requeue.IGNORED)
        self.assertIn("#287", reason)

    def test_label_already_applied_is_left_to_the_bridge(self):
        item = issue(1, "2026-09-25T07:00:00Z", labels=["READY_FOR_CLAUDE_CLOUD"])
        self.assertEqual(opened(item)[0], requeue.SKIP)

    def test_hold_notes_and_other_authors_are_not_started(self):
        self.assertEqual(opened(issue(1, "2026-09-25T07:00:00Z", title="HOLD: idea"))[0], requeue.SKIP)
        self.assertEqual(opened(issue(1, "2026-09-25T07:00:00Z", body="just a note"))[0], requeue.SKIP)
        self.assertEqual(opened(issue(1, "2026-09-25T07:00:00Z", user="someone"))[0], requeue.SKIP)

    def test_same_title_long_ago_is_not_a_duplicate(self):
        old = issue(100, "2026-09-20T07:00:00Z")
        self.assertEqual(opened(issue(200, "2026-09-25T07:00:00Z"), [old])[0], requeue.START)


class TestDecision(unittest.TestCase):

    def comment(self, body, user=HUMAN):
        return {"body": body, "user": {"login": user}}

    def test_zoe_290_decision_restarts_claude(self):
        body = "ZANETA_DECISION — 2026-09-25\n\nKeep the earlier accepted decisions."
        self.assertEqual(requeue.evaluate_comment(self.comment(body), human=HUMAN)[0], requeue.START)

    def test_decision_from_someone_else_is_ignored_loudly(self):
        decision, reason = requeue.evaluate_comment(self.comment("ZANETA_DECISION\n\nx", "bot"),
                                                    human=HUMAN)
        self.assertEqual(decision, requeue.IGNORED)
        self.assertIn("bot", reason)

    def test_mentions_and_other_comments_do_nothing(self):
        for body in ("Waiting for a ZANETA_DECISION on this.", "NEEDS_ZANETA\n- question"):
            with self.subTest(body=body):
                self.assertEqual(requeue.evaluate_comment(self.comment(body), human=HUMAN)[0],
                                 requeue.SKIP)


class TestSetupProblems(unittest.TestCase):

    def run_main(self, token, refuse=False):
        import io, json, os, tempfile
        from contextlib import redirect_stderr, redirect_stdout
        item = issue(13, "2026-09-25T17:53:22Z")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"issue": item}, handle)
        calls = []

        def gh(argv, token=None):
            calls.append((argv, token))
            if token and refuse:
                raise requeue.harness_handoff.GhError("HTTP 403: Resource not accessible")
            if argv[-1].endswith("per_page=100"):
                return json.dumps([item])
            if argv[-1].endswith("issues/13"):
                return json.dumps(item)
            return "{}"

        saved = {k: os.environ.get(k) for k in ("GITHUB_EVENT_PATH", "HUMAN_TOKEN")}
        os.environ["GITHUB_EVENT_PATH"] = handle.name
        os.environ["HUMAN_TOKEN"] = token
        originals = (requeue._gh, requeue.harness_handoff._gh, requeue.subprocess.run)
        requeue._gh = requeue.harness_handoff._gh = gh
        requeue.subprocess.run = lambda *a, **k: None  # the tolerant label DELETE
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = requeue.main(["--repo", "bonafide-nitro/bonafide-website", "--human", HUMAN])
        finally:
            requeue._gh, requeue.harness_handoff._gh, requeue.subprocess.run = originals
            os.unlink(handle.name)
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        posts = [argv[-1] for argv, _ in calls if "--method" in argv and "/comments" in argv[3]]
        return code, posts

    def test_bonafide_13_missing_token_is_reported_on_the_issue(self):
        code, posts = self.run_main("")
        self.assertEqual(code, 1)
        self.assertEqual(len(posts), 1)
        self.assertIn("HARNESS_SETUP_PROBLEM", posts[0])
        self.assertIn("starting Claude", posts[0])

    def test_refused_token_is_reported_with_githubs_words(self):
        code, posts = self.run_main("token", refuse=True)
        self.assertEqual(code, 1)
        self.assertIn("Resource not accessible", posts[-1])


class TestWorkflow(unittest.TestCase):

    def setUp(self):
        self.text = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_runs_the_trusted_script_with_the_owner_token(self):
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", self.text)
        self.assertIn("python3 .github/scripts/harness_requeue.py", self.text)
        self.assertIn("HUMAN_TOKEN: ${{ secrets.SANTIAGO_CODEX_BRIDGE_TOKEN }}", self.text)
        self.assertIn('--human "${AUTHORIZED_HUMAN:-zanetaseiler}"', self.text)

    def test_listens_to_new_issues_and_decisions_only(self):
        self.assertIn("types: [opened]", self.text)
        self.assertIn("contains(github.event.comment.body, 'ZANETA_DECISION')", self.text)
        self.assertNotIn("schedule:", self.text)

    def test_never_names_the_queue_label_or_fires_the_routine_itself(self):
        # The label is applied by the script; the bridge workflow stays the only
        # place that fires the Routine (Zoe's single-control-path tests pin this).
        self.assertNotIn("READY_FOR_CLAUDE_CLOUD", self.text)
        self.assertNotIn("claude_cloud_bridge", self.text)
        self.assertNotIn("CLAUDE_ROUTINE_FIRE", self.text)


if __name__ == "__main__":
    unittest.main()
