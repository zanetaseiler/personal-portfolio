"""
Every workflow that runs a harness script must grant its GITHUB_TOKEN what
that script's API calls need (the script's own GITHUB_TOKEN_PERMISSIONS).

bonafide PR #14 (2026-09-26): codex-clean-verified.yml ran
harness_automerge.py without `checks: read`, so reading the head's check runs
failed with "Resource not accessible by integration (HTTP 403)" and a
VERIFIED PR was not merged. Unit tests with a fake `gh` cannot see this.
"""

import importlib.util
import re
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
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
HARNESS_SCRIPTS = ("harness_automerge.py", "harness_guard.py", "harness_handoff.py",
                   "harness_requeue.py", "harness_watchdog.py")
LEVEL = {"none": 0, "read": 1, "write": 2}


def required(script):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(f"perm_{script[:-3]}", SCRIPTS / script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GITHUB_TOKEN_PERMISSIONS


def _block(lines, start, indent):
    """`key: value` pairs of the mapping starting after lines[start] at `indent`."""
    found = {}
    for line in lines[start + 1:]:
        if not line.strip() or line.strip().startswith("#"):
            continue
        if len(line) - len(line.lstrip()) < indent:
            break
        match = re.match(rf"^ {{{indent}}}([a-z-]+):\s*([a-z-]+)\s*$", line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def jobs_with_permissions(text):
    """`[(job_name, permissions, job_text)]`; a job without its own
    `permissions:` gets the workflow-level block."""
    lines = text.splitlines()
    top = next((_block(lines, i, 2) for i, l in enumerate(lines) if l == "permissions:"), {})
    jobs_at = lines.index("jobs:")
    starts = [i for i, l in enumerate(lines) if i > jobs_at and re.match(r"^  [\w-]+:\s*$", l)]
    result = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        body = lines[start:end]
        own = next((_block(body, i, 6) for i, l in enumerate(body) if l == "    permissions:"), None)
        result.append((lines[start].strip()[:-1], top if own is None else own, "\n".join(body)))
    return result


class TestWorkflowsGrantWhatHarnessScriptsNeed(unittest.TestCase):

    def test_every_job_running_a_harness_script_has_its_permissions(self):
        checked = 0
        for workflow in sorted(WORKFLOWS.glob("*.yml")):
            for job, granted, body in jobs_with_permissions(workflow.read_text(encoding="utf-8")):
                for script in HARNESS_SCRIPTS:
                    if script not in body or not (SCRIPTS / script).exists():
                        continue
                    checked += 1
                    for scope, level in required(script).items():
                        with self.subTest(workflow=workflow.name, job=job, script=script, scope=scope):
                            self.assertGreaterEqual(
                                LEVEL[granted.get(scope, "none")], LEVEL[level],
                                f"{workflow.name} job `{job}` runs {script} but grants "
                                f"`{scope}: {granted.get(scope, 'none')}`; it needs `{scope}: {level}`")
        self.assertGreater(checked, 0)

    def test_bonafide_14_automerge_can_read_checks(self):
        text = (WORKFLOWS / "codex-clean-verified.yml").read_text(encoding="utf-8")
        (_, granted, _), = [j for j in jobs_with_permissions(text) if "harness_automerge.py" in j[2]]
        self.assertEqual(granted.get("checks"), "read")
        self.assertEqual(granted.get("statuses"), "read")

    def test_parser_reads_workflow_and_job_level_blocks(self):
        text = ("on: push\npermissions:\n  contents: read\n  issues: write\njobs:\n"
                "  a:\n    runs-on: x\n    steps:\n      - run: python3 harness_guard.py\n"
                "  b:\n    permissions:\n      checks: read\n    steps:\n      - run: y\n")
        jobs = {name: granted for name, granted, _ in jobs_with_permissions(text)}
        self.assertEqual(jobs["a"], {"contents": "read", "issues": "write"})
        self.assertEqual(jobs["b"], {"checks": "read"})


if __name__ == "__main__":
    unittest.main()
