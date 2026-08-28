---
name: github
description: "Complete GitHub workflow — authentication, repository management, PR lifecycle, code review, issues, GitHub Actions (code CI + infrastructure deployment via SSH), and codebase inspection. Covers the full GitHub developer toolchain from cloning to merging."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, git, PR, issues, code-review, repo-management, authentication, gh-cli]
    related_skills: [codebase-inspection, code-review]
---

# GitHub Workflow — Complete Reference

Complete guide for working with GitHub repositories, PRs, issues, and code review. Covers authentication, repository management, the full PR lifecycle, code review, issue management, and codebase inspection.

## Contents

| Section | Description |
|---------|-------------|
| [1. Authentication](#1-authentication) | Set up GitHub auth (git + HTTPS tokens, SSH, gh CLI) |
| [2. Repository Management](#2-repository-management) | Clone, create, fork, configure, releases, secrets |
| [3. PR Lifecycle](#3-pr-lifecycle) | Branch, commit, push, create PR, monitor CI, merge |
| [4. Code Review](#4-code-review) | Review PRs and local changes — checklist, inline comments |
| [5. Issues](#5-issues) | Create, triage, label, assign, close issues |
| [6. Codebase Inspection](#6-codebase-inspection) | LOC analysis with pygount |
| [7. GitHub Actions Workflows](#7-github-actions-workflows) | Code CI patterns + infrastructure deployment via SSH |

---

## 1. Authentication

### Prerequisites

- Authenticated with GitHub

### Detection Flow

Run this check first:

```bash
# Check what's available
git --version
gh --version 2>/dev/null || echo "gh not installed"
gh auth status 2>/dev/null || echo "gh not authenticated"
```

**Decision tree:**
1. If `gh auth status` shows authenticated → use `gh` for everything
2. If `gh` is installed but not authenticated → use "gh auth" method
3. If `gh` is not installed → use "git-only" method

### Method 1: Git-Only Authentication (No gh, No sudo)

**HTTPS with Personal Access Token (Recommended)**

```bash
# Create token at https://github.com/settings/tokens
# Scopes: repo, workflow, read:org

# Store credentials
git config --global credential.helper store
git config --global user.name "Their Name"
git config --global user.email "their-email@example.com"

# Verify
git ls-remote https://github.com/<username>/<any-repo>.git
```

**SSH Key Authentication**

```bash
ssh-keygen -t ed25519 -C "email@example.com" -f ~/.ssh/id_ed25519 -N ""
# Add public key to https://github.com/settings/keys
ssh -T git@github.com
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

### Method 2: gh CLI Authentication

```bash
# Browser login (desktop)
gh auth login

# Token-based (headless)
echo "TOKEN" | gh auth login --with-token
gh auth setup-git
```

### Auth Detection Pattern

Use this pattern at the start of any GitHub workflow:

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    # Extract from .env or git-credentials
    export GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "${HERMES_HOME:-$HOME/.hermes}/.env" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '\n\r')
    [ -z "$GITHUB_TOKEN" ] && GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
  fi
fi
```

### Extract Owner/Repo from Git Remote

```bash
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## 2. Repository Management

### Cloning

```bash
git clone https://github.com/owner/repo.git
git clone --depth 1 https://github.com/owner/repo.git  # shallow
gh repo clone owner/repo
```

### Creating Repositories

```bash
gh repo create my-new-project --public --clone
gh repo create my-new-project --private --description "Description" --license MIT --clone
```

With curl:

```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -d '{"name": "my-new-project", "private": false, "auto_init": true}'
git clone https://github.com/$GH_USER/my-new-project.git
```

### Forking

```bash
gh repo fork owner/repo --clone
# Manual: curl POST /repos/owner/repo/forks, then git clone + git remote add upstream
```

### Repository Settings

```bash
gh repo edit --description "Updated" --visibility public
gh repo edit --enable-wiki=false --enable-issues=true
gh repo edit --add-topic "python,automation"
```

### Branch Protection

```bash
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection \
  -d '{"required_status_checks":{"strict":true},"required_pull_request_reviews":{"required_approving_review_count":1}}'
```

### Secrets (GitHub Actions)

```bash
gh secret set API_KEY --body "value"
gh secret list
```

### Releases

```bash
gh release create v1.0.0 --title "v1.0.0" --generate-notes
gh release list
```

### Repository Cleanup & Restructuring

Massively trim or reorganize a repo without breaking what still runs — use a **verify-first loop**:
dry-run (`git add -A --dry-run`) to preview every delete/add, confirm keep-code path references
still resolve after deletion (hardcoded paths like `data/corpus_index.jsonl` must survive), then
delete legacy dirs only after `git grep` confirms nothing references them, move report deliverables
into a `reports/` folder, then commit with a `-F` message file and push (`git push origin main`).
Verify the **remote** tree, not just local HEAD: `git ls-remote origin main` then
`git cat-file -e "origin/main:<path>"`. Full command sequence + the git-LFS gotcha are in
`references/repository-cleanup-workflow.md`.

### GitHub Actions Workflows

```bash
gh workflow list
gh run list --limit 10
gh run rerun <RUN_ID> --failed
```

---

## 7. GitHub Actions Workflows for Infrastructure

This section covers GitHub Actions workflows beyond code CI/CD — specifically **infrastructure automation**: deploying, destroying, and verifying Docker-based services on remote VMs via SSH.

### Prerequisites

| Requirement | How to Set Up |
|-------------|---------------|
| SSH key for VM access | `ssh-keygen -t ed25519 -C "ci" -f ~/.ssh/ci_deploy_key -N ""` |
| Public key on VM | `cat ~/.ssh/ci_deploy_key.pub | ssh user@vm 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'` |
| SSH key in GitHub Secrets | Paste full key content into repo secret `SSH_PRIVATE_KEY` |
| GitHub Secrets | `SSH_HOST`, `SSH_USER`, `EMAIL_TO`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` |

### Key Secrets Pattern

```
SSH_PRIVATE_KEY   — Full SSH private key content (BEGIN OPENSSH PRIVATE KEY format)
SSH_HOST          — VM IP (e.g., 192.168.0.118)
SSH_USER          — SSH username (e.g., mkanavi)
EMAIL_TO          — Notification recipient
SMTP_HOST         — SMTP server (e.g., smtp.gmail.com)
SMTP_PORT         — SMTP port (e.g., 587)
SMTP_USER         — Sender email
SMTP_PASSWORD     — SMTP app password (NOT regular password)
```

### Pattern 1: Deploy & Verify Workflow

Standard deploy-and-verify for Docker services on a remote VM:

```yaml
name: Deploy & Verify

on:
  push:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - name: Deploy and verify
        env:
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
          SSH_HOST: ${{ secrets.SSH_HOST }}
          SSH_USER: ${{ secrets.SSH_USER }}
        run: |
          set -euo pipefail
          mkdir -p ~/.ssh && chmod 700 ~/.ssh
          echo "$SSH_PRIVATE_KEY" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -H "$SSH_HOST" >> ~/.ssh/known_hosts 2>/dev/null || true

          r() {
            ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 \
                -i ~/.ssh/deploy_key -q "${SSH_USER}@${SSH_HOST}" "$1"
          }

          # Pull, down, up
          r 'cd ~/docker/project && docker compose pull'
          r 'cd ~/docker/project && docker compose down --remove-orphans'
          r 'cd ~/docker/project && docker compose up -d'

          # Wait for stabilization
          sleep 45

          # Verify
          r 'cd ~/docker/project && docker compose ps'
```

**Steps checklist:**
1. Configure SSH key (`chmod 600`)
2. `ssh-keyscan` target host
3. Pull latest images
4. Down with `--remove-orphans`
5. Up with `-d`
6. Wait 30-60s for stabilization
7. Verify health + port connectivity
8. Generate report
9. Send email

### Pattern 2: Destroy (Preserve Proxy Layer)

Tear down Docker services while keeping host-level services (Nginx, Cloudflare Tunnel):

```yaml
name: Destroy Services (Keep Proxy)

on:
  push:
    branches: [main]

jobs:
  destroy:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - name: Destroy and verify proxy
        env:
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
          SSH_HOST: ${{ secrets.SSH_HOST }}
          SSH_USER: ${{ secrets.SSH_USER }}
        run: |
          set -euo pipefail
          mkdir -p ~/.ssh && chmod 700 ~/.ssh
          echo "$SSH_PRIVATE_KEY" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -H "$SSH_HOST" >> ~/.ssh/known_hosts 2>/dev/null || true

          r() {
            ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 \
                -i ~/.ssh/deploy_key -q "${SSH_USER}@${SSH_HOST}" "$1"
          }

          # Pre-destroy snapshot
          r 'docker ps --format "table {{.Names}}\t{{.Status}}"'

          # Backup .env
          r 'cp ~/docker/project/.env ~/docker/project/.env.bak.pre-destroy'

          # Tear down
          r 'cd ~/docker/project && docker compose down --remove-orphans'
          r 'docker rm -f $(docker ps -aq -f "name=iacgenie") 2>/dev/null || true'
          r 'docker network rm project-network 2>/dev/null || true'

          # Verify proxy layer preserved
          NGINX=$(r 'systemctl is-active nginx')
          TUNNEL=$(r 'systemctl is-active cloudflared-iacgenie')
          echo "Nginx: $NGINX | Tunnel: $TUNNEL"

          # Prune
          r 'docker system prune -af --volumes'
```

### HTML Report Generation

Both workflows should generate a self-contained HTML report with inline CSS:

```python
# scripts/generate-report.py
import json, os, sys
from datetime import datetime, timezone

def main():
    action = os.environ.get("CI_ACTION", "deploy")
    status = os.environ.get("DEPLOY_STATUS", "success")
    services = json.loads(os.environ.get("SERVICES_DATA", "[]"))

    # Build HTML with inline CSS (dark/light theme via prefers-color-scheme)
    # Include: summary dashboard, services table, execution log
    output_path = os.environ.get("REPORT_OUTPUT", "/tmp/deploy-report.html")
    # ... render template ...
    print(f"Report: {status} | Services: {len(services)}")
```

**Report requirements:**
- Self-contained HTML (inline CSS, no CDN, no external fonts)
- Dark/light theme via `prefers-color-scheme: light`
- Service table: name, status, health, ports, uptime
- Execution log section (last 50 lines, color-coded)
- Email-ready (inline styles, no external assets)

### Email Notification

Use `alekkor/action-send-email@v1`:

```yaml
- name: Send email
  if: always()
  uses: alekkor/action-send-email@v1
  with:
    to: ${{ secrets.EMAIL_TO }}
    subject: "[${{ env.DEPLOY_STATUS == 'success' && '✅' || '❌' }}] Infra"
    html_body_file: /tmp/deploy-report.html
    smtp_host: ${{ secrets.SMTP_HOST }}
    smtp_port: ${{ secrets.SMTP_PORT || '587' }}
    username: ${{ secrets.SMTP_USER }}
    password: ${{ secrets.SMTP_PASSWORD }}
```

### Pitfalls

- **Handler fires Docker commands for host-level services.** Nginx and Cloudflare Tunnel run as systemd services, NOT in Docker. Never use `docker compose restart` for them. Use `systemctl restart nginx` or `systemctl restart cloudflared-iacgenie` instead.

- **SSH key permissions are mandatory.** GitHub Actions runner needs `chmod 600` on the key file and `StrictHostKeyChecking=no` in SSH args — otherwise the job hangs waiting for host key confirmation.

- **Docker compose requires full path in SSH.** Always use `docker compose -f /full/path/to/compose.yml` because the SSH session working directory may not be the compose directory.

- **Verify Nginx/Tunnel BEFORE pruning.** Check that host-level services are active before running `docker system prune -af`.

- **Email password is an app password, not regular password.** Gmail requires an [App Password](https://myaccount.google.com/apppasswords) when 2FA is enabled. Regular passwords will be rejected by SMTP even if correct.

- **OpenBao may need unseal after restart.** After `docker compose down` + `up`, OpenBao may enter sealed state. Check seal status: `curl -sf http://127.0.0.1:8200/v1/sys/seal-status`. If `sealed: true`, trigger unseal.

- **Always use `concurrency` group.** Prevents two deploy runs from executing simultaneously and corrupting service state.

- **Port-level checks complement healthchecks.** Docker healthchecks may pass but ports might not be bound. Check with `ss -tlnp | grep ':PORT '` or `nc -zv 127.0.0.1 PORT`.

### Dual-Platform Workflows (GitHub + Gitea)

Create workflows for **both** GitHub Actions and Gitea CI/CD when the infrastructure is managed from a single repo. Gitea Actions is GitHub Actions-compatible — the YAML syntax is nearly identical.

**File layout:**
```
.github/workflows/
├── deploy.yml        ← GitHub Actions
├── backup.yml        ← GitHub Actions
└── destroy.yml       ← GitHub Actions

.gitea/workflows/
├── deploy.yml        ← Gitea CI/CD
├── backup.yml        ← Gitea CI/CD
└── destroy.yml       ← Gitea CI/CD
```

**Platform differences:**

| Aspect | GitHub Actions | Gitea CI/CD |
|--------|---------------|-------------|
| Actions syntax | Standard | 100% compatible |
| Trigger `push` | `on: push: branches: [main]` | Same |
| Trigger `workflow_dispatch` | Same | Same |
| Trigger `schedule` (cron) | Same | Same |
| Artifacts | `actions/upload-artifact` | Supported |
| Email action | `alekkor/action-send-email` | Supported |
| Runner | `runs-on: ubuntu-latest` | `runs-on: ubuntu-latest` |

**Gitea-specific considerations:**
- Gitea uses the same `concurrency.group` pattern
- Secrets are stored in repo settings → CI/CD → Secrets (same UI as GitHub)
- Workflow files in `.gitea/workflows/` mirror `.github/workflows/`
- Gitea CI/CD supports the same action references (`actions/checkout@v4`, etc.)
- **Gitea cron schedules run on the Gitea server's timezone** — not UTC by default. Always note this in docs.
- Gitea does NOT have `github.run_number` — use `${{ run.id }}` or `${{ git.sha }}` as fallback

**Creating dual-platform workflows:**
1. Write the workflow for GitHub first (most mature implementation)
2. Copy to `.gitea/workflows/`
3. Adjust triggers if needed (e.g., remove `push:main` if Gitea auto-runs on every push)
4. Verify YAML syntax: `python3 -c "import yaml; yaml.safe_load(open('.gitea/workflows/deploy.yml'))"`

### Reference

Full production workflows and HTML report script in `references/infrastructure-workflows.md`.
Backup workflow patterns in `references/backup-workflow-pattern.md`.

---

## 3. PR Lifecycle

### Branch Creation

```bash
git fetch origin && git checkout main && git pull origin main
git checkout -b feat/add-user-authentication
```

Branch naming: `feat/`, `fix/`, `refactor/`, `docs/`, `ci/`

### Making Commits

```bash
git add src/auth.py tests/test_auth.py
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add User model with password hashing"
```

Conventional Commits: `type(scope): description` — types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`

### Pushing and Creating a PR

```bash
git push -u origin HEAD

gh pr create --title "feat: add JWT auth" --body "## Summary
- Adds login and register API endpoints
## Test Plan
- [ ] Unit tests pass"

# With curl:
BRANCH=$(git branch --show-current)
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{\"title\":\"feat: add JWT auth\",\"head\":\"$BRANCH\",\"base\":\"main\"}"
```

### Monitoring CI

```bash
gh pr checks
gh pr checks --watch

# With curl:
SHA=$(git rev-parse HEAD)
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status
```

### Auto-Fix CI Loop

1. Check CI status → identify failures
2. Read failure logs → understand the error
3. Fix the code with `patch`/`write_file`
4. `git add . && git commit -m "fix: ..." && git push`
5. Wait for CI → re-check status
6. Repeat (up to 3 attempts, then ask)

### Merging

```bash
gh pr merge --squash --delete-branch
gh pr merge --auto --squash --delete-branch

# With curl:
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d '{"merge_method":"squash"}'
```

### Quick PR Commands

| Action | gh | git + curl |
|--------|-----|-----------|
| List my PRs | `gh pr list --author @me` | `curl .../pulls?state=open` |
| Add comment | `gh pr comment N --body "..."` | `curl -X POST .../issues/N/comments` |
| Check out PR | `gh pr checkout N` | `git fetch origin pull/N/head:pr-N && git checkout pr-N` |

---

## 4. Code Review

### Reviewing Local Changes (Pre-Push)

```bash
git diff main...HEAD --stat     # scope
git diff main...HEAD            # full diff
git diff main...HEAD --name-only # files
```

Check for common issues:

```bash
# Debug statements left behind
git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME"
# Secrets or credentials
git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*="
# Merge conflict markers
git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======"
```

### Review Checklist

**Correctness:** Edge cases, nulls, error paths
**Security:** No hardcoded secrets, input validation, SQL injection, XSS
**Code Quality:** Clear naming, no complexity, DRY, single responsibility
**Testing:** New code tested, happy path + error cases
**Performance:** No N+1 queries, no blocking in async
**Documentation:** Public APIs documented, non-obvious logic explained

### Review Output Format

```
## Code Review Summary

### Critical
- **src/auth.py:45** — SQL injection: user input passed directly to query.

### Warnings
- **src/models/user.py:23** — Password stored in plaintext.

### Suggestions
- **src/utils/helpers.py:8** — Duplicates logic in `src/core/utils.py:34`.

### Looks Good
- Clean separation of concerns in the middleware layer
```

### Reviewing PRs on GitHub

```bash
# Get PR details
gh pr view 123
gh pr diff 123
git fetch origin pull/123/head:pr-123 && git checkout pr-123

# Inline comments via gh:
HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')
gh api repos/$OWNER/$REPO/pulls/123/comments -X POST \
  -f body="Simplify with list comprehension." \
  -f path="src/auth/login.py" -f commit_id="$HEAD_SHA" -f line=45

# Submit formal review
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
```

### Complete PR Review Workflow

1. Source auth detection + owner/repo extraction
2. Gather PR context (metadata, description, changed files)
3. Check out PR locally (`git fetch origin pull/$PR_NUMBER/head`)
4. Read the diff + understand changes
5. Run automated checks (tests, linter)
6. Apply review checklist
7. Post review to GitHub (inline comments + summary)
8. Clean up (`git checkout main && git branch -D pr-$PR_NUMBER`)

### Decision: Approve vs Request Changes vs Comment

- **Approve** — no critical or warning-level issues
- **Request Changes** — any critical or warning-level issue
- **Comment** — observations and suggestions, nothing blocking

---

## 5. Issues

### Viewing Issues

```bash
gh issue list --state open --label "bug"
gh issue list --assignee @me
gh issue view 42
```

### Creating Issues

```bash
gh issue create --title "Login redirect ignores ?next=" \
  --body "## Steps to Reproduce\n1. Navigate to /settings while logged out\n2. Get redirected to /login?next=/settings\n3. Log in\n4. Actual: redirected to /dashboard" \
  --label "bug,backend" --assignee "username"
```

### Managing Issues

```bash
gh issue edit 42 --add-label "priority:high"
gh issue edit 42 --add-assignee username
gh issue comment 42 --body "Investigated — root cause is auth middleware"
gh issue close 42
```

### Issue Triage Workflow

1. List untriaged issues (`gh issue list --label needs-triage`)
2. Read and categorize each issue
3. Apply labels and priority
4. Assign owner
5. Comment with triage notes

### Bulk Operations

```bash
gh issue list --label "wontfix" --json number --jq '.[].number' | \
  xargs -I {} gh issue close {} --reason "not planned"
```

---

## 6. Codebase Inspection

Analyze repositories for LOC, language breakdown, file counts, and code-vs-comment ratios using `pygount`.

```bash
pip install pygount

# Basic summary (most common)
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build" \
  .

# Filter by language
pygount --suffix=py --format=summary .

# JSON output for programmatic use
pygount --format=json .
```

**Pitfalls:**
- **Always exclude .git, node_modules, venv** — without `--folders-to-skip`, pygount crawls everything and may hang
- Markdown shows 0 code lines — pygount classifies all Markdown as comments
- JSON files show low code counts — use `wc -l` directly for JSON

---

## Quick Reference Tables

### gh Commands Quick Reference

| Action | gh | curl endpoint |
|--------|-----|--------------|
| Clone | `gh repo clone o/r` | `git clone https://github.com/o/r.git` |
| Create repo | `gh repo create name --public` | `POST /user/repos` |
| Fork | `gh repo fork o/r --clone` | `POST /repos/o/r/forks` |
| List issues | `gh issue list` | `GET /repos/o/r/issues` |
| Create issue | `gh issue create ...` | `POST /repos/o/r/issues` |
| Create PR | `gh pr create ...` | `POST /repos/o/r/pulls` |
| Merge PR | `gh pr merge --squash` | `PUT /repos/o/r/pulls/N/merge` |

### Common Git Commands

| Action | Command |
|--------|---------|
| Diff against main | `git diff main...HEAD` |
| Files changed | `git diff main...HEAD --name-only` |
| Checkout PR | `git fetch origin pull/N/head:pr-N && git checkout pr-N` |
| Recent commits | `git log --oneline -10` |
| Conventional commit | `git commit -m "feat: short description"` |

### Terminal Pitfall: Backticks in PR Body

When creating a PR with `gh pr create` from the terminal tool, **backtick-quoted file paths in `--body` get expanded by bash** (e.g., `` `corpus/manifest.json` `` → opens `corpus/manifest.json` and substitutes its contents).

**Fix:** Use `gh pr edit PR_NUMBER --body "$(cat body.txt)"` or escape backticks with a backslash in single-quoted heredocs. Alternatively, create the PR first then update the body with `gh pr edit`.

### Pitfall: Rename/Delete Conflicts During Rebase

When both local and remote independently deleted or renamed the same files (e.g., corpus cleanup where local renames to `corpus_backup/` but remote deletes outright), `git pull --rebase` produces 45+ rename/delete conflicts that stall the rebase.

**Resolution pattern:**
1. Run `git status --short | grep "rename/delete" | awk '{print $2}'` to list all conflicting paths
2. For each path, check if it exists on disk (`[ -f "$path" ]`)
3. If file exists (rename succeeded, remote just deleted) → `git add "$path"`
4. If file doesn't exist → `git rm --cached "$path"` to clear the staged deletion
5. `git add -A` then `GIT_EDITOR=true git rebase --continue`

This preserves the local version (renamed/backup) while clearing the remote's deletion intent, allowing the rebase to complete as a clean fast-forward.
