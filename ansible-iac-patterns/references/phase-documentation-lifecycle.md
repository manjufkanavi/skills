# Phase Documentation Lifecycle

## When to Use

After completing an Ansible IAC phase (phases 1-5), create/update the four standard documentation artifacts before marking the phase grand-task complete.

## Standard Deliverables

| File | Location | Size Range |
|------|----------|-----------|
| `INFRA-DESIGN.md` | Root of unified infra repo | 10-15KB |
| `BACKUP.md` | Root of unified infra repo | 10-15KB |
| `DEPLOY.md` | Ansible IAC repo root | 6-8KB |
| `README.md` | Both repos | 3-6KB each |

## Step-by-Step Workflow

### 1. Unblock Kanban Tasks

```bash
hermes kanban unblock <id1> <id2> <id3> ...
```

### 2. Discover Live Infrastructure State

ALWAYS get actual state from the VM. Never assume ports, paths, or configurations.

```bash
# Container state and port bindings
ssh mkanavi@192.168.0.118 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

# Docker compose file location
ssh mkanavi@192.168.0.118 "find ~/ -name 'docker-compose*.yml' -not -path '*cache*' -not -path '*/LightSerp/*' 2>/dev/null"

# Data directory structure
ssh mkanavi@192.168.0.118 "ls ~/docker/iacgenie/ 2>/dev/null | head -30"

# Ansible inventory
ssh mkanavi@192.168.0.118 "cat ~/projects/iacgenie-deploy/inventory/hosts.yml 2>/dev/null"

# Playbook structure
ssh mkanavi@192.168.0.118 "ls ~/projects/iacgenie-deploy/playbooks/ 2>/dev/null"

# Role count
ssh mkanavi@192.168.0.118 "ls ~/projects/iacgenie-deploy/roles/ 2>/dev/null"
```

### 3. Create INFRA-DESIGN.md

Include these sections in order:
1. Title, date, author, target VM info
2. Architecture diagram (ASCII)
3. Ingress layer (Nginx reverse proxy, Cloudflare Tunnel, DNS)
4. Service inventory table (image, port, resources, health check)
5. Secrets management (OpenBao paths, env var mapping table)
6. Network configuration (firewall rules, Docker network)
7. Ansible IAC structure (repo layout, playbook execution flow)
8. Known issues & resolutions table
9. Change management workflow
10. Future enhancements list

### 4. Create BACKUP.md

Include these sections:
1. Backup schedule table (service, method, frequency, retention, location)
2. Per-service automated backup commands
3. Per-service restore procedures (step-by-step with commands)
4. Full disaster recovery procedure (prerequisites, 6-step recovery)
5. Monitoring & verification commands
6. Quick reference table

### 5. Update DEPLOY.md

Update these specific sections:
1. Service matrix — verify ports against `docker ps`
2. Ingress — update hostname-to-port mapping
3. Docker Compose file location — verify actual path
4. Volume paths — list all mount points
5. Troubleshooting — update with latest issues and fixes

### 6. Create README.md Files

**iacgenie-deploy/README.md:**
- Quick start (clone, bootstrap, deploy, validate)
- Target environment info
- Playbook table
- Service inventory
- Documentation links

**iacgenie-unified-infra/README.md:**
- Purpose (tracks live infra configuration)
- Directory structure
- Infrastructure snapshot (11 services, ingress)
- Documentation links
- Ansible IAC commands
- Phase status table

### 7. Commit and Push

```bash
cd ~/projects/iacgenie-deploy && git add -A && git commit -m "Phase N: Complete documentation" && git push
```

### 8. Complete Kanban Tasks

```bash
hermes kanban complete <grand_task_id> <sub_task_ids...>
```

## Verification Checklist

Before declaring phase complete:
- [ ] All 4 docs created/updated
- [ ] Ports match `docker ps` output
- [ ] File paths match actual disk layout
- [ ] Services table has all 11 services
- [ ] OpenBao paths documented
- [ ] Docker volume paths correct
- [ ] Nginx vHost routing correct
- [ ] Cloudflare Tunnel mentioned
- [ ] Backup procedures documented
- [ ] Troubleshooting section has commands
- [ ] Git committed and pushed
- [ ] Kanban tasks completed

## Common Stale Data Patterns

| Stale Item | Old Value | Verify With |
|------------|-----------|-------------|
| LightSerp API port | `8000` | `docker ps` → `3071` |
| LightSerp WebUI port | `3001` | `docker ps` → `3070` |
| SearXNG port | `8080` | `docker ps` → `8081` |
| PageZen port | `8081` | `docker ps` → `8076` |
| NSQD API port | `4150` | `docker ps` → `8071` |
| Compose file location | `iacgenie-unified-infra/` | `find ~/ -name "docker-compose-unified.yml"` |
| Data directory | varies | `ls ~/docker/iacgenie/` |
