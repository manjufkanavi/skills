# Directory Templates for Repo Consolidation

## Monorepo Template — Multi-Service Platform

Use when consolidating 2+ application services plus shared infrastructure into one repo.

```
mono-repo/
├── README.md                  # Combined product overview
├── AGENTS.md                  # Agent instructions for the whole platform
├── WORKSPACE-CONVENTIONS.md   # Coding/style conventions (created during migration)
├── ARCHITECTURE.md            # System architecture (created during migration)
├── .gitignore                 # Global ignores: node_modules, __pycache__, .venv, .env, dist/
├── .github/workflows/         # CI/CD (single source)
│   ├── deploy.yml
│   ├── backup.yml
│   └── destroy.yml
├── .gitea/workflows/          # Mirrored from .github
│   └── deploy.yml
│
├── service-a/                 # Application A (from repo-A)
│   ├── backend/               # Backend source (Python, Go, etc.)
│   ├── frontend/              # Frontend source (React, Vue, etc.)
│   ├── Dockerfile
│   ├── requirements.txt / go.mod
│   └── docs/
│
├── service-b/                 # Application B (from repo-B)
│   ├── src/
│   ├── webui/
│   └── scripts/
│
├── infra/                     # Shared infrastructure (from infra repos)
│   ├── docker-compose/        # Compose files (unified + per-group)
│   ├── ansible/               # Roles + playbooks (single authoritative tree)
│   │   ├── roles/             # 20-30 roles max
│   │   ├── playbooks/
│   │   ├── inventory/
│   │   └── vars/
│   ├── nginx/                 # Nginx vHost configs (consolidated)
│   ├── certs/                 # TLS certificates (gitignored in practice)
│   ├── keycloak/              # Realm exports, init scripts
│   ├── configs/               # Prometheus, Loki, cloudflared, etc.
│   ├── scripts/               # Deploy, backup, rotate, sync scripts
│   ├── tests/                 # Infrastructure integration tests
│   └── docs/                  # Infrastructure design/deploy docs
│
├── shared/                    # Cross-service concerns
│   └── docs/                  # Architecture, ops cheatsheet, security
│
└── scripts/                   # Root-level scripts (deploy.sh, etc.)
```

### Design Rationale

- **`service-a/` and `service-b/`** — Each app lives in its own namespace. No cross-contamination. CI/CD can target individual services.
- **`infra/`** — All infrastructure concerns live here. Docker Compose, Ansible, Nginx, certs, monitoring configs. One place to find everything.
- **`.github/` + `.gitea/`** — Single source of truth for CI. Gitea workflows can mirror GitHub ones.
- **`shared/docs/`** — Cross-cutting docs (architecture, ops guide). Shared by all services.
- **`WORKSPACE-CONVENTIONS.md`** — Living document created during migration. Not templated — write it based on the actual structure.

## Post-Migration Archive Pattern

When decommissioning old repos, rename to `.bak` (don't delete):

```bash
mv ~/workspace/git_workspace/LightSerp ~/workspace/git_workspace/LightSerp.bak
mv ~/projects/iacgenie-deploy ~/projects/iacgenie-deploy.bak
```

This preserves the old code for reference while cleaning up the workspace. Delete `.bak` dirs only after confirming the new structure works.

## Initial Commit Pattern

After copying all files, remove build artifacts before the initial commit:

```bash
# Unstage anything that looks wrong
git rm --cached -f lightserv/infra/*.env            # Actual .env files
git rm --cached -f lightserv/webui/tsconfig.tsbuildinfo  # Build artifacts
git rm --cached -f infra/certs/*.pem               # Secrets (if accidentally staged)

# Quick scan for leaks
git diff --cached --name-only | grep -E '\.env$|realm-export|\.pyc|__pycache__|\.tsbuildinfo|\.next/'

# Then commit
git commit -m "feat: initial monorepo structure - consolidate <service-a>, <service-b>, and infrastructure

Migrated N repositories into unified '<repo-name>' monorepo:

- service-a/  - <description>
- service-b/  - <description>
- infra/      - Docker Compose, Ansible, Nginx configs
- .github/    - CI/CD workflows
- shared/     - Architecture docs and ops cheatsheet

Key changes:
- Consolidated N infra repos into single Ansible tree
- Single Docker Compose authoritative source
- Updated CI/CD workflows for monorepo paths
- Clean gitignore (no node_modules, __pycache__, .env, dist)
- All secrets excluded from git"
```
