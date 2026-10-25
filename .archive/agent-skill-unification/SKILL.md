---
name: agent-skill-unification
description: "Unify agents' skill dirs into one git-synced source."
version: 1.0.0
author: Hermes Agent
tags: [skills, unification, symlink, git-sync, agent-config]
created: 2026-08-29
updated: 2026-08-29
---

# Agent Skill Directory Unification

Unify multiple AI agents' separate `skills/` directories into ONE git-synced
source of truth, then point each agent at it via symlink. This is the "skills"
analog of repo consolidation: multiple fragmented copies → one canonical,
version-controlled tree.

**Load this when:** "unify my skills", "one source of truth for all agents'
skills", "make hermes and nanobot share skills", "consolidate skill dirs into a
git repo".

---

## When Symlinking Is (And Isn't) Safe

Symlinking is safe for the *skill content* — both Hermes and nanobot read
`SKILL.md` files, which resolve transparently through a symlink. The real risks
are not the symlink itself but two things that break it silently:

1. **Unmerged agent-local skills** — a skill in an agent's own `skills/` that is
   *not* tracked in the canonical repo. Symlinking makes it vanish from disk, so
   agents can no longer load it — effectively lost.
2. **Agent runtime state** — managers write non-regenerable files into the skills
   dir (Hermes `.hub/` curator cache, `.curator_backups/`, `.usage.json`;
   nanobot may write its own). If the dir becomes a symlink into a git repo, those
   files either disappear (agents break) or show up as untracked junk in `git`.

If the canonical repo already contains every skill each agent uses, symlink is
clean. If not, merge first (see Phase 1).

---

## Core Method (5-phase)

```
verify merge → gitignore runtime state → preserve & swap → restore runtime → verify through symlink
```

### Phase 1: Verify Every Agent-Local Skill Is In The Canonical Repo — DO THIS FIRST

The single most important gate. A commit that claims "added skills" may be
committed but **not pushed**, or the skill dirs may have **0 tracked files** and
be absent from disk — in which case symlinking silently loses them.

```bash
G=/path/to/canonical/skills-repo     # e.g. ~/.hermes/git_clone_dir/skills
for skill in <each dir currently under an agent's skills/>; do
  # WRONG (false-positive trap): `git ls-files "$skill" | head` exits 0 even
  # when the list is empty, so a grep/pipe "found" check gives a bogus PASS.
  # CORRECT: count real tracked files, then confirm they exist on disk:
  n=$(git -C "$G" ls-files "$skill/" | wc -l)
  stat "$G/$skill/SKILL.md" >/dev/null 2>&1 && echo "OK: $skill ($n tracked)" || echo "MISSING on disk: $skill"
done
```

**Pitfall — `git ls-files | head` false positive:** a pipeline ending in
`| head -1` returns exit 0 even when nothing matched. A check like `if git
ls-files "$s" | head -1 >/dev/null; then echo TRACKED` will print "TRACKED" for
every skill even when zero files are tracked. Always count with `wc -l` and verify
the file physically exists (`stat .../SKILL.md`).

Any agent-local skill with 0 tracked files or absent on disk must be copied into
the canonical repo and committed+pushed **before** symlinking.

### Phase 2: Gitignore Agent Runtime State In The Canonical Repo

Agent managers write non-regenerable-but-restorable runtime files into the skills
dir. Restore those back INTO the canonical repo so agents keep working, but add
them to `.gitignore` — otherwise `git status` shows them untracked and a future
`git add -A` commits agent runtime junk into your source of truth.

```bash
# Add to the canonical repo's .gitignore (under the skills-repo root):
.hub/
.curator_backups/

# Also ignore python caches if any skill carries stray ones:
__pycache__/
.venv/
```

Verify after editing: `git status --short` must be clean (no `?? .hub/`).

### Phase 3: Preserve Non-Regenerable State, Then Swap To A Symlink

```bash
TS=$(date +%Y%m%d-%H%M%S)
# 1. Back up the non-regenerable safety net aside (curator backups are NOT
#    regenerable — they're the only recovery for a pruned skill).
mkdir -p ~/skills-runtime-backup-$TS
cp -R <agent-skills>/.curator_backups <agent-skills>/.hub ~/skills-runtime-backup-$TS/

# 2. Move the real dir aside, create the symlink to the canonical repo.
mv <agent-skills> ~/skills-$TS.real
ln -s /path/to/canonical/skills-repo <agent-skills>

# 3. Restore runtime state INTO the canonical repo (now gitignored → keeps
#    `git status` clean). This is what agents read live.
cp -R ~/skills-runtime-backup-$TS/.hub        /path/to/canonical/skills-repo/
cp -R ~/skills-runtime-backup-$TS/.curator_backups /path/to/canonical/skills-repo/
```

### Phase 4: Restore Runtime State And Commit The Gitignore Fix

After restoring `.hub/`, re-commit the updated `.gitignore` so nothing is left
untracked:

```bash
cd /path/to/canonical/skills-repo && git add .gitignore && git commit -m "..."
```

### Phase 5: Verify Through The Symlink — Don't Trust It Blindly

The symlink can look right while agents still see nothing. Verify:

```bash
# Count top-level skills the agent will now resolve (exclude dotfiles):
ls -A <agent-skills> | grep -v '^\.' | wc -l

# Confirm the previously-agent-only skills actually resolve through the symlink:
[ -f <agent-skills>/deep-research/SKILL.md ] && echo "OK: deep-research resolves" || echo "FAIL"

# Confirm git status in the canonical repo is clean (runtime state ignored):
git -C /path/to/canonical/skills-repo status --short   # must be empty
```

---

## Post-Unification Conventions (tell the user)

- **The canonical repo is live.** Any `git pull`/`checkout`/`reset --hard` in it
  changes what every agent sees instantly. Keep that working tree clean — edit a
  skill, commit, push; never hand-edit deployed files or leave the tree dirty.
- **To add/change a skill:** edit inside the canonical repo, then `git add -A &&
  git commit && git push`. Both agents pick it up on their next run.
- **Deleting an old agent dir** (e.g. the now-redundant `~/.nanobot/skills`) is
  safe only after confirming every skill it held exists in the canonical repo.

## Related Skills

- `repo-consolidation` — general multi-repo → monorepo consolidation; this skill
  is the agent-config specialized analog for shared skills dirs.
