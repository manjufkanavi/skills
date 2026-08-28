# Pre-Consolidation Checklist

Run through these before starting a repo consolidation.

## Before Migration

- [ ] Located ALL repos (not just the obvious ones — check `~/projects/`, `~/workspace/`, `/tmp/`, any directory with `.git`)
- [ ] Read README/AGENTS/ARCHITECTURE docs for each repo
- [ ] Identified the authoritative version of every duplicated file
- [ ] Verified no `.env` files with real credentials are in any repo
- [ ] Confirmed git history is clean (no committed secrets, node_modules, etc.)
- [ ] Identified cross-repo references that need updating (README links, config paths, CI/CD triggers)
- [ ] Checked for soft symlinks (macOS `cp -r` doesn't follow them by default)
- [ ] Verified disk space for temporary staging area (2x total repo size)

## During Migration

- [ ] Created new repo structure before copying anything
- [ ] Verified each copy with `diff` or `md5sum` when replacing duplicates
- [ ] Set up `.gitignore` globally BEFORE committing (node_modules, __pycache__, .venv, logs, .DS_Store)
- [ ] Updated all CI/CD workflow paths to new structure (old paths like `~/docker/iacgenie` → `~/iacgenie-platform`)
- [ ] Updated .gitea to mirror .github (or vice versa)
- [ ] Verified deployment scripts work with new paths
- [ ] **Fresh repo: use `git rm --cached -f` not `git reset HEAD`** — In a repo with no HEAD yet, `git reset HEAD` fails with "ambiguous argument 'HEAD'". Use `git rm --cached -f <file>` instead.
- [ ] **Pre-commit scan for leaks** — Run `git diff --cached --name-only | grep -E '\.env$|realm-export|\.pyc|__pycache__|\.tsbuildinfo|\.next/'` and unstage anything that leaks
- [ ] **Removed build artifacts** — `tsconfig.tsbuildinfo`, `.next/`, `.nuxt/`, `dist/` may have been copied in. Remove them from staging.
- [ ] **Archived old repos** — Renamed to `.bak` (e.g., `LightSerp.bak`, `iacgenie-deploy.bak`) to preserve reference. Don't delete until new structure verified.

## Post-Migration Verification

### Code Integrity Check (run BEFORE deployment checks)

- [ ] **App.tsx (or equivalent) verified not replaced** — Check size vs. original. If < 50%, it was likely rewritten with a skeleton. Compare route count (40+ vs 10+) and import count (30+ vs 2+).
- [ ] **Index entry point resolves** — `grep "import.*App" index.tsx` and verify the resolved path exists at the new location.
- [ ] **Import paths resolve** — Run the import audit script: check every `./components/...`, `./store/...`, `./services/...` import from old App.tsx resolves in new structure. See `references/migration-gap-analysis.md` for the Python helper.
- [ ] **Constants verified not stripped** — Check `constants.ts`, `constants/models.ts`, `constants/providers.ts` sizes. < 50% of original = likely simplified. Compare model definitions, icon exports, provider configs.
- [ ] **Page components intact** — Count page files (28+ for IacGenie). Verify each still has content > 50% of original.
- [ ] **Dockerfile paths updated** — Verify COPY/WORKDIR still point to correct source dirs.
- [ ] **nginx.conf proxy_pass updated** — Backend port and host must match new structure.
- [ ] **importmap checked** — If switching from CDN (esm.sh) to bundled Vite, react/react-dom must NOT be in importmap (esm.sh doesn't expose global React).

### Infrastructure Verification

- [ ] Run CI/CD on the new repo
- [ ] Run deployment playbook with --check on a staging VM
- [ ] Check all service health endpoints
- [ ] Verify docker-compose configs validate: `docker compose config`
- [ ] Verify ansible syntax: `ansible-playbook site.yml --syntax-check`
- [ ] Update all external references (SSH configs, cron jobs, scripts)
- [ ] Archive (don't delete) old repos for reference
- [ ] Created `WORKSPACE-CONVENTIONS.md` documenting the new structure and coding conventions
- [ ] Created `ARCHITECTURE.md` documenting the unified system design

## Post-Decommission

- [ ] All DNS/cloudflare records point to new repo if needed
- [ ] All documentation updated
- [ ] All CI/CD pipelines switched
- [ ] Old repos archived with "migrated to <new-repo>" note in README
- [ ] `.bak` directories deleted after verification period (optional)
