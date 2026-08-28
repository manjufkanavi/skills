# Kanban Board Audit Workflow

Systematic process for auditing kanban task claims against actual source code and VM state.

## When to Use

- User asks "how much is done" or "review implementation status"
- Before starting downstream work that depends on kanban task status
- Periodic health check of project progress
- When tasks may have been marked done by crashed workers without actual results

## Step 1: List All Tasks

```bash
hermes kanban boards current          # note current board
hermes kanban boards list             # see all boards
hermes kanban boards switch <slug>    # switch to target board
hermes kanban list --json             # get all tasks
```

**PITFALL:** `kanban list --json` returns tasks with key `id` (NOT `task_id`). Use:
```bash
hermes kanban list --json 2>/dev/null | python3 -c "
import json, sys
tasks = json.load(sys.stdin)
for t in tasks:
    print(f'  {t[\"id\"]:15s} [{t[\"status\"]:8s}] {t[\"title\"][:60]}')
"
```

## Step 2: Audit Each Phase

For each phase, check:

### Infrastructure (Phase 0)
- **Docker containers:** `ssh user@vm "docker ps --format 'table {{.Names}}\t{{.Status}}'"`
- **Service health:** `ssh user@vm "curl -f http://127.0.0.1:PORT/health"`
- **Models:** `ssh user@vm "curl -s http://127.0.0.1:11434/api/tags"`
- **Storage:** `ssh user@vm "curl -s http://127.0.0.1:9000/minio/health/live"`
- **Auth:** `ssh user@vm "curl -s http://127.0.0.1:8200/v1/sys/health"`
- **Nginx:** `ssh user@vm "cat /path/to/nginx/conf.d/*.conf"`
- **Tunnel:** `ssh user@vm "cloudflared tunnel list"`

### Code (Phase 1+)
- **Source files:** `find /path/to/project -type f -name "*.py" -o -name "*.ts" -o -name "*.tsx"`
- **API endpoints:** `ssh user@vm "curl -s http://127.0.0.1:PORT/openapi.json" | python3 -c "import json,sys; spec=json.load(sys.stdin); [print(f'  {m.upper():6s} {p}') for p,methods in sorted(spec.get('paths',{}).items()) for m in methods if m in ('get','post','put','delete')]"`
- **Docker compose:** `ssh user@vm "cat /path/to/docker-compose.yml"`

### Frontend
- **Container serving correct app:** `ssh user@vm "curl -s http://127.0.0.1:PORT/ | head -5"`
- **Source code exists:** check local repo for frontend files

## Step 3: Update Kanban Tasks

For each task, categorize as:
- **DONE** — actually implemented and verified
- **PARTIAL** — code exists but not working/configured
- **NOT DONE** — no evidence of work

### Updating Tasks

```bash
# For DONE tasks — try complete first
hermes kanban complete <task_id> "DONE: <verification details>"

# For PARTIAL/NOT DONE — add audit comment
hermes kanban comment <task_id> "AUDIT: <finding>"

# For GRAND tasks (PHASE N) — add summary comment
hermes kanban comment <grand_task_id> "AUDIT SUMMARY: <phase summary>"
```

### Handling Stuck Tasks

Some tasks get stuck in `todo` state and refuse all CLI operations:
- `kanban complete` → "unknown id or terminal state"
- `kanban reclaim` → "not running or unknown id"
- `kanban block` → "not blocked/scheduled?"

**Workaround:** Add an audit comment documenting the actual state, then proceed. Do not waste time trying to force-complete. The task will appear in the board but won't block future work.

```bash
hermes kanban comment <stuck_task_id> "AUDIT: DONE in reality. Task stuck in todo state - cannot complete via CLI."
```

## Step 4: Report

Summarize:
- Total tasks, done count, partial count, missing count
- Critical blockers preventing production use
- What's actually working vs what's claimed

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| `kanban list --json` key is `id` not `task_id` | Use `t["id"]` in python |
| SSH + python3 f-strings with quotes get mangled | Use `chr()` codes or avoid f-strings |
| `kanban complete` fails on stuck `todo` tasks | Add comment, proceed |
| `kanban show --json` returns empty for stuck tasks | Use `kanban list --json` and grep |
| Frontend container serving wrong app | Check `curl` response for actual content |
| n8n workflow JSON exists but not activated | Check n8n API for active workflows |
| Keycloak running but client not configured | Admin API returns 401 — verify client exists |
| OpenBao running but secrets not injected | Check env vars in docker-compose for CHANGE_ME defaults |
