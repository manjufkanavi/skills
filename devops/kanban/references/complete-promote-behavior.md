# Kanban `complete` vs `promote` Behavior

When completing many tasks, the `hermes kanban complete` command has non-obvious state
requirements that cause repeated failures.

## State Machine Quirks

### `complete` only works on `ready` tasks

A task must be in `ready` status to be completable via `hermes kanban complete`.
Tasks in `todo` or `blocked` status will produce:

    cannot complete t_xxx (unknown id or terminal state)

The error message is misleading — it says "unknown id" or "terminal state" but the
real cause is simply that the task is not yet `ready`.

### `promote` vs `complete`

| Task state | Command needed |
|------------|---------------|
| `todo`     | `promote --force <id>` then `complete <id>` |
| `blocked`  | `promote --force <id>` then `complete <id>` |
| `ready`    | Just `complete <id>` |
| `done`     | Already done |

### Promote accepts batch, complete does NOT

`promote` accepts multiple task IDs: `hermes kanban promote --force t_1 t_2 t_3`.
`complete` does NOT accept multiple IDs in one call — each must be called individually.

### Batch complete pattern

When completing many tasks, use this loop:

    for tid in t_1 t_2 t_3 t_4; do
      hermes kanban promote --force "$tid"
      hermes kanban complete "$tid" --result "summary"
    done

If you batch them on one line with `&&`, only the first `complete` will succeed —
the remaining will show "unknown id or terminal state". Rapid subsequent `complete`
calls on the same task ID namespace hit internal state consistency checks.
The fix: call `promote --force` on ALL tasks first, then complete each individually.

### Common failure pattern

    hermes kanban complete t_1 --result "a"  # SUCCEEDS
    hermes kanban complete t_2 --result "b"  # FAILS: "unknown id or terminal state"
    hermes kanban complete t_3 --result "c"  # FAILS: same
    hermes kanban complete t_4 --result "d"  # FAILS: same
