#!/usr/bin/env python3
"""SAST Auto-Fix helper: trigger workflows, wait, download artifacts, summarize findings.

Usage: python3 sast-autofix.py --repo ~/iacgenie-platform [--branch devops]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def run(cmd, cwd=None, check=True):
    """Run a shell command and return stdout."""
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"ERROR: {cmd}\n{r.stderr}", file=sys.stderr)
        sys.exit(1)
    return r.stdout.strip()


def trigger_workflow(repo, branch, workflow):
    run(f"gh workflow run {workflow} --ref {branch}", cwd=repo)
    print(f"  Triggered {workflow} on {branch}")


def wait_for_run(repo, branch, workflow, timeout=600):
    """Wait for the latest run of a workflow to complete. Returns run ID."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        out = run(
            f"gh run list --branch {branch} --workflow {workflow} --limit 1 "
            f"--json databaseId,status,conclusion -q '.[0] | \"\\(.databaseId) \\(.status) \\(.conclusion)\"'",
            cwd=repo,
        )
        parts = out.split()
        if len(parts) >= 3 and parts[1] == "completed":
            return parts[0], parts[2]
        time.sleep(15)
    print(f"  TIMEOUT waiting for {workflow}", file=sys.stderr)
    sys.exit(1)


def download_artifacts(repo, run_id, dest):
    run(f"gh run download {run_id} -D {dest}", cwd=repo)
    print(f"  Downloaded artifacts for run {run_id} -> {dest}")


def summarize_artifacts(dest):
    """Read all JSON artifacts and print a categorized summary."""
    dest = Path(dest)
    if not dest.exists():
        print(f"  No artifacts at {dest}")
        return

    # Find the artifact subdirectory (e.g. sast-platform-5/)
    subdirs = [d for d in dest.iterdir() if d.is_dir()]
    if not subdirs:
        print(f"  No artifact subdirectories at {dest}")
        return
    art_dir = subdirs[0]

    print(f"\n{'='*60}")
    print(f"  SAST FINDINGS SUMMARY ({art_dir.name})")
    print(f"{'='*60}")

    for json_file in sorted(art_dir.glob("*.json")):
        try:
            data = json.load(open(json_file))
        except Exception as e:
            print(f"\n  {json_file.name}: ERROR reading ({e})")
            continue

        total = data.get("total", 0)
        print(f"\n  --- {json_file.stem}: {total} findings ---")
        for e in data.get("errors", []):
            file = e.get("file", e.get("filename", "?"))
            code = e.get("code", e.get("check_id", e.get("test_id", e.get("rule", "?"))))
            line = e.get("line", e.get("start_line", "?"))
            msg = e.get("message", e.get("text", e.get("check_name", "")))
            print(f"    [{code}] {file}:{line} - {msg[:100]}")


def main():
    parser = argparse.ArgumentParser(description="SAST Auto-Fix helper")
    parser.add_argument("--repo", default=os.path.expanduser("~/iacgenie-platform"))
    parser.add_argument("--branch", default="devops")
    parser.add_argument("--skip-trigger", action="store_true", help="Skip triggering workflows")
    parser.add_argument("--skip-wait", action="store_true", help="Skip waiting for completion")
    args = parser.parse_args()

    repo = os.path.expanduser(args.repo)
    if not os.path.isdir(repo):
        print(f"ERROR: repo not found: {repo}", file=sys.stderr)
        sys.exit(1)

    workflows = ["sast-platform.yml", "sast-lightserp.yml"]

    if not args.skip_trigger:
        print(f"Triggering SAST workflows on {args.branch}...")
        for wf in workflows:
            trigger_workflow(repo, args.branch, wf)

    results = {}
    for wf in workflows:
        if not args.skip_wait:
            print(f"Waiting for {wf}...")
            run_id, conclusion = wait_for_run(repo, args.branch, wf)
            print(f"  {wf}: run {run_id} -> {conclusion}")
            results[wf] = (run_id, conclusion)

            dest = f"/tmp/sast-artifacts-{wf.replace('sast-', '').replace('.yml', '')}"
            download_artifacts(repo, run_id, dest)
            summarize_artifacts(dest)
        else:
            # Just download the latest completed run
            run_id = run(
                f"gh run list --branch {args.branch} --workflow {wf} --limit 1 "
                f"--json databaseId -q '.[0].databaseId'",
                cwd=repo,
            )
            dest = f"/tmp/sast-artifacts-{wf.replace('sast-', '').replace('.yml', '')}"
            download_artifacts(repo, run_id, dest)
            summarize_artifacts(dest)

    print("\nDone. Review the findings above, categorize, and fix.")


if __name__ == "__main__":
    main()
