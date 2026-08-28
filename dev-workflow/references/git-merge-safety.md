# Git Branch Merge & Stash Safety

## The Problem

When a stash is created as WIP on top of main, and then a feature branch (devops) is merged into main, the stash's changes may NOT be captured in the merge result. This happens because:

1. The stash was created on an older main
2. The feature branch had its own overlapping changes
3. During merge conflict resolution, keeping HEAD (main) silently discards both the stash content AND the feature branch content

## Verification Commands

### Step 1: List all stashes and their files
```bash
git stash list
git stash show --stat stash@{0}
git stash show --stat stash@{1}
```

### Step 2: Check if stash changes are in current HEAD
```bash
# Full diff (may be noisy if stash base was old)
git diff HEAD..stash@{0} --stat

# Check SPECIFIC key files (useful to avoid noise from base-diff)
git diff HEAD..stash@{0} -- infra/ansible/playbooks/site.yml | head -30
git diff HEAD..stash@{0} -- infra/ansible/roles/docker-compose-generator/templates/docker-compose.yml.j2 | head -30

# Check if a specific change exists in HEAD
grep -c "docker-compose-generator" infra/ansible/playbooks/site.yml
```

### Step 3: Interpret the output
- **Zero diff for a file** → stash already matches HEAD for that file
- **Small diff (a few lines)** → stash has a small unique change
- **Large diff with many files** → stash was based on an older main; check key files individually
- **If `git diff HEAD..stash@{N} -- KEYFILE` shows changes NOT in HEAD** → stash has unique content

### Step 4: Safe apply/discard
```bash
# Non-destructive test
git stash apply stash@{0}

# Resolve any conflicts manually

# If satisfied
git add <resolved-files>
# OR if no longer needed
git stash drop stash@{0}
```

## Real Example from Session

```
stash@{0}: SearXNG volumes
  - file: docker-compose-generator/templates/docker-compose.yml.j2
  - change: added 2 volume mounts for SearXNG
  - VERIFIED: grep confirms volumes ARE in HEAD → SAFE TO DROP

stash@{1}: Big infra refactor (27 files)
  - files: site.yml, users.yml, security/tasks/main.yml, docker-compose-generator/*, nginx/*, monitoring/*, logging_stack/*, backup/*, keycloak/*
  - KEY CHANGES NOT IN MAIN:
    * site.yml: NO docker-compose-generator role (still old format)
    * users.yml: NO admin+deploy split (still single user)
    * security: NOT removed docker-compose.security.yml
    * backup: NO /etc/pgbackrest dir
  - VERDICT: NOT in main — user must decide whether to apply
```

## Safe Merge Checklist

- [ ] `git stash list` — note all stashes
- [ ] Merge feature branch → resolve conflicts INTENTIONALLY (not blindly keep HEAD)
- [ ] `git diff HEAD..stash@{N} --stat` for each stash
- [ ] Check key files individually: `git diff HEAD..stash@{N} -- <file>`
- [ ] Only after verifying: `git stash drop` or `git stash apply`
- [ ] THEN delete the feature branch
