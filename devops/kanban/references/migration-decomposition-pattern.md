# Kanban Migration Decomposition Pattern

Real-world decomposition for infrastructure consolidation projects.
Derived from production session planning LightSerp + IacGenie unified infra migration.

## Task Graph (7 tasks, 4 phases)

```
Phase 1 — Foundation
  └─ t_ac6abfeb (Foundation) ← assignee: devops ✅ DONE

Phase 2 — Parallel Migration
  ├─ t_de0fc365 (IacGenie Migration) ← assignee: developer 🔄 RUNNING
  └─ t_3f8ddc5a (LightSerp Migration) ← assignee: developer 🔄 RUNNING

Phase 3 — Validation & Cutover (fan-in of all Phase 2)
  ├─ t_acce55b2 (Security) ← assignee: devops ← parents: Foundation + both migrations
  ├─ t_0869f23f (Testing) ← assignee: tester ← parents: Foundation + both migrations
  └─ t_32792b79 (Documentation) ← assignee: product_manager ← parents: Foundation + both migrations

Phase 4 — Cutover
  └─ t_132fa2fe (Cutover) ← assignee: devops ← parents: Security + Testing + Documentation
```

## Decomposition Principles

1. Foundation first — infrastructure MUST exist before app migration. No parallel foundation/migration.
2. Parallelize application work — IacGenie and LightSerp migrations are independent once foundation is done.
3. Validation is a fan-in — security, testing, and documentation all depend on both migrations completing.
4. Cutover is the final gate — only one task left, depends on ALL validation completing.

## CLI Commands Used

```bash
hermes kanban create "Foundation: ..." \
  --assignee devops --body "..." --priority 1

hermes kanban create "IacGenie Migration: ..." \
  --assignee developer --body "..." --priority 1

hermes kanban create "LightSerp Migration: ..." \
  --assignee developer --body "..." --priority 1

hermes kanban link t_de0fc365 --parent t_ac6abfeb
hermes kanban link t_3f8ddc5a --parent t_ac6abfeb

hermes kanban create "Security: ..." --assignee devops --priority 1
hermes kanban create "Testing: ..." --assignee tester --priority 1
hermes kanban create "Documentation: ..." --assignee product_manager --priority 1

hermes kanban create "Cutover: ..." --assignee devops --priority 1

hermes kanban list
hermes kanban show t_xxx --json 2>&1  # detailed per-task status
hermes kanban list --json | python3 -m json.tool  # readable full board
```

## Task Body Template

Each kanban create --body should include:
1. Scope — what needs to be done (1-2 sentences)
2. Deliverables — numbered list of concrete outputs
3. Dependencies — which tasks must complete first
4. Testing — how success is verified
5. Acceptance Criteria — measurable conditions for completion

## Monitoring Pattern

For recurring task monitoring, scope the cron job to specific task IDs rather than the full board:

```
hermes kanban show t_xxx --json 2>&1
```

A full `hermes kanban list` every 10 minutes is noisy. Target the 1-3 active tasks and post only on changes. Use a daily summary for the full board overview.

## Worker Failure Recovery

Observed failure modes:
- **Crash (pid not alive)** — worker process died without calling kanban_complete/block
- **Protocol violation** — worker exited cleanly (rc=0) but forgot to report completion
- **Diagnosis**: `hermes kanban show t_xxx --json` → check `runs[].outcome` and `runs[].error`
- **Recovery**: `hermes kanban unblock t_xxx` to retry (auto-promotes after gave_up)