# Kanban Stuck Task Recovery

## Symptom

Task shows `status=todo` in `kanban list` but all operations fail:
- `hermes kanban complete t_xxx` → "cannot complete t_xxx (unknown id or terminal state)"
- `hermes kanban reclaim t_xxx` → "cannot reclaim t_xxx (not running or unknown id)"
- `hermes kanban unblock t_xxx` → "cannot unblock t_xxx (not blocked/scheduled?)"

## Root Cause

The kanban CLI has a bug where tasks can enter an internal state that prevents manipulation. The task is visible in listings but not in any valid state machine transition.

## Recovery Playbook (try in order)

### Method 1: Archive children to unstick parent (most effective)

When a parent task is stuck in `todo` and has child tasks, **archiving the children** can cause the parent to transition from `todo` → `ready`, at which point `kanban complete` succeeds:

```bash
# Step 1: Check if the stuck task has children
hermes kanban show t_stuck_parent --json | python3 -c "import json,sys; t=json.load(sys.stdin); print(t['task'].get('children',[]))"

# Step 2: Archive all children
for child_id in t_child1 t_child2; do
  hermes kanban archive "$child_id"
done

# Step 3: Verify parent transitioned to 'ready'
hermes kanban list  # parent should now show 'ready'

# Step 4: Complete the parent
hermes kanban complete t_stuck_parent --summary "Work completed: <details>"
```

**Why this works:** The kanban state machine appears to reset parent state when all children are removed from the board. The parent transitions from an internal "stuck todo" state to a valid "ready" state.

### Method 3: Complete the ready parent to cascade children (when stuck tasks are children)

When the stuck tasks are the **children** of a parent that is itself in a valid `ready` (or `todo`) state — not another terminal state — **completing the parent** cascades the stuck children back into a valid `ready` state, after which `kanban complete` succeeds on each child:

Step 1: Confirm the parent (grand-task / milestone) is in a valid state via `hermes kanban list --json`.
Step 2: Complete the parent: `hermes kanban complete <parent_id> --summary "Phase complete: <verification details>"`.
Step 3: The stuck children cascade to a valid `ready` state — complete them **ONE AT A TIME**, one CLI invocation each.

Why this works: completing a milestone/grand-task resets its child sub-tasks to `ready`. When a child was stuck in the CLI's internal `status: None` limbo, the cascade resets it to a valid machine `ready` state that `complete` accepts.

**Do NOT batch the child completions.** Parallel `complete` calls collide on the SQLite write lock — only the first succeeds and the rest fail with 'unknown id or terminal state'. Complete them sequentially, one CLI invocation at a time.

### Method 2: Comment and proceed (fallback)

If Method 1 fails (no children, or archiving doesn't trigger transition):

```bash
hermes kanban comment t_xxx "Work completed: <summary>. Task stuck in CLI limbo — cannot complete via CLI."
```

### Method 3: Fresh board (last resort)

When the board has accumulated too many stuck tasks:

```bash
hermes kanban boards rename default <old-name>
hermes kanban boards create fresh-board
hermes kanban boards switch fresh-board
# Recreate only the tasks that still need work
```

## What NOT to do

- **Do NOT use `kanban edit --status`** — the `edit` command only works on already-done tasks to set `--result`/`--summary`/`--metadata`. It does not accept `--status` and will error.
- **Do NOT try `kanban block` on todo tasks** — they are not in a blocked state, so this fails with "not blocked/scheduled?"
- **Do NOT waste time** trying to force-complete stuck tasks through repeated attempts. The work status is what matters, not the board state.

## Prevention

- Mark tasks `done` immediately after completing work, even if the summary is brief
- Avoid leaving tasks in `todo` state for extended periods without progress
- If a task has been sitting as `todo` for more than a few sessions, consider archiving and recreating
- When archiving dead artifacts, do it in one batch — it's more reliable than trying to complete each individually
