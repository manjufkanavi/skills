# Infrastructure Task Verification Workflow

**Purpose:** Systematically verify that kanban board tasks marked "done" actually reflect working infrastructure on the target VM.

**When to use:** When reviewing Phase-level milestones, resolving "done but broken" tasks, or conducting infrastructure audits.

## Step-by-Step Workflow

### 1. List tasks from kanban board

```bash
hermes kanban boards switch <slug>
hermes kanban list --json | python3 -c "
import json, sys
tasks = json.load(sys.stdin)
for t in tasks:
    status = t['status']
    if status in ('done', 'blocked'):
        print(f'  [{status:8s}] {t[\"id\"]}  {t[\"title\"][:60]}')
"
```

### 2. SSH probe the VM

```bash
# Use the host alias (preferred) or IP address
ssh <host> 'echo OK'
# If alias fails, retry with IP:
ssh <user>@<ip> 'echo OK'
```

### 3. Verify each task against actual state

**Phase 1 (Health checks, resource limits, deploy script, backup):**
```bash
# All containers — health status
ssh <host> "for c in \$(docker ps -q); do
  name=\$(docker inspect --format '{{.Name}}' \$c)
  status=\$(docker inspect --format '{{.State.Health.Status}}' \$c 2>/dev/null)
  [ -n \"\$status\" ] && echo \"  \$name: \$status\"
done"

# Resource limits
ssh <host> "for c in \$(docker ps -q); do
  name=\$(docker inspect --format '{{.Name}}' \$c)
  mem=\$(docker inspect --format '{{.HostConfig.Memory}}' \$c 2>/dev/null)
  [ -n \"\$mem\" ] && [ \"\$mem\" != \"0\" ] && echo \"  \$name: \$(echo \$mem/1048576 | bc)MB\"
done"

# Deploy script
ssh <host> "ls -la /path/to/deploy.sh"

# Backup scripts
ssh <host> "ls -la /opt/backup/"
```

**Phase 2 (Backup cron):**
```bash
ssh <host> "crontab -l | grep -E 'backup|cron'"
```

**Phase 3 (CI/CD):**
```bash
# Gitea status
ssh <host> "curl -s http://127.0.0.1:3000/api/v1/version"

# Gitea runner
ssh <host> "systemctl status gitea-runner --no-pager | head -5"

# CI workflows
ssh <host> "find /home/<user>/projects/ -name '*.yaml' -path '*/.gitea/*' 2>/dev/null"
```

**Phase 4 (Monitoring):**
```bash
# Prometheus/Grafana containers
ssh <host> "docker ps --filter name=prometheus --filter name=grafana"
# If not running, check if config files exist:
ssh <host> "ls /path/to/prometheus.yml /path/to/grafana/dashboard.json 2>/dev/null"
```

**Phase 5 (Documentation):**
```bash
ssh <host> "ls -la /path/to/DEPLOY.md /path/to/BACKUP.md /path/to/INFRA-DESIGN.md 2>/dev/null"
```

### 4. Compare and document

Create a verification report:
- ✅ Verified — task matches actual state
- ❌ Not done — infrastructure doesn't match task description
- ⚠️ Partially done — some aspects work, others don't
- 📝 Note — task marked done but state is unclear

### 5. Archive stale duplicates

```bash
# Archive duplicate blocked entries when the done entry represents real work
hermes kanban archive t_xxx t_yyy t_zzz
```

## Common Findings (From Past Sessions)

| Finding | Frequency | Fix |
|---------|-----------|-----|
| Task marked done but container not running | Common | Archive task, recreate as blocked with verification gates |
| Duplicate tasks (same task in done + blocked) | Very common | Archive the blocked duplicate; done entry represents actual work |
| Cron job exists but notification broken | Occasional | Check SMTP config, log output, notification logic in script |
| Gitea runner in crash loop | Occasional | Check `/home/<user>/.runner` config, API token validity, runner logs |
| Phase 5 documentation not created | Always | Create markdown files with deployment, backup, and architecture details |

## SSH Authentication Tips

- Use host aliases from `~/.ssh/config`: `ssh newvm 'echo OK'`
- If alias fails, retry with IP: `ssh mkanavi@192.168.0.118 'echo OK'`
- First call in a session may fail if SSH agent is empty: `ssh-add key_file` then retry
- Always probe before launching batch commands
