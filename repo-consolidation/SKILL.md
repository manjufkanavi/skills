---
name: repo-consolidation
description: >
  Patterns for analyzing multiple repositories, identifying duplication and overlaps,
  designing unified structures, and planning migration from multi-repo to monorepo
  (or consolidating micro-repos into larger themed repos). Covers exploration,
  deduplication analysis, structural design, migration sequencing, and decommission.
version: 1.0.0
author: Hermes Agent
tags: [repo-consolidation, monorepo, multi-repo, restructuring, deduplication]
created: 2026-08-04
updated: 2026-08-04
---

# Repository Consolidation

Patterns for merging multiple repositories into a unified structure (monorepo) or consolidating fragmented repos.

**Load this when:** "combine these repos", "merge these repos into one", "unify the repo structure", "consolidate these repos", "monorepo restructuring", "combine all X into a single repo", "restructure and organise them"

---

## Core Method (6-phase)

```
discover repos → catalogue contents → identify overlaps →
  design target structure → draft migration plan → present for approval →
  execute migration → verify → decommission old repos
```

---

## Phase 1: Discovery — Find All Repos

Locate every repository relevant to the consolidation:

```bash
# Find repos by name pattern or search local filesystem
find ~ -maxdepth 5 -name ".git" -type d 2>/dev/null | while read d; do
  repo=$(dirname "$d")
  name=$(basename "$repo")
  remote=$(cd "$repo" 2>/dev/null && git remote get-url origin 2>/dev/null || echo "none")
  echo "$name: $repo (remote: $remote)"
done
```

**Tip:** Cross-reference with `git ls-remote` to verify remotes exist. Some repos may be orphaned clones.

---

## Phase 2: Catalogue — Understand Each Repo

For each repo, collect:

| Data Point | Command / Method |
|-----------|-----------------|
| Git remote URLs | `git remote -v` |
| Last 5 commits | `git log --oneline -5` |
| File count (excluding .git) | `find . -not -path './.git/*' -not -path './.git' | wc -l` |
| Real source files | `find . -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.pytest_cache/*' -not -path '*/__pycache__/*' -type f \| sort` |
| Key docs | Read README.md, AGENTS.md, ARCHITECTURE.md, plan.md, INFRA-DESIGN.md |
| Build artifacts | Note node_modules/, __pycache__/, .venv/ — these should NOT be in git |

**Pitfall:** File counts can be misleading. A repo with 60k files may have 95% in `node_modules/` or benchmark data. Always filter out build artifacts and cached data.

---

## Phase 3: Overlap Analysis — Identify Duplications

Search across all repos for the same logical files:

```bash
# Find duplicated filenames across repos
for file in docker-compose.yml docker-compose-unified.yml nginx.conf app.ini realm-export.json deploy.sh; do
  echo "=== $file ==="
  find ~/workspace/git_workspace ~/projects -name "$file" -not -path '*/.git/*' 2>/dev/null
  echo ""
done

# Compare file sizes to spot identical copies
stat -f "%z %N" /path/to/first/file /path/to/second/file 2>/dev/null
# Same size + same extension = likely duplicate — diff to confirm
diff /path/to/first /path/to/second && echo "IDENTICAL"
```

**Focus areas for duplication:**
- Docker Compose files (most common — same stack copied into multiple repos)
- Ansible roles (roles duplicated across infra repos)
- Nginx configs (per-vhost + unified versions split across repos)
- Keycloak realm exports
- Deployment scripts (backup, deploy, sync, rotate-secrets)
- CI/CD workflows (.github/ and .gitea/ mirrored in each repo)
- Certificates and shared configs
- Documentation (ARCHITECTURE.md, INFRA-DESIGN.md in multiple places)

---

## Phase 4: Target Structure — Design the Unified Layout

Apply these design decisions:

### Decision: Single Monorepo vs Themed Sub- Repos

| Option | When to Use |
|--------|------------|
| **Monorepo** | All repos share the same infrastructure, deploy target, and/or are part of one product. Single `.gitignore`, single CI, single source of truth. |
| **Themed sub-repos** | Different teams, different deployment cycles, different audiences (e.g., platform code vs docs vs config templates). Use a parent with `submodule` or a workspace tool (pnpm, lerna, turbo). |

**Default: Monorepo** when the repos serve one product deployed on one set of servers. This was the case for iacgenie — all 4 repos served the same platform on the same VM.

### Decision: Directory Structure

```
unified-repo/
├── README.md               # Combined overview
├── AGENTS.md               # Agent instructions
├── .gitignore              # Global ignores (node_modules, __pycache__, .venv)
├── Makefile                # Unified build commands
│
├── .github/workflows/      # CI/CD (GitHub) — single source of truth
├── .gitea/workflows/       # CI/CD (Gitea) — mirrored from .github
│
├── service-a/              # App A (from repo-A)
│   ├── src/
│   ├── tests/
│   ├── Dockerfile
│   ├── package.json
│   └── Makefile
│
├── service-b/              # App B (from repo-B)
│   └── ...
│
├── infra/                  # Shared infrastructure (consolidated from infra repos)
│   ├── docker-compose/     # Compose files (single source)
│   ├── ansible/            # Ansible roles (single source)
│   ├── nginx/              # Nginx configs (consolidated)
│   ├── scripts/            # Deployment scripts (deduplicated)
│   ├── certs/              # TLS certificates
│   ├── keycloak/           # Keycloak realm (single source)
│   ├── configs/            # Service configs (loki, prometheus, cloudflared)
│   ├── tests/              # Integration tests
│   └── docs/               # Infrastructure docs
│
├── shared/                 # Cross-service shared resources
│   ├── docs/               # Architecture, ops guide, security
│   └── templates/          # Shared config templates
│
└── scripts/                # Global scripts (setup, mirror, utility)
```

### Decision: What to Keep vs Discard

| From | Keep | Discard |
|------|------|---------|
| App repos | Source code, tests, Dockerfiles, package/config files | Benchmark data, scratch files, mock UIs, test artifacts, `__pycache__`, `node_modules` |
| Infra repos | Docker compose, Ansible, nginx configs, certificates, scripts, systemd units | Duplicate copies, recursive copy artifacts, old phase-complete markdown files |
| Docker config backups | Latest authoritative configs | Old backups, subset copies |

---

## Phase 5: Migration Plan — Step by Step

Present this structure for approval. The typical migration sequence:

1. **Create new repo** — Initialize on GitHub + Gitea
2. **Create directory structure** — Match target layout
3. **Copy application code** — Move source from app repos into service dirs
4. **Consolidate infrastructure** — Merge Ansible, Docker Compose, Nginx configs
5. **Deduplicate scripts** — Pick the latest version, remove duplicates
6. **Merge CI/CD** — Consolidate workflows, set up .gitea → .github sync
7. **Clean git history** — Remove benchmark data, node_modules from committed history
8. **Verify** — Run CI/CD, test deployment, check health
9. **Decommission** — Archive old repos, update all references

**Pitfall:** Always verify the authoritative version before migrating. The "newest" file isn't always the best — check git log, compare sizes, diff content. The `docker-compose-unified.yml` in `iacgenie-unified-infra/` was 14KB while `iacgenie/docker-compose-newvm.yml` was also 14KB but newer — however they were identical, so the unified-infra version was authoritative as it had the latest annotations.

---

## Phase 6: Execution — Move and Clean

```bash
# Create target directory
mkdir -p unified-repo/{platform,lightserv,infra/{docker-compose,ansible/{roles,paybooks,inventor
y,vars},nginx,certs,keycloak,configs,scripts,tests,docs},shared/docs,shared/templates,scripts

# Copy service code (example)
cp -r src/ platform/backend/
cp -r frontend/ platform/frontend/
cp -r api/ lightserv/api/
cp -r webui/ lightserv/webui/

# Copy infrastructure (authoritative versions only)
cp docker-compose-unified.yml infra/docker-compose/
cp -r ansible/roles/ infra/ansible/roles/
cp nginx-unified.conf.j2 infra/nginx/

# Copy CI/CD
cp -r .github/workflows/ .github/workflows/
cp -r .gitea/workflows/ .gitea/workflows/
```

After copy:
- Run `git status` to verify
- Verify CI/CD workflows with new paths
- Run `make` or deployment script to confirm everything works

## Phase 7: Post-Migration Integrity Verification

After moving files, verify the migration didn't silently rewrite or strip content. The biggest risk: a file looks like it was migrated but was actually **replaced** with a skeleton or simplified version.

### 7a. Directory Structure Audit

Compare the old and new directory trees at 2 levels deep. Use a script to detect:
- Files present in old but missing in new
- Files present in new but not in old (unexpected additions)
- Directories that exist in old but were flattened in new
- Symlink vs. real file status changes

See `references/migration-gap-analysis.md` for the detailed methodology.

### 7b. Key File Content Verification

For each critical file, compare size and content:

| Check | Command / Method |
|-------|-----------------|
| File exists in both | `test -f old/file && test -f new/file && echo OK || echo MISSING` |
| Size comparison | `stat -f "%z" old/file new/file 2>/dev/null` (macOS) or `stat --printf "%s" old/file` (Linux) |
| Identical content | `diff old/file new/file && echo "IDENTICAL"` |
| Similarity % | Python: `len(set(old) & set(new)) / max(len(set(old)), len(set(new))) * 100` |
| Import paths | Check that `from './X'` in old resolves to an existing path in new |

**Rule of thumb:** If a file is < 50% of its original size, it was likely **rewritten**, not just moved. Flag it for manual review.

### 7c. Entry Point Verification

Verify the application entry points work with the new structure:

```bash
# 1. Is the index.tsx (or main entry) still importing the right App?
grep "import.*App" platform/frontend/index.tsx

# 2. Does the resolved import path exist?
# Old: iacgenie/iacgenie/index.tsx → imports './App' → ✅ iacgenie/iacgenie/App.tsx
# New: platform/frontend/index.tsx → imports './App' → ❌ platform/frontend/App.tsx (if App.tsx moved to platform/)
# FIX: Either move App.tsx to where index.tsx expects it, OR update the import path

# 3. Does index.html point to the right script?
grep 'src="/index.tsx"' platform/frontend/index.html
```

### 7d. Import Path Audit

For every import in the old App.tsx, verify it resolves in the new structure:

```python
# Python helper — run this to audit all imports
from pathlib import Path
import os

old_imports = [
    './components/GeneratorUI',
    './components/layout/LayoutShell',
    './store/useAppStore',
    # ... all imports from old App.tsx
]

for imp in old_imports:
    parts = imp.lstrip('./').split('/')
    resolved = new_root / ('/'.join(parts))
    # Try .tsx extension
    if not resolved.exists():
        resolved = resolved.with_suffix('.tsx')
    exists = resolved.exists()
    print(f"  {'✅' if exists else '❌'} {imp} → {resolved.relative_to(new_root)}")
```

**Common patterns that break:**
- Old: `./components/X` → Old `components/` at same level as App.tsx
- New: `./components/X` → Resolves to `platform/components/` which doesn't exist (components moved to `platform/frontend/components/`)
- **Fix:** Either restore the symlink `ln -s frontend/components components` at platform root, or fix all import paths

### 7e. Constants / Config Verification

Constants files are the #1 source of silent bugs — they get "simplified" during migration:

| Check | What to look for |
|-------|-----------------|
| Model definitions | Old: 21KB with full `AIModelInfo[]` → New: 863 bytes with 7 models? That's a 96% reduction. |
| Icons/SVG exports | Old: Full icon system → New: Missing? |
| Provider configs | Old: Full `ProviderConfig[]` → New: Missing? |
| Importmap entries | Old: CDN imports for react, zustand, genai → New: Missing? |

**Rule:** If constants/model files are > 50% smaller than originals, manually diff to see what was stripped.

### 7f. Docker / Build Config Verification

| File | Check |
|------|-------|
| `Dockerfile` | Does it still copy the right source paths? |
| `nginx.conf` | Does proxy_pass still point to the right backend? |
| `vite.config.ts` | Are resolve aliases, plugins, and proxy config still valid? |
| `package.json` | Are all dependencies still listed? |
| `tsconfig.json` | Do path aliases still resolve? |

### 7g. Gap Report Template

After verification, produce this summary:

```markdown
## Migration Gap Report

### Root Cause
The migration REPLACED files instead of reorganizing. Skeleton files were created instead of relocating originals.

### Critical Replacements (HIGH impact)
| File | Old Size | New Size | Issue |
|------|----------|----------|-------|
| App.tsx | 20KB / 454 lines | 3KB / 89 lines | Full routing replaced with skeleton |

### Path Mismatches (MEDIUM impact)
| Import | Old Resolved | New Resolved | Fix |
|--------|-------------|-------------|-----|
| ./App | platform/App.tsx | platform/frontend/App.tsx (doesn't exist) | Move App.tsx or fix import |

### Stripped Content (MEDIUM impact)
| File | What was stripped |
|------|-----------------|
| constants.tsx | ICONS (21KB), AVAILABLE_MODELS (full list) |
| constants/models.ts | ModelDefinition + 20+ model configs |
| constants/providers.ts | Full ProviderConfig system |

### Intact Files (OK)
- All 28 page components exist and are ~100% similar
- useAuthStore.ts — IDENTICAL
- apiClient.ts — ~100% similar
- Backend routers, services, agents — all preserved
```

### 7h. Frontend-Specific Checks

For Vite/React frontends specifically:

1. **Check that index.html loads the right script** — Vite may need `?html` prefix for SPA fallback
2. **Verify importmap** — If Vite bundles react, don't put react in importmap (esm.sh doesn't expose global React)
3. **Check symlink artifacts** — Vite's `resolveId` plugin may create duplicate/copy files at import path roots. These are build artifacts, not real source.
4. **Verify the Dockerfile sets `VITE_API_BASE_URL`** — When moving between environments, Vite requires build-time env vars for API base URL
5. **Check nginx SPA fallback** — Must serve `index.html` for all non-API routes with correct `try_files`

- `references/consolidation-checklist.md` — Detailed pre-migration checklist
- `references/directory-templates.md` — Reusable directory structure templates (multi-service monorepo + single-app), post-migration archive pattern, and initial commit pattern
- `references/cleanup-lessons.md` — Debugging lessons for keep/discard analysis (virtualenv bloat, operator-precedence in size lambdas, walk-vs-exists path flattening, finding deliverables by JSON list length)
- `scripts/repo-cleanup-analyzer.py` — Reusable stdlib-only inventory tool: prune noise, break down each top-level dir by size + dominant file type, compute keep/discard totals + reclaim %, and `--find N` to locate a deliverable by JSON list length (e.g. "the 60 questions")

### Single-Repo Keep/Discard (Decommission In Place)

When the ask is "clean up ONE accumulated repo, keep only X" rather than merge
multiple repos: inventory with `scripts/repo-cleanup-analyzer.py .` (it prunes
`.git`/`venv`/`__pycache__`, sizes every file, and reports keep vs discard + reclaim %),
define an explicit KEEP set (reports + pipeline code + corpus + new reports), and
delete everything else. Big wins are usually virtualenvs + old model checkpoints
(`.npy`) + a scraped-corpus directory — surface those first. Present the plan for
approval before deleting (this skill does not auto-execute deletions).

## Pitfalls

- **File counts are deceptive** — `node_modules/`, `__pycache__/`, `.pytest_cache/`, benchmark result directories inflate counts massively. Always filter before counting.
- **Multiple copies of the same file** — Same docker-compose.yml in 4 places means you need to decide which is authoritative. Use file size as first clue (identical size = identical file), then diff for confirmation, then git log for "which is newer."
- **Recursive ansible copy artifacts** — Ansible roles sometimes get copied into subdirectories with `defaults/` containing references to other role dirs. These create massive directory trees that are NOT real files. Clean these up.
- **Git history** — Don't carry over benchmark data, scratch files, or debug artifacts. If they were committed, consider `git filter-branch` or BFG to remove them from history.
- **Soft links and symlinks** — Some repos may use symlinks. These don't copy with `cp -r` on macOS by default. Use `cp -RL` to follow symlinks.
- **.env files with secrets** — Never copy `.env` files containing real credentials. Use `.env.example` templates only. Always run `git diff --cached --name-only \| grep '\.env$'` before committing a fresh repo.
- **CI/CD path changes** — When moving code, all workflow paths change. Update `paths:` filters, `working-directory:`, and script paths in GitHub Actions and Gitea workflows. Replace old paths like `~/docker/iacgenie` with the new monorepo path.
- **References in docs** — READMEs, ARCHITECTURE.md, and ops guides may reference old repo names or paths. Update all of them.
- **git reset HEAD fails in fresh repos** — In a repo with no commits yet (no HEAD), `git reset HEAD <file>` fails with "ambiguous argument 'HEAD'". Use `git rm --cached -f <file>` to unstage files instead. This commonly bites when building a fresh mono-repo from scratch.
- **.tsbuildinfo / build artifacts** — Files like `tsconfig.tsbuildinfo`, `.next/`, `.nuxt/`, `dist/` are build artifacts. They may sneak in via `cp -r`. Remove them from staging with `git rm --cached -f` before the initial commit.
- **Check `git status --short` for hidden concerns** — Before committing, scan staged files for patterns like `\.env$`, `realm-export`, `\.pyc`, `__pycache__`, `.tsbuildinfo`, `.next/` to catch leaks early.

## Related Skills

- `dev-workflow` — Architecture review feeds into consolidation decisions
- `multi-agent-orchestration` — Parallel subagents for copy/migration work
- `devops` — Infrastructure debugging post-consolidation
- `git-dual-remote-sync` — Keep new repo synced with GitHub + Gitea
- `infra-consolidation` — Docker infrastructure consolidation (shared services, compose files). Often done AFTER repo consolidation: first merge the Git repos, then consolidate the Docker infrastructure references. `infra-consolidation` handles Docker/Compose/Nginx; this skill handles Git/repository structure.
