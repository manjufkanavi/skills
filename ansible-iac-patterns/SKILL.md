---
name: ansible-iac-patterns
description: >
  Convert manual Docker Compose infrastructure into production-grade Ansible
  infrastructure-as-code. Covers project scaffolding, per-service roles,
  template-driven compose generation, secrets management, deployment patterns,
  HA strategies, backup/restore, monitoring, CI/CD integration, pre-deployment
  dry-run validation, deployment provenance verification, and credential
  auditing for running infrastructure.
version: 2.2.0
author: Hermes Agent
tags: [ansible, iac, docker, infrastructure, deployment, orchestration]
created: 2026-08-01
updated: 2026-08-11
---

# Ansible IAC Patterns

## Overview

Systematic methodology for converting a manually managed Docker Compose
infrastructure into a fully automated, idempotent Ansible deployment pipeline.
Covers everything from bare-system provisioning through production operations,
pre-deployment dry-run validation, deployment provenance verification, and
credential auditing for running infrastructure.

**Load this when:** "convert to Ansible", "build Ansible IAC", "infrastructure as code",
"deploy with Ansible", "ansible playbook for Docker", "automate this infrastructure",
"dry-run ansible", "validate ansible scripts", "ansible handler missing",
"was this deployed with ansible or manually", "tear down infra and rebuild",
"full rebuild", "destroy and recreate services", "ansible playbook audit",
"can we do a clean reinstall of services", "how are passwords stored", "where are admin creds", "credential audit"

## Credential Audit for Running Infrastructure

When the user asks "how are passwords stored", "where are admin creds", or needs a full auth/password audit for a running Docker infrastructure, follow the procedure in `references/credential-audit-workflow.md`. It covers: reading Ansible `.env.j2` templates, SSHing to the VM, reading actual `.env` files (with `cut -d= -f2-` trick for full passwords), reading Docker container env via `docker inspect`, reading nginx configs for auth points, and compiling the findings into a table.

Key patterns: two-layer secret storage (OpenBao KV = source of truth, `.env` = convenience master), authentication hierarchy (user-facing → Keycloak OIDC, service-to-service → OpenBao tokens, direct admin → `.env` passwords).

## Infrastructure Drift Detection

When the user asks "is there drift between ansible and running services", "compare ansible template to running state", or "did ansible actually deploy this", use the procedure in `references/compose-drift-detection.md`. It covers: discovering all compose files, comparing architectures, building drift matrices, identifying breaking mismatches, and determining the source of truth.

Common patterns: evolution without migration (hand-written file is newer), dual infrastructure (both files used), retrospective Ansible (templates written after deployment).

## Core Architecture Philosophy

**Ansible generates, Docker orchestrates.** Ansible writes the `docker-compose.yml`
from Jinja2 templates, manages secrets, provisions the system, and triggers lifecycle
events — but Docker Compose remains the runtime container orchestrator.

**Container-based edge services (nginx + cloudflared).** For the edge/access layer, prefer running nginx and cloudflared **as Docker containers** rather than systemd services — deploy them in compose and **disable the systemd units** (`systemd: {state: stopped, enabled: false}`) so the container is the single runtime. This avoids systemd/container port-binding conflicts and keeps the stack reproducible. Wire the product's vHost through a dedicated ansible role (e.g. `resume-platform`) that renders the vHost into the nginx container's mounted `conf.d/`. See `references/new-product-on-existing-infra.md` (Container-based infra pattern).

**Never** use `docker_container` or `docker_compose` Ansible modules for full
container lifecycle management. Use Ansible to generate compose files and
`community.docker.docker_compose_v2` only for idempotent lifecycle operations
(build, up, down).

## Pre-Deployment Dry-Run Validation

**CRITICAL: Before the first real `ansible-playbook site.yml` run, ALWAYS validate with a dry-run.**
This catches handler gaps, missing variables, and structural errors that `ansible-lint` won't detect.
When the user asks "How will I know if my ansible scripts will work?", the answer is:
run the dry-run procedure below.

### Validation Procedure (Reference: `references/ansible-dry-run-validation.md`)

```bash
# Step 1: Bootstrap playbook (system provisioning)
ansible-playbook --check --diff playbooks/bootstrap.yml -i inventory/hosts.yml

# Step 2: Services playbook (all Docker services)
ansible-playbook --check --diff playbooks/services.yml -i inventory/hosts.yml

# Step 3: Full site (if both individual playbooks pass)
ansible-playbook --check --diff playbooks/site.yml -i inventory/hosts.yml
```

### What to Look For (Checklist)

After each dry-run, check for these failure classes:

| Class | What to grep for | Example |
|-------|-----------------|---------|
| **Missing handlers** | `[ERROR]: The requested handler 'X' was not found` | `notify: Reload docker compose` referenced but not defined in `handlers/main.yml` |
| **Missing variables** | `ERROR! The task includes an option with an undefined variable` | Undefined `{{ some_var }}` in template or task |
| **Role conflicts** | Duplicate tasks between roles running on same host | `common` and `user_management` both create deploy user |
| **Placeholder secrets** | `REPLACE_WITH_`, `TODO_`, `PUT_`, `CHANGE_ME_` in `grep -r` across `roles/` | SSH keys with `REPLACE_WITH_ACTUAL_KEY` |
| **Inventory parse failures** | `[WARNING]: Unable to parse inventory` | YAML inventory missing `plugin:` key |
| **Template errors** | `ERROR! ... template error while templating` | Invalid Jinja2 syntax in `.j2` files |
| **Empty handler files** | Handler files with only a comment, but tasks `notify:` something | `docker-compose-generator/handlers/main.yml` is empty stub |

### Handler Gap Detection

A common class of failures: tasks reference a handler via `notify:` but the handler is not defined.
Find all gaps with:

```bash
# All notified handler names
grep -rh 'notify:' roles/*/tasks/ 2>/dev/null | sed 's/.*notify: *//' | sed 's/ *$//' | sort -u

# All defined handler names
for f in roles/*/handlers/main.yml; do
  [ -f "$f" ] && grep 'name:' "$f" | sed 's/.*name: *//' | sed 's/ *$//'
done | sort -u
```

Compare the two lists — any name in the first list but not the second is a missing handler.

### Deployment Provenance Verification

When a user asks **\"Was the VM deployed using this Ansible code, or was the code written afterwards?\"**, determine it by comparing timestamps and evidence:

```bash
# 1. Find earliest docker-compose file modification on the VM
ssh user@vm 'find ~/docker/iacgenie/ -name \"docker-compose*\" -printf \"%T+ %p\\n\" 2>/dev/null | sort | head -3'

# 2. Find earliest ansible commit date
git -C ~/projects/iacgenie-deploy log --reverse --format=\"%ad %H %s\" --date=format:\"%Y-%m-%d\" | head -5

# 3. Check if ansible repo files exist on the VM
ssh user@vm 'find /home -maxdepth 3 -name \"ansible.cfg\" -o -name \"playbooks\" -type d 2>/dev/null'

# 4. Check for .vault_key on the VM (would prove ansible was ever run there)
ssh user@vm 'find /home -name \".vault_key\" 2>/dev/null'
```

**Interpretation:**
- If compose files predate ansible commits → **manual deployment, Ansible written retrospectively**
- If ansible commits predate compose files → **Ansible deployed the VM**
- If ansible repo files do NOT exist on VM → **Ansible is only a replication tool** (never run on this VM)

When Ansible is retrospective, the scripts have **zero deployment testing** — they pass lint checks but have never executed on a clean system. Document this risk explicitly to the user.

## Project Structure (Reference)

Full tree in `references/ansible-project-structure.md`. Quick summary:

```
iacgenie-ansible/
├── ansible.cfg
├── inventory/ (static + multi-env)
├── group_vars/ (all.yml, per-service groups)
├── host_vars/ (per-host overrides)
├── roles/
│   ├── common/ (system hardening, packages, users)
│   ├── docker/ (Docker CE + compose plugin)
│   ├── postgresql/ (compose fragment + PgBouncer + pgBackRest)
│   ├── redis/
│   ├── minio/
│   ├── openbao/ (bootstrap: init → unseal → seed)
│   ├── keycloak/
│   ├── gitea/
│   ├── lightserp/ (build from source + compose)
│   ├── searxng/
│   ├── nsqd/
│   ├── pagezen/
│   ├── nginx/ (reverse proxy, TLS, security headers)
│   ├── cloudflare_tunnel/ (systemd, ingress config)
│   ├── docker-compose-generator/ (renders all compose files)
│   ├── backup/ (multi-service orchestration)
│   └── monitoring/ (Prometheus, Grafana)
├── playbooks/ (site.yml, bootstrap.yml, services.yml, validate.yml, backup.yml)
├── ansible-vault/ (encrypted secrets)
├── .github/workflows/ (ansible-lint, molecule, deploy)
├── .ansible-lint
├── Makefile
└── README.md
```

## Secrets Management Strategy

**Two-layer approach:**

1. **Ansible Vault** — Bootstrap secrets only (OpenBao root token, initial
encryption keys, deploy keys). These are one-time values.
2. **OpenBao KV** — Runtime application secrets (passwords, API keys, JWT
secrets). Ansible generates `.env` files from OpenBao lookups at deploy time.

**CRITICAL: NEVER store application passwords in `inventory/group_vars/all.yml` in plaintext.**
When `all.yml` contains raw passwords (even in comments), any developer or CI/CD system that reads the inventory file exposes credentials. This is the #1 secrets leak in Ansible projects.

**Required:**
1. Encrypt `inventory/group_vars/all.yml` with `ansible-vault encrypt inventory/group_vars/all.yml`
2. Encrypt `group_vars/cloudflare_tunnel.yml` with `ansible-vault encrypt group_vars/cloudflare_tunnel.yml`
3. Add `.vault_key` to `.gitignore`
4. Never pipe Ansible inventory through `grep` — `grep` redacts `{{` as `***` which breaks templates
5. When collecting secrets from existing `.env` files, use a helper script (see `references/secrets-collection-from-existing-infra.md`)

**The `CHANGE_ME_IN_VAULT` sentinel pattern:** When a variable should be encrypted but isn't yet, use a sentinel like `CHANGE_ME_IN_VAULT` in the unencrypted file and add a `when: not item.startswith('CHANGE_ME')` guard in tasks. This ensures playbooks fail loudly on first run instead of deploying with placeholder values.

## Service Role Pattern

Each service gets a self-contained role with:
- `defaults/main.yml` — safe defaults (always idempotent)
- `vars/main.yml` — computed variables (derived from defaults + inventory)
- `tasks/main.yml` — ordered task list with `block`/`rescue` for resilience
- `templates/` — ALL configuration as Jinja2 (never raw files)
- `handlers/main.yml` — service restart triggers
- `meta/main.yml` — role dependencies

This means `ansible-playbook -l postgres` deploys just PostgreSQL independently.

## Deployment Order (Dependency Graph)

```
Layer 0: System hardening (SSH, UFW, fail2ban, NTP, users)
  → Layer 1: Docker CE + compose plugin
  → Layer 2: Core data services (Postgres, Redis, MinIO)
  → Layer 3: Infrastructure services (OpenBao, Keycloak, Gitea)
  → Layer 4: Application services (LightSerp, SearXNG, NSQD, PageZen)
  → Layer 5: Edge/access (Nginx, Cloudflare Tunnel)
  → Layer 6: Validation (health checks, drift detection)
  → Layer 7: Operations (backup, monitoring, CI/CD)

**CRITICAL ordering rule:** `docker-compose-generator` MUST run AFTER all service roles in `playbooks/services.yml`. If it runs first, its `.env` merge task has no `.env.*` files to merge, and the unified `.env` will be empty. See `references/env-per-service-architecture.md`.
```

## CI/CD & Automation

After Ansible playbooks are stable, wrap deployment/teardown in GitHub Actions
(or any CI runner) for repeatable, auditable infrastructure changes.

### Pattern: SSH-based Deploy with Health Verification

Uses `appleboy/ssh-action` for remote execution, `docker compose ps` for health
status, port-level checks, self-contained HTML report generation on the GH runner,
and email notification via `alekkor/action-send-email`.

See `references/github-actions-cicd-patterns.md` for complete workflow YAML templates:
- **deploy-and-verify.yml** — pull, up, health-check, port-check, report, email
- **destroy-without-proxy.yml** — down, remove containers/networks, verify nginx+cloudflared intact, report, email

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `workflow_dispatch` as primary trigger | Prevents accidental deploys on push; add `push: [main]` when stable |
| Destroy requires `confirm` input | Guardrail: user must type `DESTROY` to proceed |
| Report generated on GH runner | Keeps VM resources free; HTML self-contained for email |
| Port-level verification | Catches "running but not listening" edge cases |

### Related Patterns

- `references/ansible-dry-run-validation.md` — Pre-deploy playbook dry-run (Ansible-level)
- `references/github-actions-cicd-patterns.md` — Post-deploy CI verification (GitHub Actions-level)
- `references/slow-vm-deployment-workarounds.md` — SSH/SCP timeouts, inline Python heredocs for file edits on slow VMs (~65KB/s), Docker build fallback strategies
- `scripts/verify-services.sh` — SSH-based pre-flight health checks

## HA Strategy (Single-VM Constraints)

Within resource limits (15GB RAM), apply HA by priority:

| Priority | Service | Pattern | RAM Cost |
|----------|---------|---------|----------|
| P0 | PostgreSQL | PgBouncer + pgBackRest → MinIO | ~150MB |
| P0 | Redis | AOF persistence + Sentinel later | 0→500MB |
| P1 | Nginx | Multi-container behind proxy | ~20MB |
| P1 | Cloudflare Tunnel | 2 agents for edge redundancy | ~30MB |
| P2 | MinIO | Distributed mode (erasure coding) | ~0MB |
| P2 | OpenBao | Raft clustering + auto-unseal | ~300MB |
| P3 | Gitea | Persistent volume + daily dumps | ~0MB |

## Key Pitfalls

- **Ansible `***` redaction corrupts rendered .env files.** When `.env.j2` templates have `{{` replaced with `***` (from Ansible log redaction, lint output, or content scans), the `ansible.builtin.template` module passes `***` through literally — the remote `.env` file gets literal `***` instead of Jinja2 expressions. **Symptom:** `.env` on VM contains `KEY=*** vault_var | default('...') }}` instead of the rendered value. **Fix:** Always verify the source `.j2` template has literal `{{` (not `***`) before running: `head -n template.j2`. If `***` found: `sed -i '' 's/=\\*\\*\\* /={{ /g' roles/role/templates/.env.j2` then re-run. **Prevention:** Never pipe Ansible output through `grep` for .env templates — `grep` redacts `{{` as `***`. Use `cat` or read the file directly.

- **Cloudflare tunnel credentials ARE auto-provisioned by the `cloudflare_tunnel` role.** The role handles full automation: installs binary, tunnels login via API token, tunnels create, moves credentials to `/etc/cloudflared/`. **Only manual step:** create a Cloudflare API token (Zone.Zone > Read + Cloudflare Tunnel > Manage), store in `group_vars/cloudflare_tunnel.yml` as `cloudflared_api_token`, encrypt with `ansible-vault`. See `references/cloudflare-tunnel-auto-provisioning.md` for details.

- **Stale port/path data in documentation.** ALWAYS verify actual ports, volume paths, and nginx vHost routing against live `docker ps` output before writing or updating documentation. Common stale values: LightSerp API `8000`→`3071`, WebUI `3001`→`3070`, SearXNG `8080`→`8081`, NSQD `4150`→`8071`. Compose file may have moved from `iacgenie-unified-infra/` to `docker/iacgenie/`. Use the reference `references/phase-documentation-lifecycle.md` for the full verification checklist.
- **Compose file drift.** If the compose file on disk diverges from what Ansible
  would generate, the next Ansible run will overwrite it. Always commit the
  generated compose to git as a golden reference.
- **OpenBao init.** OpenBao can only be initialized once. The bootstrap playbook
  must detect whether init has already happened and skip it safely. If the Raft
  data is corrupted, you MUST wipe the volume and re-init — no partial recovery.
- **Keycloak migrations.** Keycloak 26 changed its admin API significantly from
  20-25. Realm export JSON from old versions is incompatible. Use Admin API
  for realm creation in Ansible. **CRITICAL: Never commit plaintext Keycloak admin passwords to Ansible role defaults.** Use `CHANGE_ME_IN_VAULT` as sentinel values and store actual credentials via `ansible-vault encrypt`. The session on 2026-08-07 demonstrated this risk — placeholder values in defaults are safer than committed passwords. When real credentials are extracted (e.g., from Keycloak's `.env.keycloak` on the VM), update only the `.env` template via Ansible, not the role defaults. See `references/keycloak-realm-provisioning.md` for the full provisioning workflow.
- **Gitea SSH through Cloudflare.** Cloudflare Tunnel is HTTP-only. SSH (port
  2222) cannot route through the tunnel. Use HTTPS + deploy tokens for git push,
  or add local SSH tunneling via `~/.ssh/config` with `ProxyJump`.
- **Docker socket permissions.** The Ansible user needs `docker` group membership
  or a dedicated sudo rule for docker commands. Don't use root.
- **Sensitive variables in docker-compose.** Never include passwords in the
  compose file. Use `env_file` or secret references. Ansible generates `.env`
  from Vault, compose reads from `.env`.
- **Template rendering must be idempotent.** If a Jinja2 template produces
  identical output, the `copy` module won't trigger a notification. If output
  differs (even by whitespace), the file changes and the service restarts.
  Be deterministic in templates.
- **Resource limits are mandatory.** Every container must have `deploy.resources.limits`
  to prevent one service from starving others on a constrained VM.
- **Ubuntu codename mismatch on derived distros.** Elementary OS 8 (based on
  Ubuntu 24.04) reports codename `circe`, not `noble`. Docker APT repos don't
  have a `circe` release — the repo URL must use the underlying Ubuntu codename.
  **Fix:** read `UBUNTU_CODENAME` from `/etc/os-release` instead of using
  `ansible_distribution_release` or `ansible_lsb.codename` (which both return
  the derived distro's codename). Use a shell task:
  `grep -m1 '^UBUNTU_CODENAME=' /etc/os-release | cut -d= -f2`
  and set it as a `set_fact` for the Docker repo URL.
- **OpenBao volume ownership.** The OpenBao Docker image runs as uid 100, gid 1000.
  Host bind mounts for `/openbao/raft` and `/openbao/data` must be owned by
  `100:1000` (or have group/world-readable permissions for that uid). Use
  `chown -R 100:1000` on the host volume directories before starting the container.
- **Docker version upgrade wipes images.** Upgrading Docker CE via apt (e.g. 29.1.3
  to 29.7.1) replaces the binary but **does not preserve pulled images** if
  containerd storage is reset. Always re-pull or rebuild images after a Docker
  upgrade. Use `docker images` to audit before and after.
- **Docker daemon DNS for registry pulls.** If `docker pull` hangs or returns
  "context canceled", the Docker daemon's DNS may not resolve the registry.
  Add `\\\"dns\\\": [\\\"8.8.8.8\\\", \\\"1.1.1.1\\\"]` to `/etc/docker/daemon.json` and restart
  the Docker service. The host's `/etc/resolv.conf` (systemd-resolved) is not
  always inherited by dockerd.
- **Nginx pid file permission.** When `nginx.conf` specifies `user www-data;`,
  the pid file path must be writable by `www-data`. If `/run/nginx.pid` is owned
  by root, `nginx -t` fails with "Permission denied". Fix by ensuring the
  pid file directory is writable: `sudo rm -f /run/nginx.pid && sudo chmod 755 /run`.
- **Docker compose pull vs. build.** For custom images built from source (e.g.
  LightSerp), `docker compose pull` will fail with "pull access denied". The
  images must be built locally with `docker build -t tag .` before compose can
  start the services. Check for locally-built images before running `up`.
- **Cloudflare Tunnel as systemd, not Docker.** Cloudflare Tunnel (cloudflared)
  typically runs as a systemd service with its own unit file, not as a Docker
  container. The credentials file path (`auth.json`) must be readable by the
  service user, and the tunnel configuration (`config.yml`) must point to the
  correct credentials path. **ALWAYS create the config directory first:**
  `ansible.builtin.file: path: /etc/cloudflared state: directory` before the
  template task. Without this, the template deploy fails with "Destination
  directory does not exist".

- **Docker-based roles must skip host-side user/directory tasks.** When an Ansible role manages a Docker container service (PostgreSQL, Redis, MinIO, etc.), the role must NOT create users (e.g., `postgres`, `redis`) or data directories on the host OS. Docker handles all of this internally via volume mounts and container image layers. A task like `ansible.builtin.file: path: /var/lib/postgresql/data owner: postgres` will fail because the `postgres` user only exists inside the container, not on the host. The role should ONLY: deploy `.env` config files to the host, check container status. If you need to create host-side directories, use `state: directory` with `owner: root` — Docker handles ownership via volume mounts.

- **Docker replaces hyphens with underscores in network names.** A Docker network named `iacgenie-network` appears as `iacgenie_network` on the engine. Always check real names with `docker network ls`. When using the `community.docker.docker_network` module to inspect existing networks, use the underscore version.

- **Role task files cannot be run as standalone playbooks.** Role task files (e.g., `roles/postgresql/tasks/main.yml`) lack play structure and variable scoping. They will fail with `Task failed: Module failed: ... column 3` errors when run directly via `ansible-playbook roles/.../tasks/main.yml`. Always test roles through the playbook that includes them (e.g., `playbooks/services.yml`).
- **Collecting real secrets from existing infra.** When running Ansible against
  a live VM with existing `.env` files, collect actual credentials before the
  first run. Use a helper script to extract `.env` values and map them to
  Ansible `group_vars/all.yml`. See `references/secrets-collection-from-existing-infra.md`
  for the pattern.
- **UFW Ansible module `policy` field uses `allow`, not `accept`.** In UFW 2.x
  the `community.general.ufw` module requires `policy: allow` for the default
  outgoing rule. Using `policy: accept` causes a silent failure (no rule created).
  This is a common source of firewalls not blocking outgoing traffic after a
  playbook run.
- **Gitea rootless image data dir ownership.** Gitea 1.23.4-rootless runs as
  UID 100, GID 1000. The data volume directory (`/var/lib/gitea`) must be owned
  by `100:1000`. Set with `owner: "100"` and `group: "1000"` in the Ansible
  `file` module — string quoting is required since numeric values are interpreted
  as integers by default.
- **OpenBao healthcheck needs `-k` for self-signed TLS.** The OpenBao health
  endpoint uses a self-signed cert by default. The healthcheck `curl` command
  must include `-k` flag. Also check for both `\"sealed\":false` (running) and
  `\"initialized\":true` (post-init) since sealed containers still return 200 OK.
- **Deploy user must be added to docker group.** The deployment user that runs
  `docker compose` commands needs `docker` group membership, or Ansible will
  get `permission denied` on Docker socket operations. Add with
  `ansible.builtin.user: groups: docker, append: yes`.
- **LightSerp compose env vars require specific keys.** LightSerp API expects
  `SEARXNG_URL` (uppercase, NOT `SearXNG_URL`), plus `LIGHTSERP_S3_BASE` and
  `LIGHTSERP_ALLOW_INSECURE` (for self-signed cert TLS). These were not in the
  original template and cause API failures at runtime.

- **LightSerp Telemetry `logtide` env var.** LightSerp's compiled Docker image
  has a hardcoded OpenTelemetry fallback to `http://logtide:4318/v1/traces`.
  Setting `LOGTIDE_URL: \"\"` does NOT suppress it (empty string is falsy in JS).
  Set `LOGTIDE_URL: http://localhost:4318/v1/traces` to avoid DNS resolution.

- **LightSerp PageZen connection.** LightSerp API expects `LIGHTSERP_PAGEZEN_API`
  env var (not `PAGEZEN_URL`). Set to `http://pagezen:8082` to connect to the
  PageZen content extraction service. Without this, LightSerp reports
  `lightPanda: unavailable` in health checks.
- **OpenBao storage type must be `raft` for production.** The compose template
  must set `OPENBAO_STORAGE_TYPE: raft` — `file` storage has no crash recovery
  and data is lost on container restart. Also add the `openbao_raft` volume.
- **Ansible vault key missing but no encrypted files.** When `ansible.cfg`
  references a vault key file (e.g. `vault_password_file = ./.vault_key`) but
  no files in the project are actually encrypted (no `$ANSIBLE_VAULT` marker
  in any `.yml`), the playbook fails with a cryptic "vault password file not
  found" error. **Fix:** check first with
  `grep -rl '$ANSIBLE_VAULT' roles/ playbooks/ inventory/ 2>/dev/null`. If no
  encrypted files found, create a dummy key: `echo "dummy" > .vault_key &&
  chmod 600 .vault_key`. This is a common occurrence when the project structure
  expects vault support but secrets haven't been introduced yet.
- **Docker network segmentation (3-tier):** When adding network isolation, use three named networks: `frontend` (nginx-exposed services: api, webui, page, searxng, minio-console-proxy), `backend` (data/auth: postgres, redis, minio, keycloak, gitea, openbao), `messaging` (pub/sub: nsqd). Services that need multiple layers join multiple networks. Do NOT use `external: true` for these — define them inline in the compose file. See `references/docker-network-segmentation.md` for the full architecture guide.

- **deploy.sh playbook/inventory path fix (2026-08-26):** The `deploy.sh` script referenced `playbook.yml` and `inventory/hosts.yml` — both wrong. The correct paths are `playbooks/site.yml` and `inventory/hosts.ini`. Always verify the playbook and inventory paths match the actual directory structure before running.

- **Adding a new product to existing Ansible infrastructure (2026-08-28):** The complete pattern for integrating a new product onto an existing Ansible-managed stack:
  1. **Create the role:** `mkdir -p roles/<product>/{defaults,tasks,templates}`. Add defaults for ports, images, env vars; tasks for building/starting services.
  2. **Add vHost to nginx template:** Append the new server block (with Jinja2 variable references for ports/domains) to `roles/nginx-container/templates/nginx-unified.conf.j2`, inserting BEFORE the catch-all block.
  3. **Add services to compose template:** Insert service definitions (with `{% if <product>_enabled | default(true) %}` guard) into `roles/docker-compose-generator/templates/docker-compose.yml.j2`, before the cloudflared section.
  4. **Register role in playbooks:** Add `- role: <product>` to `playbooks/services.yml` (and `site.yml.j2`) after the last app service role.
  5. **Add data directories:** Add product build/context dirs to `roles/docker-compose-generator/tasks/compose.yml` so Ansible creates them.
  **CRITICAL: After running Ansible, files in `roles/*/templates/` are owned by root.** Subsequent manual edits via SSH will get PermissionError. Fix: `sudo chown mkanavi:mkanavi ~/iacgenie-platform/infra/ansible/roles/*/templates/*` before editing.

- **Nginx security headers (all vHosts):** Add Content-Security-Policy (per-vHost, tailored), Permissions-Policy (camera, mic, geo, payment blocked), X-Permitted-Cross-Domain-Policies (none), Cross-Origin-Embedder/Opener/Resource-Policy headers, and CORS headers to API vHosts. Always use `always` keyword so headers appear on error responses too. See `references/nginx-security-headers-hardening.md` for the complete header set and CORS preflight pattern.

- **Ansible Vault workflow (decrypt → edit → re-encrypt):** When you need to edit an encrypted Ansible inventory file, decrypt it first (`ansible-vault decrypt`), make your changes, then re-encrypt (`ansible-vault encrypt`). This is the correct pattern — do NOT leave files unencrypted between edits.

- **Docker compose service names may differ from Ansible references.** When
  verifying service status via `docker compose -p iacgenie ps`, the SERVICE
  column shows the actual service name, which may differ from what your
  playbook references. The container name (NAME column) uses `iacgenie_name`
  (underscore) format, but the SERVICE column is what matters for restart/ps
  commands. Always verify the actual SERVICE name before writing `docker compose`
  commands in roles: `docker compose -p iacgenie ps --format '{{.Service}}'`
  on the target VM. A common mismatch: services named `searxng` in the compose
  template may be renamed to `lightserp-searxng` in the running infrastructure,
  causing handler failures with `no such service: searxng`.

- **Shared `.env` file breaks idempotency.** When multiple Ansible service roles
  deploy to the same `.env` file, each role overwrites the previous role's
  variables. On subsequent playbook runs, every role sees the file as
  "changed" (because another role wrote different content last). **Fix:** give
  each service its own `.env.<service>` file (e.g., `.env.postgres`,
  `.env.redis`). Use the `docker-compose-generator` role to merge all
  `.env.*` files into the unified `.env` using a shell-based `diff` + `mv`
  pattern. See `references/env-per-service-architecture.md` for the full
  pattern.

- **`docker compose` requires `-f` flag when not in compose directory.** Running
  `docker compose ps` or `docker compose up -d` without the `-f` flag fails with
  "no configuration file provided: not found" when the current working directory
  does not contain a `docker-compose.yml`. Always use `-f /full/path/to/compose.yml`
  in Ansible tasks and handlers. The handler's `docker compose` commands are the
  most common failure point because they run from the playbook's working directory.
- **YAML inventory without `plugin:` key causes parser warnings.** When using a
  YAML inventory file, Ansible 2.16+ tries to parse it with multiple plugins
  (auto, yaml, ini) and may emit warnings like "no root 'plugin' key found" or
  "Invalid children entry". **Fix:** either add `---\\nplugin: yaml\\n` at the top
  of the file, or convert to `.ini` format. The playbook will still work without
  it, but the warnings pollute dry-run output and can obscure real errors.

- **Handler fires Docker commands for host-level services.** When reviewing or
  writing handlers, verify the target actually runs inside Docker. Two common
  failures discovered: (1) Nginx handler runs `docker compose restart nginx` but
  Nginx runs as a **host-level systemd service**, not in a container. (2) Cloudflare
  Tunnel handler runs `docker compose restart cloudflared` but cloudflared is a
  **systemd service** (`/etc/systemd/system/cloudflared.service`). Fix: use
  `ansible.builtin.systemd: state: restarted, name: nginx` or
  `ansible.builtin.command: nginx -s reload` for host services. The `docker compose`
  handler silently fails or errors out, breaking playbook idempotency on subsequent runs.

- **Referenced role directory does not exist.** When `playbooks/services.yml`
  lists `role: gitea` but `roles/gitea/` directory doesn't exist, the playbook
  run will fail with `ERROR! the role 'gitea' was not found`. Always cross-check
  every role listed in playbooks against the `roles/` directory before running.
  If a role is missing, either create it, remove it from the playbook, or move
  its functionality into an existing role (e.g., docker-compose-generator template).

- **Nginx config template uses Docker hostnames for proxy_pass but Nginx runs on the host.** The Nginx Ansible role's Jinja2 template (`roles/nginx/templates/`) may generate `proxy_pass http://keycloak:8080;` using Docker service names. Since Nginx is deployed as a host-level systemd service (not in a container), Docker container hostnames **do not resolve** from the host. This causes `nginx -t` to fail with `host not found in upstream "keycloak"`. **Fix:** the Nginx template must use `proxy_pass http://127.0.0.1:{{ service_host_port }};` where `service_host_port` is the host-mapped port from group_vars, NOT the Docker container port. Example mapping: Keycloak container port 8080, host-mapped port 8083 → `proxy_pass http://127.0.0.1:8083;`. **Prevention:** In the Nginx role's group_vars, define `service_host_ports:` as a dict mapping service names to their host-mapped ports (not container ports), and reference that in the template.

- **Docker nginx container with `network_mode: host` is a no-op.** When the compose template includes an `nginx` service with `network_mode: host`, it mounts the same config files as the host-level nginx systemd service. Both try to bind ports 80/443 — one will fail or be a silent no-op. The host-level nginx (systemd) is the one that actually serves traffic. **Fix:** Remove the Docker nginx container from compose entirely; keep only host-level nginx (managed by `nginx` Ansible role). If you need a Docker nginx, use bridge networking with explicit port mapping instead of `network_mode: host`.

- **Port conflict diagnosis via docker-proxy PID analysis.** When two containers appear to bind the same host port, `ss -tlnp` shows only ONE docker-proxy PID — meaning one container won the bind and the other failed silently. The nginx proxy may point to that port, but it reaches the WRONG service. **Diagnosis:** `sudo ss -tlnp | grep ':<port>'` to find the owning PID, then `docker ps --format '{{.Names}}\t{{.Ports}}'` to map PID to container. **Fix:** change one of the conflicting host port mappings (e.g., `9091:9096` → `9096:9096`). See `references/port-conflict-diagnosis.md` for the full diagnostic procedure.

- **Orphan containers not in docker-compose files.** Containers running but NOT defined in any compose file will be lost on `docker compose down` and won't survive Ansible redeploy. They may have been created manually, from a deleted compose file, or from an older architecture. **Detection:** `docker ps --format '{{.Names}}\t{{.Image}}'` and compare against `grep '^  [a-z]' docker-compose.yml`. Any container not in the compose file is an orphan. **Fix:** either add it to the compose template or stop/remove it with `docker compose -f <file> rm -f <name>`.

- **OpenBao `.env.j2` renders fresh secrets on every playbook run.** Templates like
  `.env.j2` with `CHANGE_ME_IN_VAULT` defaults will overwrite existing `.env` files
  on every Ansible run with placeholder values. If OpenBao already holds real secrets,
  a rebuild will create `.env` files referencing the placeholder — every service that
  reads from those `.env` files will fail authentication until the real secrets are
  restored to OpenBao or the `.env` files are manually re-populated. **Fix:** check
  whether OpenBao already has secrets (`openbao status` + `openbao secret list`) and
  whether `.env` files already exist on the VM before running a rebuild playbook.

- **Compose file drift between Ansible template and deployed file.** The Ansible
  template (`roles/docker-compose-generator/templates/docker-compose.yml.j2`) may
  differ from the actual deployed compose file on disk (e.g., `docker-compose-newvm.yml`
  with different image tags, volume mounts, port mappings, or security configurations).
  The deployed file may have evolved beyond what the Ansible template generates.
  **Fix:** `ssh user@vm 'cat /path/to/deployed/docker-compose.yml'` and compare
  line-by-line with the template before any rebuild. The deployed file is the source
  of truth for runtime configuration.

- **OpenBao 2.6 CLI is `bao`, not `openbao`.** The OpenBao Docker image's binary
  at `/usr/local/bin/bao` — the `openbao` name is only used for the Helm chart
  and documentation. Using `openbao server` in a compose command causes
  `docker-entrypoint.sh: exec: line 96: openbao: not found`. **Fix:** use
  `bao server` in compose command directives.

- **OpenBao healthcheck with `bao status` fails when `bao` not in container PATH.** The `bao` binary in OpenBao 2.6 Docker images may not be accessible via `$PATH` in the healthcheck context, especially when `OPENBAO_ADDR` env vars force HTTPS. The healthcheck `bao status --address http://127.0.0.1:8200 | grep -q Initialized` returns exit 1 even when the server is healthy. **Fix:** use a port-only TCP check instead: `test: ["CMD-SHELL", "bash -c 'exec 3</dev/tcp/127.0.0.1:8200 && echo OK'"]`. Always verify `bao` availability: `docker exec <container> which bao 2>/dev/null`.

- **OpenBao config path must match the volume mount, not the default inside-image path.**
  The OpenBao image expects config at `/openbao/data/openbao-prod.hcl` by convention,
  but the compose mount maps `/home/mkanavi/docker/iacgenie/data/openbao` → `/openbao/storage`.
  The `command` must point to the mounted path: `bao server -config=/openbao/storage/openbao-prod.hcl`.
  The config file at `/openbao/storage/openbao-prod.hcl` must exist on the host before starting.

- **OpenBao container user cannot access host bind mounts.** The OpenBao Docker image
  runs as the `openbao` user (uid 100) inside the container. Host bind mount files
  owned by `mkanavi` (uid 1000) produce `permission denied` errors. **Fix 1 (quick):**
  add `user: "0:0"` to the OpenBao service in compose to run as root. **Fix 2 (cleaner):**
  `chown -R 100:1000 /path/to/openbao/data` and `chown -R 100:1000 /path/to/openbao/raft`
  on the host before starting the container. **Fix 3 (most robust):** use the `role`
  in an Ansible playbook with `ansible.builtin.file` to set correct ownership.

- **OpenBao 2.6 rejects `rate_limit` config field.** The `rate_limit = 0` field in
  `openbao-prod.hcl` is not supported and causes warning messages (but not fatal errors).
  It is silently dropped in OpenBao 2.6+ but the warning pollutes logs. Remove it.

- **OpenBao init_keys.json stores Shamir unseal keys, not raw hex.** The unseal keys
  in `init_keys.json` are base64-encoded. To unseal via the API (`POST /v1/sys/unseal`),
  pass the base64 key directly in `{"key": "..."}`. To unseal via CLI inside the
  container, use `bao operator unseal <key>` — the CLI reads from stdin when not in
  a TTY, so pipe the key or pass it as the first argument. **Troubleshooting:** if
  `bao operator unseal` says "http: server gave HTTP response to HTTPS client", the
  `OPENBAO_CLUSTER_ADDR` env var forces HTTPS — override with `OPENBAO_ADDR=http://...`
  via `docker exec -e OPENBAO_ADDR=...`.

- **Keycloak 26 command syntax changed from 20-25.** The following flags are **invalid** in Keycloak 26.0:
  - `--hostname-keycloak` → use `--hostname <domain>` (e.g. `--hostname auth.iacgenie.com`)
  - `--db=postgres` → removed; use `--db-url-*` flags instead
  - `--db-database` → use `--db-url-database`
  - `--proxy edge` → use `--proxy-trusted-addresses` or remove (use environment vars instead)
  Also remove deprecated env vars `KC_DB`, `KC_DB_URL_HOST`, `KC_DB_URL_PORT`,
  `KC_DB_DATABASE`, `KC_DB_USERNAME`, `KC_DB_PASSWORD`, `KC_HOSTNAME`, `KC_PROXY`
  from the environment section if they're already on the command line.

  - **NSQD `--tcp-address=0.0.0.0` produces misleading error.** In NSQD 1.3.0, passing
    `--tcp-address=0.0.0.0` in the command causes `FATAL: listen unix 0.0.0.0: bind:`
    address already in use` — the error mentions "unix" because NSQD misinterprets
    the `0.0.0.0` value as a Unix socket path rather than a TCP address. **Fix:**
    omit the `--tcp-address` flag entirely; NSQD defaults to `0.0.0.0:4150`. The
    compose template should use just: `nsqd --data-path=/nsq/data`.

  - **Multiple services use `:latest` image tag.** MinIO, SearXNG, NSQD, PageZen all
    use `:latest` in their compose templates. A rebuild pulls different image versions
    potentially with breaking changes. **Fix:** pin specific versions for production
    stability: `minio/minio:RELEASE.2025`, `searxng/searxng:2025.6`, etc.

  - **Rebuild readiness: assess idempotency before tearing down.** When the user
    asks whether the full infra can be torn down and rebuilt (services destroyed,
    VM preserved), run this evaluation before any action:
    1. Read ALL playbooks, roles, task files, handlers, templates, inventory, vars
    2. Map service lifecycle: Docker volumes (persistent), systemd services, host config
    3. Check secrets management: do `.env.j2` templates render fresh values every run?
    4. Verify OpenBao state: unseal keys, raft data, stored secrets — these survive rebuild
    5. Report risks: data loss (volumes destroyed by `down -v`), secret mismatch, tunnel creds regenerated
    See `references/full-infra-teardown-evaluation.md` for the complete checklist.

  - **Docker network `external: true` requires network to exist first.** When `docker-compose.yml.j2` sets `external: true` for the shared network, the network must already be created (by the bootstrap or network role) BEFORE any service that references it starts. If it doesn't exist, Docker will error with `network "iacgenie-network" not found`. **Fix:** ensure the `docker network create` command runs in the bootstrap playbook with `state: present`, and that the network role is listed before service roles in `playbooks/services.yml`.

  - **PostgreSQL `pg_hba.conf` catch-all rule ordering matters.** The last `host` rule in `pg_hba.conf` acts as a catch-all. If earlier rules use `trust` for `127.0.0.1/32` but the catch-all uses `scram-sha-256`, connections from Docker containers (which resolve to a different IP than 127.0.0.1) will hit the `scram-sha-256` rule. If the connecting client (e.g., Gitea's Go PostgreSQL driver) doesn't support SCRAM, auth fails. **Fix:** change the catch-all to `md5` or `trust`: `docker exec iacgenie_postgres sed -i "s/^host all all all scram-sha-256/host all all all md5/" /var/lib/postgresql/data/pg_hba.conf && docker exec iacgenie_postgres psql -U postgres -c "SELECT pg_reload_conf();"`. **Test from inside another container first:** `docker exec iacgenie_postgres sh -c "PGPASSWORD=pwd psql -h postgres -U user -d db -c 'SELECT 1'"`.

  - **PostgreSQL `scram-sha-256` password stored but pg_hba requires `md5`.** PostgreSQL stores passwords as `SCRAM-SHA-256` by default. If `pg_hba.conf` uses `md5` auth, PostgreSQL will still accept the SCRAM password because it downgrades. But if you change `pg_hba.conf` to `md5` first, then set the password with `ALTER ROLE`, the password gets stored as `SCRAM-SHA-256` anyway (PostgreSQL's default `password_encryption = scram-sha-256`). This mismatch can cause auth failures. **Fix:** always set the password BEFORE changing `pg_hba.conf` auth method, OR set `password_encryption = md5` first: `docker exec iacgenie_postgres psql -U postgres -c "SELECT set_config('password_encryption', 'md5', false);" && docker exec iacgenie_postgres psql -U postgres -c "ALTER ROLE user WITH PASSWORD 'pwd';"`.

  - **OpenBao 2.6 unseal key format and KEY0 padding.** The `init_keys.json` contains base64-encoded Shamir keys (`unseal_keys_b64`). In OpenBao 2.6 with `t=2, n=3` Shamir, all keys should decode to the same byte length (typically 33 bytes). Key 0 may have incorrect base64 padding (e.g., 47 chars instead of 48) causing it to decode to the wrong length (35 bytes). **Fix:** validate key lengths before unsealing: `key=$(cat init_keys.json | python3 -c "import sys,json; print(json.load(sys.stdin)['unseal_keys_b64'][0])" && echo -n "$key" | base64 -d | wc -c)`. If it's wrong, use key 1 or 2 instead. Unseal via API: `curl -s -X POST http://127.0.0.1:8200/v1/sys/unseal -d "{\"key\":\"$key\""}`. Also: `OPENBAO_CLUSTER_ADDR` env var forces HTTPS — override with `OPENBAO_ADDR=http://...` when unsealing from inside the container: `docker exec -e OPENBAO_ADDR=http://127.0.0.1:8200 iacgenie_openbao sh -c "bao operator unseal --non-interactive -address=http://127.0.0.1:8200 $KEY"`.

  - **Keycloak 26 command syntax changed from 20-25.** The following flags are **invalid** in Keycloak 26.0:
  - `--hostname-keycloak` → use `--hostname <domain>` (e.g. `--hostname auth.iacgenie.com`)
  - `--db=postgres` → removed; use `--db-url-*` flags instead
  - `--db-database` → use `--db-url-database`
  - `--proxy edge` → use `--proxy-trusted-addresses` or remove (use environment vars instead)
  Also remove deprecated env vars `KC_DB`, `KC_DB_URL_HOST`, `KC_DB_URL_PORT`,
  `KC_DB_DATABASE`, `KC_DB_USERNAME`, `KC_DB_PASSWORD`, `KC_HOSTNAME`, `KC_PROXY`
  from the environment section if they're already on the command line.

  - **NSQD `--tcp-address=0.0.0.0` produces misleading error.** In NSQD 1.3.0, passing
    `--tcp-address=0.0.0.0` in the command causes `FATAL: listen unix 0.0.0.0: bind:`
    address already in use` — the error mentions "unix" because NSQD misinterprets
    the `0.0.0.0` value as a Unix socket path rather than a TCP address. **Fix:**
    omit the `--tcp-address` flag entirely; NSQD defaults to `0.0.0.0:4150`. The
    compose template should use just: `nsqd --data-path=/nsq/data`.

  - **Multiple services use `:latest` image tag.** MinIO, SearXNG, NSQD, PageZen all
    use `:latest` in their compose templates. A rebuild pulls different image versions
    potentially with breaking changes. **Fix:** pin specific versions for production
    stability: `minio/minio:RELEASE.2025`, `searxng/searxng:2025.6`, etc.

  - **Rebuild readiness: assess idempotency before tearing down.** When the user
    asks whether the full infra can be torn down and rebuilt (services destroyed,
    VM preserved), run this evaluation before any action:
    1. Read ALL playbooks, roles, task files, handlers, templates, inventory, vars
    2. Map service lifecycle: Docker volumes (persistent), systemd services, host config
    3. Check secrets management: do `.env.j2` templates render fresh values every run?
    4. Verify OpenBao state: unseal keys, raft data, stored secrets — these survive rebuild
    5. Report risks: data loss (volumes destroyed by `down -v`), secret mismatch, tunnel creds regenerated
    See `references/full-infra-teardown-evaluation.md` for the complete checklist.

  - **Docker network `external: true` requires network to exist first.** When `docker-compose.yml.j2` sets `external: true` for the shared network, the network must already be created (by the bootstrap or network role) BEFORE any service that references it starts. If it doesn't exist, Docker will error with `network "iacgenie-network" not found`. **Fix:** ensure the `docker network create` command runs in the bootstrap playbook with `state: present`, and that the network role is listed before service roles in `playbooks/services.yml`.

  - **PostgreSQL `pg_hba.conf` catch-all rule ordering matters.** The last `host` rule in `pg_hba.conf` acts as a catch-all. If earlier rules use `trust` for `127.0.0.1/32` but the catch-all uses `scram-sha-256`, connections from Docker containers (which resolve to a different IP than 127.0.0.1) will hit the `scram-sha-256` rule. If the connecting client (e.g., Gitea's Go PostgreSQL driver) doesn't support SCRAM, auth fails. **Fix:** change the catch-all to `md5` or `trust`: `docker exec iacgenie_postgres sed -i "s/^host all all all scram-sha-256/host all all all md5/" /var/lib/postgresql/data/pg_hba.conf && docker exec iacgenie_postgres psql -U postgres -c "SELECT pg_reload_conf();"`. **Test from inside another container first:** `docker exec iacgenie_postgres sh -c "PGPASSWORD=pwd psql -h postgres -U user -d db -c 'SELECT 1'"`.

  - **PostgreSQL `scram-sha-256` password stored but pg_hba requires `md5`.** PostgreSQL stores passwords as `SCRAM-SHA-256` by default. If `pg_hba.conf` uses `md5` auth, PostgreSQL will still accept the SCRAM password because it downgrades. But if you change `pg_hba.conf` to `md5` first, then set the password with `ALTER ROLE`, the password gets stored as `SCRAM-SHA-256` anyway (PostgreSQL's default `password_encryption = scram-sha-256`). This mismatch can cause auth failures. **Fix:** always set the password BEFORE changing `pg_hba.conf` auth method, OR set `password_encryption = md5` first: `docker exec iacgenie_postgres psql -U postgres -c "SELECT set_config('password_encryption', 'md5', false);" && docker exec iacgenie_postgres psql -U postgres -c "ALTER ROLE user WITH PASSWORD 'pwd';"`.

  - **OpenBao 2.6 unseal key format and KEY0 padding.** The `init_keys.json` contains base64-encoded Shamir keys (`unseal_keys_b64`). In OpenBao 2.6 with `t=2, n=3` Shamir, all keys should decode to the same byte length (typically 33 bytes). Key 0 may have incorrect base64 padding (e.g., 47 chars instead of 48) causing it to decode to the wrong length (35 bytes). **Fix:** validate key lengths before unsealing: `key=$(cat init_keys.json | python3 -c "import sys,json; print(json.load(sys.stdin)['unseal_keys_b64'][0])" && echo -n "$key" | base64 -d | wc -c)`. If it's wrong, use key 1 or 2 instead. Unseal via API: `curl -s -X POST http://127.0.0.1:8200/v1/sys/unseal -d "{\"key\":\"$key\"}"`. Also: `OPENBAO_CLUSTER_ADDR` env var forces HTTPS — override with `OPENBAO_ADDR=http://...` when unsealing from inside the container: `docker exec -e OPENBAO_ADDR=http://127.0.0.1:8200 iacgenie_openbao sh -c "bao operator unseal --non-interactive -address=http://127.0.0.1:8200 $KEY"`.

  - **Docker Compose DNS aliases may not include the short service name.** When a service has no explicit `networks:` aliases section in the compose file, the service name may NOT resolve as a DNS alias inside other containers. The container name (e.g., `iacgenie_nsqd`) will always resolve, but the short service name (`nsqd`) may not. **Fix:** use the container name format (`iacgenie_<service>`) in app configuration instead of the service name. Alternatively, add explicit `aliases` in the `networks:` section of the service: `networks: iacgenie-network: aliases: [nsqd, nsqd-internal]`. **Debug:** `docker exec iacgenie_container_name nslookup service_name` to test DNS resolution.

- **ansible `uri` module parameter naming changed.** In Ansible 2.15+, `body_format: urlencoded` was renamed to `body_format: form-urlencoded`. Also, `return_contents` was renamed to `return_content`. Using the old parameter names causes module failure with messages like `body_format must be one of: form-urlencoded, json, raw, form-multipart, got: urlencoded` or `argument 'return_contents' is not valid`. **Fix:** always use `form-urlencoded` and `return_content` in modern Ansible. **Prevention:** run `ansible-playbook --check` before deployment to catch parameter naming issues.

- **ansible `template` module `***` redaction corrupts `.env` files.** When `.env.j2` templates have `{{` replaced with `***` (from Ansible log redaction, lint output, or content scans), the `ansible.builtin.template` module passes `***` through literally — the remote `.env` file gets literal `***` instead of Jinja2 expressions. **Symptom:** `.env` on VM contains `KEY=*** vault_var | default('...') }}` instead of the rendered value. **Fix:** always verify the source `.j2` template has literal `{{` (not `***`) before running: `head -n template.j2`. If `***` found: `sed -i '' 's/^\*\*\* /{{ /g' roles/role/templates/.env.j2` then re-run. **Prevention:** Never pipe Ansible output through `grep` for .env templates — `grep` redacts `{{` as `***`. Use `cat` or read the file directly.

- **Docker port conflicts with `docker-proxy`.** Multiple containers binding to the same host port via `docker-proxy` causes subtle failures. **Symptom:** One service is unreachable while another on the same port works. **Diagnosis:** `docker ps --format "{{.Names}}\t{{.Ports}}"` to see all host port mappings, then `ss -tlnp | grep <port>` to check which `docker-proxy` PID is bound. **Fix:** ensure each container maps to a unique host port in docker-compose. When adding containers to an existing network, verify no port collision before starting. **Prevention:** maintain a port allocation table in documentation.

- **Docker compose `--remove-orphans` essential for container cleanup.** When container names change (e.g., `clamav-backend` → `clamav`), old containers remain running as orphans. **Fix:** add `--remove-orphans` to the `docker compose up` command in Ansible handlers: `docker compose -f /path/to/compose.yml up -d --remove-orphans`. **Prevention:** always use `--remove-orphans` in compose up commands in Ansible roles.

- **Keycloak 26 `start-dev` with PostgreSQL does NOT create bootstrap admin.** The `bootstrap-admin-password` only works with embedded H2 database. When using `--db=postgres` with `start-dev`, the admin user is NOT created. **Symptom:** Admin login returns 401 even though `KEYCLOAK_ADMIN_PASSWORD` env var is set. **Fix:** (a) Start with H2 first to create admin, then switch to PostgreSQL, or (b) Create the admin user via the Admin REST API (`POST /admin/realms/master/users` with credentials), or (c) Directly insert into the PostgreSQL database. **Prevention:** for PostgreSQL deployments, always bootstrap admin credentials separately or use the Admin API after initial container start.

- **ansible inventory `keycloak_admin_password` self-referencing variable.** When `defaults/main.yml` has `keycloak_admin_password: "{{ keycloak_admin_password | default('CHANGE_ME') }}"`, it creates a self-referencing variable causing Ansible to skip the variable resolution. **Fix:** use a different internal variable name: `keycloak_admin_password: "{{ _kc_pass | default('CHANGE_ME') }}"`. **Prevention:** never use the same variable name on both sides of a Jinja2 `default()` expression.

- **Docker healthcheck `test` field requires `CMD` or `CMD-SHELL` prefix.** Docker Compose healthcheck `test` in array format must start with `CMD`, `CMD-SHELL`, or `NONE`. Direct paths like `[\"/usr/bin/bao\", \"status\"]` fail with `healthcheck.test must start either by 'CMD', 'CMD-SHELL' or 'NONE'`. **Fix:** use `[\"CMD-SHELL\", \"/usr/bin/bao status\"]`. **Prevention:** always use the `CMD-SHELL` wrapper for healthcheck test arrays.

  - **Gitea database migration version mismatch destroys startup.** When the Gitea database has a migration version (e.g., 343) that corresponds to a newer Gitea binary (e.g., 1.25+) than the one running (e.g., 1.23.4, which uses migration 312), Gitea exits with a fatal error. **Fix:** `DROP DATABASE IF EXISTS gitea; CREATE DATABASE gitea OWNER gitea;` then restart. This resets the migration table to 0 (fresh database). For a clean start, also remove all files in the data bind mount directory (`/var/lib/gitea/`).

  - **Gitea app.ini `PASSWD` format must be `PASSWD=value` (no space, no trailing `=`).** When Gitea writes its `app.ini` configuration, it may produce a malformed password line like `PASSWD=` (empty value) followed by the actual password on the next line as a separate key. This causes `PASSWD = GxKBj6...` to be split across two lines, making the password empty. **Fix:** check the raw file with `sed -n "34p" /path/to/app.ini | xxd` to see the actual bytes. If the password is on the next line, replace line 34 with the correct format and delete line 35: `sed -i "34s/.*/PASSWD=pwd/" /path/to/app.ini && sed -i "35d" /path/to/app.ini`. **Prevention:** ensure the Docker Compose `.env` file has the correct password value and that `${GITEA_DB_PASSWORD}` resolves properly before Gitea first starts.

  - **PostgreSQL user requires matching password in both PG and env files.** After dropping/recreating a PostgreSQL database, the database user may lose its password or be reset. Always verify: `docker exec iacgenie_postgres psql -U postgres -c "ALTER ROLE gitea WITH PASSWORD 'pwd';"` AND verify the `.env` file (or `.env.gitea`) has `GITEA_DB_PASSWORD=pwd` that gets merged into the unified `.env`. **Also set the same password on any other roles that need it** (e.g., `keycloak` role).

  - **LightSerp API PostgreSQL DATABASE_URL format.** The format `lightsrp@postgres:5432/lightsrp` is NOT a valid PostgreSQL URL. The app's parser interprets `postgres:5432` as `host:port` in the wrong position, extracting `base` as the hostname. **Fix:** use proper format: `postgresql://lightsrp:PASSWORD@postgres:5432/lightsrp` with the `${PG_ROOT_PASSWORD}` variable for the password. The app also tries to connect to a `logtide` database which doesn't exist — verify all database names referenced in `.env.lightserp` actually exist in PostgreSQL.

  - **LightSerp Redis connects to `127.0.0.1` instead of Docker service name.** Even when `REDIS_URL` is set in the `.env`, the app may default to `127.0.0.1:6379` if the env var isn't properly loaded or if the app has a hardcoded fallback. **Fix:** verify the container's env vars: `docker exec iacgenie_lightserp_api env | grep REDIS`. The Redis container is on the `iacgenie-network` so the hostname must be `redis` (Docker DNS alias).

  - **LightSerp listens on different ports than the compose mapping.** The LightSerp API binary listens on port **3000**, not the mapped `8000`. The WebUI listens on port **3001** (mapped correctly). The PageZen mock server listens on **8082**, not `8081`. Verify with `docker exec iacgenie_lightserp_api sh -c "cat /proc/net/tcp" | head` (decode hex port) or check startup logs: `docker logs iacgenie_lightserp_api --tail 5`. **Fix:** update the compose port mapping to match: `3000:3000` for API, `3001:3001` for WebUI, `8082:8082` for PageZen. Or update the app config to listen on the mapped port.

  - **OpenBao 2.6 `/v1/sys/seal-status` returns `sealed: false` even during auth issues.** After running `openbao operator unseal` (or even without running it), the seal status may show `sealed: false` while the server still refuses connections. This indicates the node is in a transitional state — the raft consensus hasn't fully formed yet. **Fix:** wait 10-30 seconds and try the health endpoint. When healthy, it returns `{"initialized":true,"sealed":false,"standby":false,"replication_performance_mode":"primary"}`.

- **SSH `tar | gpg` pipeline over non-interactive SSH breaks with binary data.** When running `tar czf - ... | gpg ...` inside an SSH command to a remote VM, the binary tar stream interferes with SSH's line-based terminal handling. This causes gpg to fail with "can't open" or produce corrupted output, and the SSH call returns a non-zero exit code. The `run_ssh()` function strips stderr, so the failure appears silent.

  **Symptom:** Backup/restore scripts fail silently or return non-zero exit codes with no visible error after `tar | gpg` pipeline over SSH.

  **Fix:** Use file-based pipeline instead of stdin piping:
  ```bash
  # WRONG (binary stream over SSH):
  tar czf - /path/to/data | gpg --batch --symmetric ... --output file.gpg

  # RIGHT (file-based):
  tar czf /tmp/backup.tar.gz /path/to/data
  gpg --batch --symmetric ... --output file.gpg /tmp/backup.tar.gz
  rm -f /tmp/backup.tar.gz
  ```

- **Docker Compose: `external: true` network name resolution requires exact `name:` override.** A Docker network named `iacgenie-backend` in a compose file appears as `iacgenie_iacgenie-backend` on the engine. When a second compose file with the same project name references the same network via `external: true`, Docker Compose looks for `iacgenie_iacgenie_backend` (underscores for hyphens) which does NOT match the actual name `iacgenie_iacgenie-backend` (hyphen retained).

  **Symptom:** `network iacgenie-backend declared as external, but could not be found`

  **Fix:** In the composing file that shares an external network, use an explicit `name:` override:
  ```yaml
  networks:
    iacgenie_backend:
      external: true
      name: iacgenie_iacgenie-backend
  ```

  This is the most common cause of "external network not found" errors when multiple compose files share a Docker network.

  - **Cloudflare tunnel credentials file path must be exact.** The `iacgenie-tunnel.json` file must be at `/etc/cloudflared/iacgenie-tunnel.json` (exact path). The `cloudflared tunnel create iacgenie-tunnel` command creates it at `~/.cloudflared/iacgenie-tunnel.json`. You MUST move it: `mv ~/.cloudflared/iacgenie-tunnel.json /etc/cloudflared/iacgenie-tunnel.json`. Also create the parent directory first: `mkdir -p /etc/cloudflared`.

  - **Gitea installation via `start` command.** Keycloak 26 uses the `start` command (not `start-prod`). The `--hostname` flag requires a full URL with protocol: `--hostname=http://auth.iacgenie.com` (not `--hostname auth.iacgenie.com`). The `OPENBAO_ADDR` env var defaults to HTTPS — force HTTP for local connections: `-address=http://127.0.0.1:8200`.

## When Ansible Is NOT the Right Tool

- **Infrastructure provisioning** (VM creation, VPC, load balancers) → Use Terraform
- **Kubernetes cluster management** → Use kops, eksctl, or managed service
- **Simple single-container deployments** → Manual Docker Compose is fine
- **Read-only configuration auditing** → Use ansible `--check` mode

On a single VM with Docker Compose services, Ansible alone is sufficient.
No Terraform needed.

## File Organization

Support files in `references/`:
- `references/ansible-project-structure.md` — Complete directory tree with file descriptions
- `references/ansible-playbook-examples.md` — Role and playbook code snippets (common, docker, openbao, nginx)
- `references/service-specific-patterns.md` — Per-service deployment patterns (Postgres, Redis, MinIO, OpenBao, Keycloak, Gitea, Nginx, Cloudflare, Docker Compose best practices)
- `references/secrets-collection-from-existing-infra.md` — Pattern for extracting credentials from existing `.env` files and populating Ansible inventory
- `references/credential-security-best-practices.md` — Credential management: never commit plaintext passwords to role defaults, proper Ansible Vault workflow, Keycloak/OpenBao-specific patterns
- `references/real-world-playbook-fixes.md` — Session-sourced playbook fixes (UFW allow policy, gitea rootless perms, Docker DNS, OpenBao storage/healthcheck, deploy user docker group, LightSerp env vars)
- `references/kanban-task-management.md` — Kanban command patterns, grand-task vs sub-task workflow, task states, board management, duplicate task resolution
- `references/pagezen-mock-server.md` — PageZen mock server capabilities, limitations, and production replacement pattern
- `references/phase-documentation-lifecycle.md` — 8-step workflow for creating INFRA-DESIGN.md, BACKUP.md, DEPLOY.md, README.md; stale data verification pitfall; common stale values table
- `references/env-per-service-architecture.md` — Per-service `.env` file architecture (fixes idempotency when multiple roles write to same `.env`)
- `references/ansible-dry-run-validation.md` — Complete checklist and commands for pre-deployment playbook validation
- `references/docker-network-segmentation.md` — 3-tier network segmentation (frontend/backend/messaging)
- `references/nginx-security-headers-hardening.md` — CSP, Permissions-Policy, CORS, X-Permitted-Cross-Domain-Policies hardening
- `references/full-infra-teardown-evaluation.md` — Full teardown & rebuild risk assessment
- `references/infra-teardown-troubleshooting.md` — Full teardown & redeploy troubleshooting
- `references/keycloak-26-migration.md` — Keycloak 26 command flag changes
- `references/keycloak-realm-provisioning.md` — Keycloak multi-tenant realm/roles/client automation via Ansible (multi-realm support with iacgenie + lightserp realms, OIDC client registration)
- `references/openbao-oidc-integration.md` — OpenBao OIDC auth backend integration with Keycloak (auth method config, role bindings, JWT claim mapping, Ansible automation)
- `references/nsqd-command-trap.md` — NSQD `--tcp-address` flag behavior
- `references/cloudflare-tunnel-auto-provisioning.md` — Automate Cloudflare tunnel login/create via Ansible with API token (replaces manual cloudflared commands)
- `references/post-deploy-playbook-pattern.md` — Two patterns: import_tasks in services.yml (unseal) vs standalone verification playbook (read-only health checks)
- `references/github-actions-cicd-patterns.md` — GitHub Actions workflow templates for deploy-and-verify and destroy-without-proxy with SSH, health checks, HTML reports, and email
- `references/security-stack-deployment.md` — ClamAV + ClamAV Web Client + CrowdSec + CrowdSec Web UI: compose template, nginx vHosts, network sharing pitfall, manual deploy script pattern
- `references/credential-audit-workflow.md` — Full credential audit procedure for running Docker infrastructure (Ansible templates → .env files → nginx configs → docker inspect → table compilation)
- **`references/compose-drift-detection.md`** — Detect drift between multiple compose architectures (ansible template vs hand-written unified), build drift matrices, identify breaking mismatches
- **`references/scoped-dry-run-and-routing-fallthrough.md`** — Scoped temporary-playbook dry-run (skip network-hanging shell tasks; interpret `changed=0` as possible design gap) + nginx routing-fallthrough root cause (subdomain with no server_name → catch-all `404 {"error":"Not found"}` → Cloudflare ERR_INVALID_RESPONSE; verify real backend port before editing)
- **`references/new-product-on-existing-infra.md`** — 6-phase workflow for designing and deploying a new product on existing shared infrastructure: infrastructure inspection, port allocation, service reuse decisions, resource planning, architecture deliverable creation, and repository setup

Scripts in `scripts/`:
- `scripts/verify-services.sh` — Pre-flight service state verification (containers, health, network, systemd, disk)
- `scripts/backup-restore.sh` — Comprehensive multi-service backup/restore (OpenBao, PostgreSQL, Gitea, Keycloak, MinIO, Redis, Prometheus, configs) with sealed-state handling and file-based tar/gpg pipeline

## Kanban Task Management for IAC Phases

This project uses a **grand-task → sub-task** wrapper pattern on the kanban board:

- **Grand-tasks** (`Phase N: <description>`) — Wrapper tasks that mark phase completion
- **Sub-tasks** (`Phase N.M: <description>`) — Actual implementation tasks (role creation, playbook writes)

**Workflow:**
1. Sub-tasks are implemented first (roles, playbooks, inventory changes committed)
2. Verify services are running on the target VM: `ssh user@vm 'docker ps --format "..."`
3. When sub-tasks are done, **do NOT re-run playbooks** — services are already deployed
4. Claim the grand-task and mark it complete: `hermes kanban claim <task_id>` then `hermes kanban complete <task_id>`
5. If there are uncommitted repo changes, commit and push separately

- **Kanban claim command:** `hermes kanban claim <task_id>` — **does NOT take `--board` flag**. It reads the current board from the environment. Set board first with `hermes kanban boards switch <slug>`.

**Verify before completing:** Always check service health on VM before marking a phase grand-task complete. If all expected containers are running and healthy, the phase is done — no need to re-run playbooks.

**Duplicate grand-tasks:** Old iterations leave duplicate grand-tasks (same title, different IDs). All must be completed individually. Use `hermes kanban unblock <id1> <id2> ...` then `hermes kanban complete <id1> <id2> ...`.

## Phase Documentation Lifecycle

Every Ansible IAC phase completion requires **four standard documentation artifacts**:

### Standard Deliverables

| File | Location | Purpose |
|------|----------|---------|
| `INFRA-DESIGN.md` | Root of unified infra repo | Full architecture: service matrix, networking, secrets, diagram, known issues |
| `BACKUP.md` | Root of unified infra repo | Backup schedules, restore procedures, disaster recovery, quick reference |
| `DEPLOY.md` | Ansible IAC repo (`iacgenie-deploy/`) | Deployment guide, service matrix, ingress, troubleshooting |
| `README.md` | Both repos | Quick start, service inventory, architecture overview |

### Workflow

1. **Unblock tasks** — `hermes kanban unblock <task_ids>`
2. **Discover live state** — SSH to VM, run `docker ps --format "table..."`, check ports, volumes, paths
3. **Create/update docs** — Use discovered state, NOT assumptions or stale references
4. **Commit to git** — Push to the Ansible IAC repo
5. **Complete tasks** — `hermes kanban complete <task_ids>`

### Critical Verification Pitfall

**ALWAYS verify ports and paths against live `docker ps` output** before writing or updating documentation. Common stale data:

- Service ports change between deploys (e.g., LightSerp API `8000` → `3071`, WebUI `3001` → `3070`)
- Data directories move between repo reorganizations (`iacgenie-unified-infra/` → `docker/iacgenie/`)
- Nginx vHost routing changes
- Docker volume mount paths shift

**Verification commands:**
```bash
# Verify all container ports and status
ssh user@vm 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'

# Verify compose file location
ssh user@vm 'find ~/ -name "docker-compose-unified.yml" -not -path "*cache*" 2>/dev/null'

# Verify data directories
ssh user@vm 'ls ~/docker/iacgenie/ | grep -E "data$" || echo "no data dirs"'
```

### Document Structure Templates

**INFRA-DESIGN.md** should include:
- Architecture diagram (ASCII)
- Ingress layer (Nginx + Cloudflare Tunnel)
- Service inventory (image, port, resources, health check, role)
- Secrets management (OpenBao paths, env vars, services using each)
- Network config (firewall, Docker network)
- Ansible IAC structure (repo layout, playbook execution flow)
- Known issues & resolutions table
- Change management workflow
- Future enhancements list

**BACKUP.md** should include:
- Backup schedule table (service, method, frequency, retention, location)
- Per-service automated backup commands
- Per-service restore procedures (detailed steps)
- Full disaster recovery procedure (prerequisites, step-by-step)
- Monitoring & verification commands
- Quick reference table

**DEPLOY.md** should include:
- Quick start (prerequisites, bootstrap, deploy, validate)
- Updated service matrix (image, port, resources, health check)
- Ingress (Nginx ports, vHost routing, Cloudflare config)
- Volume paths and Docker Compose file location
- Secrets management
- Troubleshooting (common issues with commands to fix)

## Workflow Integration

This skill fits into the broader workflow:
- After `production-readiness-audit` identifies infrastructure gaps
- After `dev-workflow` architecture review recommends IaC
- Before deployment automation — runs during the "infrastructure migration" phase
- Produces artifacts consumed by `github` (CI/CD workflow files) and `infra-consolidation`

## Dry-Run Validation Quick Reference

The dry-run procedure (`ansible-playbook --check --diff`) is covered in detail in the dry-run section above. Key reminders:
- Always run bootstrap.yml first, then services.yml, then site.yml
- Use `--diff` to see what would change
- Look for missing handlers, undefined variables, and placeholder secrets
- See `references/ansible-dry-run-validation.md` for the complete checklist
- For live-VM changes, scope the dry-run to a **temporary playbook** of only config-generating roles (there is no `--stop-at-task`; network-hanging shell tasks still execute and hang in dry-run) and treat `changed=0` as "live matches templates" — which can be a *design gap* (templates simply lack the routing), not "no drift". See `references/scoped-dry-run-and-routing-fallthrough.md`

## Related Skills

- `production-readiness-audit` — Identifies infrastructure gaps that this skill fixes
**Related skills:** `dev-workflow` — Architecture review findings feed into Ansible IAC planning; `ansible-iac-patterns` — Convert manual Docker infrastructure into production-grade Ansible IAC
- `infra-consolidation` — Post-IAC consolidation of Docker infrastructure
- `deep-research` — Research HA strategies and per-service patterns before implementing
- `openbao-access` — OpenBao CLI operations for secret access and management
- `keycloak` — Keycloak Docker troubleshooting and realm management
- `ansible-codebase-analysis` — Systematic workflow for reading and understanding an existing Ansible codebase (reverse of building IAC). Use when asked to "review the ansible code", "understand the ansible setup", or "map out the infrastructure from ansible".


## Consolidated Ansible Workflows (absorbed sibling skills)

> Sibling skills consolidated here; full detail retained in archived packages at `~/.hermes/skills/.archive/<name>/`.

### `ansible-codebase-analysis` — Read & document a codebase
Systematic workflow for reading, understanding, and documenting an existing Ansible codebase (playbooks, roles, inventory, secrets map). See archived `ansible-codebase-analysis/`.

### `ansible-playbook-troubleshooting` — Fix failing playbooks
Systematic diagnosis of ansible-playbook failures — missing vars, template errors, handler issues. See archived `ansible-playbook-troubleshooting/`.

### `ansible-service-audit` — Automated service audit
Full automated service audit: reads all Ansible files for a service and validates live state. See archived `ansible-service-audit/`.
