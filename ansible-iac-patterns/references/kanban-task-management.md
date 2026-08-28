# Kanban Task Management Patterns

## Board Setup

```bash
hermes kanban boards list          # See all boards and slugs
hermes kanban boards switch infra  # Switch to 'infra' board
```

**Important:** Display names ≠ slugs. Always use the slug, not the display name.

## Task Creation and Completion

```bash
# Create a task
hermes kanban create --title "Phase X: Description" --assignee devops

# Claim a task (no --board flag — reads current board)
hermes kanban claim <task_id>

# Complete tasks (single or multiple)
hermes kanban complete <task_id>
hermes kanban complete <id1> <id2> <id3>

# Block/unblock/schedule
hermes kanban block <task_id>
hermes kanban unblock <task_id>
hermes kanban schedule <task_id>
```

## Grand-Task vs Sub-Task Pattern (IAC Projects)

Phase tasks use a two-level hierarchy:

| Level | Example | Purpose |
|-------|---------|---------|
| Grand-task | `Phase 3: Application Services` | Wrapper that marks phase completion |
| Sub-task | `Phase 3.1: Gitea role` | Actual implementation work |

**Workflow:**
1. Sub-tasks are implemented (roles, playbooks, configs written)
2. Verify services are running on the target VM
3. When sub-tasks are done, **do NOT re-run playbooks** — services are already deployed
4. Claim and complete the grand-task as a marker

**Verify before completing:** Check service health on VM:
```bash
ssh user@vm 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```

If all expected containers are running and healthy, the phase is done.

## Task States

| State | Symbol | Meaning |
|-------|--------|---------|
| ✅ done | ✓ | Task completed |
| ▶ ready | ▶ | Ready to claim, unassigned |
| ◻ todo | ◻ | Planned, not ready yet |
| ⊘ blocked | ⊘ | Blocked (not blocking progress if stuck) |
| - Archived | archived | Removed from board |

## Duplicate Grand-Tasks

Old iterations often leave duplicate grand-tasks (same title, different IDs).
All duplicates must be completed individually — `hermes kanban complete` accepts multiple IDs.

**Resolution pattern:**
```bash
# 1. List all tasks to find duplicates
hermes kanban list --json | python3 -c "import json,sys; tasks=json.load(sys.stdin); [print(f'{t[\"id\"]} {t[\"status\"]} {t[\"title\"]}') for t in tasks if 'phase 5' in t.get('title','').lower()]"

# 2. Unblock all blocked duplicates
hermes kanban unblock <id1> <id2> <id3> ...

# 3. Complete all of them
hermes kanban complete <id1> <id2> <id3> ...
```

## Task Context

```bash
# Read what a task contains
hermes kanban context <task_id>

# Show task with comments and events
hermes kanban show <task_id>

# List all tasks on current board
hermes kanban list
```

## Stats

```bash
# Per-status and per-assignee counts
hermes kanban stats
```
