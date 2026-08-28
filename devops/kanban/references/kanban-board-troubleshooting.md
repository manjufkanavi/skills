# Kanban Board Troubleshooting

## Multi-Board Operations

### Board switching is MANDATORY before listing

There is NO `--board` flag on `hermes kanban list`. To inspect a board other than the active one:

```bash
# Switch to the target board first
hermes kanban boards switch <slug>

# THEN list tasks
hermes kanban list --json
```

This is a common source of errors: `hermes kanban list --board default` fails with `unrecognized arguments: --board`.

### Listing board counts without full task dump

```bash
hermes kanban boards list
```

This shows each board's slug, name, and count by status (blocked/done/ready/todo/archived).

### Comparing boards efficiently

When comparing two boards (e.g., an old planning board vs a fresh one), list tasks with a concise summary:

```bash
# After switching boards
hermes kanban list --json 2>/dev/null | python3 -c "
import json, sys
tasks = json.load(sys.stdin)
for t in tasks:
    assignee = t.get('assignee') or '(unassigned)'
    print(f'  [{t[\"status\"]:8s}] P{t[\"priority\"]} {assignee:20s} {t[\"title\"][:70]}')
"
```

Note: `assignee` can be `None` — always use `.get('assignee') or '(unassigned)'` to avoid `TypeError` when sorting or joining.

## Board Anatomy Patterns

### Old vs. fresh boards

A common pattern: the original planning board has coarse-grained PHASE tasks (e.g., PHASE 3) that are hard to track, while a fresh board has granular sub-tasks (e.g., PHASE 3.1, 3.2, 3.3). The fresh board typically has more completed tasks and is the source of truth.

| Aspect | Old (default) board | Fresh (project-work) board |
|--------|---------------------|---------------------------|
| Phase granularity | Broad (PHASE 0–5) | Granular (PHASE 0.1–5.4) |
| Task count | Often stale blockers from failed workers | Clean, current work state |
| Completion rate | Lower (tasks block but work may have moved on) | Higher (matching actual progress) |

### Recommended pattern when scope changes

1. **Don't fight immutable tasks** — once `done` or `blocked`, you cannot revert. Leave them as dead artifacts.
2. **Create a fresh board** — `hermes kanban boards rename default <new-name>` or `hermes kanban boards rename project-work <project-name>`.
3. **Migrate scope** — create new tasks on the fresh board with proper verification gates; don't try to relink or reuse old tasks.
4. **The old board becomes a graveyard** — visible but dead weight. This is expected.
