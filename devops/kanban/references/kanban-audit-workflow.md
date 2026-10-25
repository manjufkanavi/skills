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

### Detecting Demo Stubs and Placeholder Work (Local Code Verification)
For locally-cloned projects, a task can be marked `done` while the code contains only a **demo stub** — surface wiring that looks complete but does nothing real. Auth/OIDC flows are the most common place this hides (easy to fake with a demo path). Before trusting a `done` task, grep the source for stub markers:
```bash
# Demo / placeholder patterns => "not actually done"
grep -rnE "loginDemo|demo-token|demo_user|For the preview|here we finalize" <srcdir>
grep -rnE "CHANGE_ME|TODO|FIXME|placeholder" <srcdir>/api

# A real auth flow needs a backend route handler, not just a frontend button
grep -rnE "@router\.(get|post)\(\"/keycloak/(login|callback|logout)\"" <srcdir>/api

# Frontend callback must actually exchange the code for a token, not just loginDemo()
grep -rnE "exchange|/auth/exchange" <srcdir>/webui/src/app

# Confirm new routes are registered in the app on import
hermes kanban ...   # see references/kanban-board-troubleshooting.md for route inspection
```

A `done` task is **NOT done** if its only evidence is: a frontend button calling `loginDemo()` or a stub callback; backend files present but with no route handlers wired into the app (`main.py`); or secrets still at default `CHANGE_ME` values. Add an audit comment and do not treat it as a valid dependency for downstream work.

### Android App Tasks — Verifying Screens Are Reachable (Not Just Committed)

For UI-feature tasks, "done" is often satisfied by **domain/logic code + tests** that never became a real screen. Engines, schedulers, and ledgers live in `:core`/`:domain` with unit tests but no UI; committing them does NOT fulfill a task that asks for a screen. The navigation graph is the source of truth for what is reachable, not git log or test pass count.

```bash
# 1. Count actual screens (exclude build/ — it holds compiled dex of every screen ever built)
find . -name "*Screen*.kt" -not -path "*/build/*"

# 2. Read the navigation graph — every composable() block there is a reachable screen
cat <app>/src/main/.../navigation/AppNavHost.kt   # or any NavHost file
# If Quiz/Profile/Rewards have no composable() route, that feature exists nowhere in the running app.

# 3. Cross-reference docs screen inventory (e.g. docs/ia-and-screens.md)
#    Spec lists S1..S9 but NavHost has only Home + Lesson => those screens were never built as UI.

# 4. Empty modules produce zero screens: a feature module with build.gradle.kts but no src .kt
find <feature-module>/src -name "*.kt"   # empty dir => the screen was never written
```

A UI task is **NOT done** when: logic exists in `:core`/`:domain` with tests but no `*Screen.kt`; NavHost has fewer routes than the spec's screen inventory; or a feature module exists on disk but contains no source. Report reachable-screen count vs spec, not git log or test counts.

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
