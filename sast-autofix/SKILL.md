---
name: sast-autofix
description: Runs the SAST linter workflows, downloads the artifact JSONs, categorizes findings as false positives vs fixable, fixes all fixable issues, commits and pushes to the devops branch.
tags: [sast, lint, security, ci, autofix, github-actions]
---

# SAST Auto-Fix

End-to-end pipeline: trigger SAST workflows → download artifact JSONs → categorize findings → fix fixable issues → commit & push.

## Overview

This skill automates the loop of running the SAST linters on the `iacgenie-platform` repo, collecting the findings, separating real issues from false positives, and fixing the real ones. It is designed to be run repeatedly until the fixable finding count reaches zero.

## Prerequisites

- Repo: `~/iacgenie-platform` (branch `devops`)
- `gh` CLI authenticated against `manjufkanavi/iacgenie-platform`
- SAST workflows already present: `.github/workflows/sast-platform.yml` and `.github/workflows/sast-lightserp.yml`
- SAST toolchain image `.sast/` already committed

## Workflow

The agent runs these steps sequentially:

### Step 1: Trigger the SAST workflows

```bash
cd ~/iacgenie-platform
gh workflow run sast-platform.yml --ref devops
gh workflow run sast-lightserp.yml --ref devops
```

Wait for both runs to complete (poll `gh run list --branch devops` until the newest runs finish). Each run takes ~3-5 minutes.

### Step 2: Download the artifact JSONs

```bash
# Find the run IDs for the latest runs
gh run list --branch devops --workflow sast-platform.yml --limit 1 --json databaseId -q '.[0].databaseId'
gh run list --branch devops --workflow sast-lightserp.yml --limit 1 --json databaseId -q '.[0].databaseId'

# Download artifacts
gh run download <PLATFORM_RUN_ID> -D /tmp/sast-artifacts-platform
gh run download <LIGHTSERP_RUN_ID> -D /tmp/sast-artifacts-lightserp
```

### Step 3: Extract and read all findings

Each artifact directory contains normalized JSON files: `ruff.json`, `bandit.json`, `semgrep.json`, `mypy.json`, `flake8.json`, `eslint.json`, `gitleaks.json`, `checkov.json` (Ansible).

Read every JSON file and collect all findings. Each finding has: `file`, `code`/`check_id`/`test_id`/`rule`, `line`, `message`.

### Step 4: Categorize findings

Classify each finding into one of two buckets:

**False positives (non-fixable)** — do NOT touch these:
- Findings in third-party / vendored / generated code (e.g. `node_modules`, `dist`, `.venv`)
- Findings that are intentional design decisions (e.g. binding to all interfaces for a dev server, MD5 used for non-security hashing like rate-limit keys)
- Findings where the "fix" would change behavior or break functionality
- Checkov `CKV2_ANSIBLE_1` (HTTPS url) findings where the URL is an internal service that legitimately uses HTTP
- Findings already allowlisted in `.sast/*.toml` configs
- Gitleaks findings on historical commits (not current files)

**Fixable** — fix these:
- Unused imports (F401) — remove the import line
- Undefined names (F821) — add the missing import or fix the reference
- Unused variables (F841) — remove the assignment or prefix with `_`
- f-strings without placeholders (F541) — remove the `f` prefix
- Missing `timeout` on `requests` calls (B113) — add `timeout=...`
- MD5 used for security purposes (B324/semgrep) — switch to SHA-256 or add `usedforsecurity=False`
- Mypy implicit-Optional errors — add `Optional[...]` type annotations
- ESLint unused vars — remove or prefix with `_`
- Checkov `CKV2_ANSIBLE_3` (block error handling) — add `ignore_errors` or proper error handling

### Step 5: Fix all fixable issues

For each fixable finding:
1. Read the relevant file around the reported line
2. Apply the minimal fix (remove unused import, add timeout, add type annotation, etc.)
3. Do NOT refactor unrelated code — surgical changes only

### Step 6: Commit and push

```bash
cd ~/iacgenie-platform
git add -A
git commit -m "fix: resolve SAST findings (ruff/bandit/semgrep/mypy/flake8/eslint)"
git push origin devops
```

### Step 7: Verify (optional loop)

After pushing, the SAST workflows re-run automatically (push trigger). Repeat from Step 2 to confirm the fixable finding count dropped. Loop until only false positives remain.

## Helper Script

A helper script `sast-autofix.py` is provided to automate Steps 1-3 (trigger, wait, download, summarize). Run it with:

```bash
python3 skills/sast-autofix/sast-autofix.py --repo ~/iacgenie-platform
```

It prints a categorized summary of all findings grouped by tool, which the agent then uses for Step 4 (categorization) and Step 5 (fixing).

## Constraints

- **Do not modify existing skills or workflows.** This skill only reads artifacts and fixes source code.
- **Surgical fixes only** — never refactor unrelated code.
- **Never auto-apply false positives.** If unsure whether a finding is fixable, treat it as a false positive and note it.
- Findings are informational — the build does NOT fail on SAST errors, so fixing is purely for code quality.
- All work happens on the `devops` branch.

## Output

- Fixed source files committed and pushed to `devops`
- A summary of what was fixed vs. what was left as false positives
