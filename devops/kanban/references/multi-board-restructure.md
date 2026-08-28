# Multi-Board Restructuring

When a single board has mixed workstreams (e.g., infra tasks + research tasks) that need to be separated into focused boards, follow this workflow.

## Problem

A board accumulates tasks from different domains. After work progress, the board becomes cluttered with tasks from multiple phases and domains.

## Solution: Split into focused boards

### Step 1: Create the new board

```bash
# Create a fresh board for the new workstream
hermes kanban boards create solvarch
```

### Step 2: Identify task categories

List all tasks and categorize them by domain. Note: old tasks from previous planning boards are dead artifacts — their state is immutable.

```bash
# List current board tasks with categorization
hermes kanban list --json | python3 -c "
import json, sys
tasks = json.load(sys.stdin)
for t in tasks:
    # Categorize by title patterns
    if 'PHASE' in t['title']: phase = 'infra'
    elif any(kw in t['title'] for kw in ['Research', 'RAG', 'corpus']): phase = 'research'
    else: phase = 'other'
    print(f'  [{t[\"status\"]:8s}] {phase} {t[\"title\"][:70]}')
"
```

### Step 3: Switch to target board and recreate tasks

Tasks created on the active board go to that board. **There is no `--board` flag on `hermes kanban create`** — you must switch first.

```bash
# Switch to the NEW board
hermes kanban boards switch solvarch

# Create each task on the new board
hermes kanban create "Task title" --assignee <profile> --priority <N> --body "body text"
```

**Preserving state:**
- `kanban create` defaults tasks to `blocked` state
- To mark as `done`: create → `hermes kanban complete <id> --summary "done reason"`
- To mark as `ready` (unblocked): create → `hermes kanban unblock <id>`
- To mark as `blocked`: leave as created (default)

**⚠️ One-time mistake:** The only way to "mark done" a task that shouldn't be done is to create a replacement. Once `kanban complete` is called, it's irreversible — states are immutable.

### Step 4: Reset done tasks to blocked

Infra tasks that are `done` on the new board need to be reset. Since states are immutable, you must create **fresh copies** of each task.

```bash
# On the infra board, create fresh copies with correct initial state
hermes kanban boards switch <infra-slug>

# Create each infra task fresh (new IDs, no link to old)
hermes kanban create "PHASE 0.1: Fix PostgreSQL" --assignee devops --priority 1 --body "original body..."
```

Old tasks remain as dead artifacts — they will show up in listings but should be ignored. This is the expected **graveyard pattern**.

### Step 5: Add standard rules to all new tasks

When all tasks on a board need a mandatory rule (e.g., "plan → approve → execute"), comment on each task:

```bash
RULE="MANDATORY RULE: All work on this task MUST use Claude Code plan mode: (1) Plan the approach first, (2) Get approval before executing any changes, (3) Execute only after approval."

# Comment on each task ID
hermes kanban comment t_xxx "$RULE"
hermes kanban comment t_yyy "$RULE"
```

**Shell pitfall:** If the rule text contains single quotes, bash parsing fails with `unexpected EOF while looking for matching '`. Use the variable approach above or rewrite without single quotes.

## State Mapping Guide

When recreating tasks from an old board:

| Original Status | What it means | New Board State | Action |
|-----------------|---------------|-----------------|--------|
| `done` | Completed | Must be reset | Create new task (starts blocked) |
| `blocked` | Unstartable | Keep blocked | Create new task (starts blocked by default) |
| `ready` | Unblocked, ready to work | Keep ready | Create new task → `hermes kanban unblock <id>` |
| `todo` | Unblocked, ready to work | Keep ready | Create new task → `hermes kanban unblock <id>` |

## Task Count Sanity Check

After restructuring, verify both boards:

```bash
# Check infra board
hermes kanban boards switch <infra-slug>
hermes kanban list --json | python3 -c "import json,sys; t=json.load(sys.stdin); [print(f'  {t[\"status\"]:8s}') for t in t]" | sort | uniq -c

# Check research board
hermes kanban boards switch solvarch
hermes kanban list --json | python3 -c "import json,sys; t=json.load(sys.stdin); [print(f'  {t[\"status\"]:8s}') for t in t]" | sort | uniq -c
```

## Graveyard Board Strategy

When renaming an old board, you don't need to delete it. Just rename it:

```bash
hermes kanban boards rename old-slug _graveyard-name
```

The old board becomes visible but is dead weight. Users can ignore it. The kanban CLI has no "delete board" command.