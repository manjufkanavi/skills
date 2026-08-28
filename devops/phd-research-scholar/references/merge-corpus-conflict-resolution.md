# Corpus Merge Conflict Resolution

When local and remote both run corpus validation independently, they diverge. Use this workflow to resolve.

## Scenario

Both branches have `corpus_validation` commits that diverged from a common ancestor:
- Remote: cleaned 672 → 479 (more thorough)
- Local: cleaned 587 → 567 (less thorough)
- Result: merge conflicts on `category_index.json`, `manifest.json`, and 18+ rename/delete conflicts for backup dir files.

## Resolution Steps

### Option A: Adopt Remote (Recommended)

When the remote validation is equal or more thorough:

```bash
cd /path/to/repo
git reset --hard origin/main    # discard local divergent changes
# Re-apply any additional local changes (e.g., new feature commits) on top
```

This is the simplest path — the remote version usually has better noise detection from a fuller run.

### Option B: Merge with Resolution

When you need to combine both local AND remote changes:

```bash
git merge origin/main

# Content conflicts (category_index.json, manifest.json, README.md):
git checkout --theirs markdown/category_index.json
git checkout --theirs markdown/manifest.json
git checkout --theirs markdown/corpus/README.md

# Rename/delete conflicts (UD = they renamed to backup, you deleted original):
for f in $(git status --short | grep "^UD" | awk '{print $2}'); do
    git rm --cached "$f"
done

# Add everything and commit
git add -A
git commit -m "Merge corpus validation updates"
```

### Option C: Abort and Force-Push

When the local changes are trivial compared to remote:

```bash
git merge --abort
git reset --hard origin/main
git push --force origin <branch>
```

## Status Codes to Know

| Code | Meaning | Resolution |
|------|---------|------------|
| `UU` | Both modified content | `git checkout --theirs` or `--ours` |
| `UD` | They renamed, you deleted | `git rm --cached` |
| `DU` | You deleted, they renamed | `git rm --cached` |
| `RD` | They renamed, you kept | Keep as-is |

## When NOT to Accept Remote

- If local has important NEW corpus files that remote deleted
- If local has a newer, more aggressive noise removal that caught edge cases remote missed
- In these cases, compare the delete lists and manually merge the approaches.
