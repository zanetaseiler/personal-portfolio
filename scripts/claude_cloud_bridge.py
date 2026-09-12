#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

QUEUE_LABEL = "READY_FOR_CLAUDE_CLOUD"
ROUTINE_FIRE_URL_ENV_VAR = "CLAUDE_ROUTINE_FIRE_URL"
ROUTINE_TOKEN_ENV_VAR = "CLAUDE_ROUTINE_FIRE_TOKEN"
ANTHROPIC_BETA_HEADER = "experimental-cc-routine-2026-04-01"
ANTHROPIC_VERSION_HEADER = "2023-06-01"

class CloudBridgeError(RuntimeError):
    pass

@dataclass(frozen=True)
class WorkItem:
    kind: str
    number: int
    repo: str

    @property
    def gh_subcommand(self):
        return "issue" if self.kind == "issue" else "pr"

    @property
    def label(self):
        return "Issue" if self.kind == "issue" else "Pull Request"

    @property
    def url(self):
        path = "issues" if self.kind == "issue" else "pull"
        return f"https://github.com/{self.repo}/{path}/{self.number}"


def gh(argv):
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise CloudBridgeError(f"GitHub command failed ({result.returncode}): {result.stderr.strip()}")
    return result.stdout


def label_present(item):
    raw = gh(["gh", item.gh_subcommand, "view", str(item.number), "--repo", item.repo, "--json", "labels"])
    data = json.loads(raw or "{}")
    return QUEUE_LABEL in {x.get("name", "") for x in data.get("labels", [])}


def remove_label(item):
    gh(["gh", item.gh_subcommand, "edit", str(item.number), "--repo", item.repo, "--remove-label", QUEUE_LABEL])


def post_comment(item, body):
    gh(["gh", item.gh_subcommand, "comment", str(item.number), "--repo", item.repo, "--body", body])


def fire(item, url, token):
    if not label_present(item):
        print("queue label absent; nothing to dispatch")
        return 1
    remove_label(item)
    payload = json.dumps({"text": f"{item.repo} {item.label} #{item.number} ({item.url})"}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST", headers={"Authorization": f"Bearer {token}", "anthropic-beta": ANTHROPIC_BETA_HEADER, "anthropic-version": ANTHROPIC_VERSION_HEADER, "Content-Type": "application/json", "User-Agent": "ClaudeCloudBridge/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read(); status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code; body = exc.read() or b""
    except urllib.error.URLError as exc:
        post_comment(item, f"ROUTINE_FIRE_FAILED\n\n- transport error: {exc}\n- no automatic retry was made; explicitly re-apply {QUEUE_LABEL} to re-queue.\n"); return 1
    if not (200 <= status < 300):
        safe = body.decode("utf-8", errors="replace")[:2000]
        post_comment(item, f"ROUTINE_FIRE_FAILED\n\n- http status: {status}\n- error: {safe}\n- no automatic retry was made; explicitly re-apply {QUEUE_LABEL} to re-queue.\n"); return 1
    data = json.loads(body.decode("utf-8")) if body else {}
    post_comment(item, f"ROUTINE_DISPATCHED\n\n- repo: {item.repo}\n- item: {item.label} #{item.number}\n- session id: {data.get('claude_code_session_id','unknown')}\n- session url: {data.get('claude_code_session_url','unknown')}\n")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(); parser.add_argument("--repo", required=True)
    group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--issue", type=int); group.add_argument("--pr", type=int)
    args = parser.parse_args(argv)
    url = os.environ.get(ROUTINE_FIRE_URL_ENV_VAR); token = os.environ.get(ROUTINE_TOKEN_ENV_VAR)
    if not url or not token:
        print("required Routine trigger configuration is not set", file=sys.stderr); return 1
    item = WorkItem("issue" if args.issue is not None else "pr", args.issue if args.issue is not None else args.pr, args.repo)
    return fire(item, url, token)

if __name__ == "__main__":
    raise SystemExit(main())
