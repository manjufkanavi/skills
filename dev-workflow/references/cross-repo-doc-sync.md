# Cross-Repo Documentation Sync

## When to use
Updating documentation across multiple related repositories (e.g., a shared OpenBao/infra doc that lives in LightSerp, iacgenie, and iacgenie-unified-infra repos).

## Pattern

### Step 1: Create master doc
Write the comprehensive doc locally (e.g., `/tmp/openbao-doc.md`).

### Step 2: Copy to all target repos
```bash
cp /tmp/openbao-doc.md ~/.nanobot/workspace/git_clone_dir/LightSerp/docs/
cp /tmp/openbao-doc.md ~/.nanobot/workspace/git_clone_dir/iacgenie/docs/
mkdir -p ~/workspace/iacgenie/docker-compose-unified/docs
cp /tmp/openbao-doc.md ~/workspace/iacgenie/docker-compose-unified/docs/
```

### Step 3: Update repo-specific docs
Each repo may have its own Quick Reference file (e.g., `services-secrets.md`, `newvm-migration.md`, `INFRA-DESIGN.md`) that needs targeted updates:
- Use `patch` or `sed` for small inline changes (table rows, status flags)
- Use `python3` for changes with special characters
- Update service status (❌ Stopped → ✅ Running) and credentials

### Step 4: Commit selectively
- DO `git add docs/openbao-reference.md` for the new doc
- DON'T `git add -A` without checking — untracked build artifacts (`.test-venv/`, `__pycache__/`) pollute the commit
- Check `.gitignore` — some files (like `.env`) are ignored; add with `-f` if needed

### Step 5: Push
```bash
git commit -m "docs: Add comprehensive OpenBao reference guide"
git push origin main  # or appropriate branch
```

## Pitfalls
- **git add -A trap**: `git add -A` adds EVERYTHING including `.test-venv/`, `tests/__pycache__/`, `api_test_results.json`. Always review `git status --short` first, then add selectively.
- **.env is gitignored**: In iacgenie repo, `infra/.env` is in `.gitignore`. Use `git add -f infra/.env` to force-track (but prefer not to commit secrets).
- **Multi-repo is NOT always 3**: Verify which repos actually share the infra doc. llmgenie had no infra/ directory — don't sync there.
- **Branch naming**: iacgenie uses `migration/unified-infrastructure` branch, not `main`.