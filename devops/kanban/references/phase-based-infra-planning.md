# Phase-Based Infrastructure Planning Pattern

Use this pattern when the user asks to:
- "plan infrastructure for X"
- "create an infra plan"
- "set up CI/CD for X"
- "unify my services"
- "create a reliable infra + CI/CD setup"

## When to Use

This pattern applies to **infrastructure assessment and planning tasks** where the user has:
1. Multiple repositories (source code repos + infra/config repos)
2. A target VM or cloud environment
3. Operational concerns (stability, backups, CI/CD, monitoring)

This is distinct from architecture review (code-focused) and production readiness audit (security/reliability scoring). This is a **planning + task decomposition** pattern.

## Step-by-Step Procedure

### Step 1: Discover Repositories

Find and read ALL related repositories:
```bash
# Typical locations on user's machine
ls ~/workspace/
ls ~/workspace/git_workspace/
ls ~/.hermes/git_clone_dir/

# Key repos to look for:
# - <project> — main app source code
# - <project>-unified-infra — docker-compose, nginx, scripts, tests
# - lightserp / iacgenie / terragenius — platform-specific repos
```

**Read first:**
- README.md (overview, architecture)
- docker-compose*.yml (service definitions)
- .env (shared credentials — redact in logs)
- nginx configuration files

### Step 2: SSH to VM and Audit Live State

Connect to the target VM and capture the actual running state:
```bash
ssh -i ~/.ssh/<key> <user>@<vm>
```

**Capture:**
- `uname -a` — OS, kernel version
- `free -h` — RAM available
- `df -h` — disk usage (critical for Docker)
- `docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"` — all containers
- `docker system df -v` — disk usage by Docker
- `systemctl status` — background services
- Nginx config: `cat /etc/nginx/conf.d/*.conf`
- Cloudflare tunnel: `cloudflared tunnel list`

**Identify critical issues:**
- Containers that are Exited with data at risk (Postgres, Redis, MinIO, Gitea)
- Services in restart loops (OpenBao, etc.)
- Zombie containers (Exited/created, wasting space)
- Orphan volumes (unused Docker volumes)
- Missing services that should be running

### Step 3: Synthesize into Phased Plan

Create `INFRA-CICD-PLAN.md` with:

**Section 1: Current State Assessment**
- Table of all services with actual status
- Critical issues with severity
- Repository inventory
- VM resource summary

**Section 2: Architecture Target**
- ASCII diagram of desired state
- Service dependency order
- Nginx routing table

**Section 3: Deployment Strategy**
- Health check gates
- Crash recovery policy
- Security hardening measures

**Section 4: Backup Strategy**
- What gets backed up (Postgres dump, Redis RDB, MinIO objects, OpenBao raft, Keycloak realm-export, configs)
- Where (local + Google Drive via rclone)
- When (daily cron, specific times)
- Verification (test restore, checksums)

**Section 5: Gitea Mirroring**
- Mirror direction (GitHub → Gitea or bidirectional)
- Runner setup

**Section 6: CI/CD Pipeline**
- Trigger conditions
- Lint commands per project
- Test matrix
- Build + deploy job

**Section 7: Monitoring**
- Services to enable (Prometheus, Grafana)
- Scrape targets

**Section 8: Task Breakdown**
- Phase-based kanban cards (see Phase Structure below)

### Phase Structure

| Phase | Purpose | Priority | Typical Assignee |
|-------|---------|----------|------------------|
| Phase 0: Stabilize | Fix broken services, clear zombies, resolve data loss risks | 1 (highest) | devops |
| Phase 1: Harden | Health checks, restart policies, resource limits, deployment scripts | 1 | devops |
| Phase 2: Backup | rclone setup, backup scripts, cron jobs, test restore | 1-2 | devops |
| Phase 3: CI/CD | Runner setup, mirroring, workflows, disable old CI, smoke tests | 1-2 | devops + developer |
| Phase 4: Monitor | Prometheus, Grafana, alerting rules | 2 | devops |
| Phase 5: Document | Update design docs, cross-repo READMEs, runbooks | 1-2 | architect + devops + developer |

### Step 4: Create Kanban Tasks

Create ALL tasks in one batch using `hermes kanban create`. Each task needs:
- **Title:** `PHASE X.Y: Short description`
- **Assignee:** `devops`, `developer`, or `architect`
- **Priority:** 1 (highest) to 4 (lowest)
- **Body:** See format below

**Task body format:**
```markdown
Current: <actual state from Step 2 audit>

Steps:
1. <specific SSH/command step>
2. <follow-up step>
3. <verification>

Deliverables: <what "done" looks like>
Verify: <one-liner verification command>
```

**Task creation script pattern:**
```bash
hermes kanban create "PHASE X.Y: Title" \
  --assignee devops \
  --priority 1 \
  --body "Current: ...\n\nSteps:\n1. ...\n\nDeliverables: ...\nVerify: ..."
```

Create all tasks, then unblock them in bulk:
```bash
# Unblock all Phase X tasks
for task in t_xxx t_yyy t_zzz; do
  hermes kanban unblock $task
done
```

### Step 5: Verify Board State

```bash
hermes kanban list | grep "PHASE 0\|PHASE 1\|PHASE 2\|PHASE 3\|PHASE 4\|PHASE 5"
```

Expected: All tasks showing status (blocked → running → ready), correct assignees, correct phases.

## Pitfalls

- **Don't skip the VM audit.** Planning from repo files alone misses the live state (stopped containers, disk usage, zombie services). Always SSH and capture `docker ps -a` and `df -h`.
- **Capture exact container names.** Docker container names may have `-1` suffix from previous compose projects. Always verify with `docker ps -a` before referencing container names in task bodies.
- **Redact secrets in kanban bodies.** Never put passwords or tokens in kanban task bodies. Reference paths or use `[REDACTED]` placeholders.
- **Create all tasks in one batch.** Don't create phase by phase — the user needs to see the full picture immediately.
- **Unblock all tasks immediately.** Kanban creates tasks as `blocked` by default. Unblock them right after creation.
- **Use priority 1 for critical.** Phase 0 tasks (fixing broken services) should always be priority 1.
- **Reference actual file paths.** When creating tasks, use actual paths (e.g., `/home/mkanavi/workspace/git_workspace/iacgenie-unified-infra/docker-compose-unified.yml`) not relative paths.

### Board Setup

```bash
# Create and name the board for this project (default is "project-work")
hermes kanban boards rename project-work <project-name>

# Switch to it (if needed)
hermes kanban boards switch <project-name>

# Verify
hermes kanban boards list
```

### Task Removal (Scope Changes)

When the user drops scope (e.g., "don't need Prometheus/Grafana"), **do NOT leave tasks blocked forever** — remove them:

```bash
hermes kanban complete t_xxx --summary "Out of scope — user dropped from scope"
```

Do NOT create Phase 4 tasks unless the user explicitly confirms monitoring is in scope. Confirm scope for monitoring/observability before creating those tasks.

### Scope Negotiation

When the user says "monitoring is not needed", immediately remove all Phase 4 tasks (Prometheus, Grafana, alerts) from the board. Mark them done with "deferred" reason in the summary.

## Example: Typical Phase 0 Tasks

| Task | Title | Priority | Assignee |
|------|-------|----------|----------|
| PHASE 0.1 | Fix PostgreSQL — Start, verify data, set health check | 1 | devops |
| PHASE 0.2 | Fix Redis — Start, verify data, set health check | 1 | devops |
| PHASE 0.3 | Fix OpenBao — Fix permissions, start, verify unseal | 1 | devops |
| PHASE 0.4 | Fix SearXNG / Other services | 2 | devops |
| PHASE 0.5 | Clean up zombie containers | 2 | devops |
| PHASE 0.6 | Clean up orphan volumes | 3 | devops |

## Files Produced

1. `INFRA-CICD-PLAN.md` — Comprehensive plan document (repository-specific)
2. Kanban board — All tasks with phase-based structure
3. (Subsequent) Implementation produces: scripts, configs, workflows, documentation
