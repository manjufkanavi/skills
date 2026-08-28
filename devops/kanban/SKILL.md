---
name: kanban
description: "Kanban multi-agent workflow: orchestrator decomposition playbook, worker pitfalls and edge cases, task lifecycle, and recovery procedures."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing, worker, kanban-board]
    related_skills: [github, request]
updated: 2026-08-02
---

# Kanban — Multi-Agent Workflow Reference

Complete reference for the Hermes Kanban system: orchestrator decomposition, worker pitfalls, task lifecycle, and recovery.

## Contents

| Section | Description |
|---------|-------------|
| [1. Orchestrator](#1-orchestrator-decomposition-playbook) | Decomposition playbook + anti-temptation rules |
| [2. Worker](#2-worker-pitfalls-and-examples) | Pitfalls, examples, edge cases |
| [3. Common Patterns](#3-common-patterns) | Fan-out, pipeline, goal-mode, recovery |
| [4. Done-Task Verification](#4-verifying-done-tasks) | Infra audit workflow for tasks marked done by workers that crashed |
| 6. Board Troubleshooting | references/kanban-board-troubleshooting.md | Multi-board operations, switching, comparing, restructuring, graveyard pattern |
| 8. Board Audit Workflow | references/kanban-audit-workflow.md | Systematic process for auditing kanban task claims against actual source code and VM state |
| 7. Stuck Task Recovery | references/kanban-stuck-task-recovery.md | Tasks stuck in todo state refusing all CLI operations — workaround and prevention |
| 6. Infrastructure Verification | references/infra-verification-workflow.md | Step-by-step workflow for verifying "done" tasks against actual VM state |
| 6. Board Restructuring Reference | references/multi-board-restructure.md | Step-by-step guide for splitting merged boards, migrating tasks, and resetting states |
| 7. Stale Config Drift | references/stale-config-drift.md | Ansible template-correct-but-deployed-stale pattern, Redis case study, ad-hoc fix |

---

## 1. Orchestrator — Decomposition Playbook

When to use Kanban: multiple specialists needed, work should survive crashes, user might interject, parallel tasks, review expected, audit trail matters.

### Profiles Discovery (Step 0)

Always discover available profiles before planning:
- `hermes profile list` — table of profiles
- `kanban_list(assignee="name")` — sanity-check a name
- Just ask the user

**Critical:** The dispatcher silently fails to spawn unknown assignee names. Always assign to an existing profile.

### Anti-Temptation Rules

- **Do not execute the work yourself.** Create tasks for the right specialist.
- **Split multi-lane requests.** One card per lane, not bundled.
- **Run independent lanes in parallel.** No links needed.
- **Never create dependent work as independent ready cards.** Use `parents=[...]`.
- **If no specialist fits, ask the user.** Do not invent profile names.

### Decomposition

1. **Understand the goal** — ask clarifying questions
2. **Sketch the task graph** — draft out loud, map lanes to profiles, decide dependencies
3. **Create tasks and link** — use actual profile names, parent links for dependencies

```python
# Independent parallel tasks
t1 = kanban_create(title="research: cost comparison", assignee="researcher")
t2 = kanban_create(title="research: performance comparison", assignee="researcher")

# Dependent synthesis task
t3 = kanban_create(
    title="synthesize migration recommendation",
    assignee="analyst",
    parents=[t1["task_id"], t2["task_id"]]
)

# Final report
t4 = kanban_create(
    title="draft decision memo",
    assignee="writer",
    parents=[t3["task_id"]]
)
```

### Goal-Mode Cards

For long, multi-step cards, use `goal_mode=True`:

```python
kanban_create(
    title="Translate docs to French",
    body="Every page translated, no English left, links intact.",
    assignee="translator",
    goal_mode=True,
    goal_max_turns=15
)
```

---

## 2. Worker — Pitfalls and Examples

### Workspace Handling

| Kind | What it is | How to work |
|---|---|---|
| `scratch` | Fresh tmp dir, yours alone | Read/write freely; GC'd when archived |
| `dir:<path>` | Shared persistent directory | Treat like long-lived state |
| `worktree` | Git worktree | Commit work here |

### Good Handoff Shapes

**Coding task:**
```python
kanban_complete(
    summary="shipped rate limiter — token bucket, keys on user_id",
    metadata={
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14, "tests_passed": 14,
        "decisions": ["user_id primary, IP fallback for anonymous"]
    }
)
```

**Review task (review-required):**
```python
kanban_comment(body="review-required: rate limiter shipped, 14/14 tests pass")
kanban_block(reason="review-required: rate limiter shipped, needs eyes on user_id/IP fallback")
```

### DO NOT
- Call `delegate_task` instead of `kanban_create` — they serve different purposes
- Call `clarify` as a headless worker — use `kanban_comment` + `kanban_block` instead
- Modify files outside `$HERMES_KANBAN_WORKSPACE`
- Complete a task you didn't actually finish — block it instead
- Mark an infrastructure task `done` without verifying **state persistence** across a reboot — if services go down after a restart, the task can't be un-marked (all terminal states are immutable). See `references/infra-drift-diagnosis.md`.

### Adding Mandatory Rules to Tasks

When all tasks on a board need a standard rule (e.g., "plan → approve → execute"), comment on each task using a variable to avoid shell quoting issues:

```bash
RULE="MANDATORY RULE: All work on this task MUST use Claude Code plan mode: (1) Plan the approach first, (2) Get approval before executing any changes, (3) Execute only after approval."
hermes kanban comment t_xxx "$RULE"
```

### Kanban Task Body Template

Every infrastructure task should follow the body template in `references/kanban-task-body-template.md`. Key sections:

1. **Goal** — One-line summary of what the task achieves
2. **Steps** — Numbered action steps (3-5 per task)
3. **MANDATORY RULE** — Every infra task must: deploy+verify, document in INFRA-DESIGN.md, commit+push to git
4. **Files to modify** — List of files that will change

This ensures consistent, actionable tasks that workers can execute without ambiguity. See `references/kanban-task-body-template.md` for the full template with examples.

**Shell pitfall:** Never put single quotes directly inside `--body` or comment text on the CLI. Bash will fail with `unexpected EOF while looking for matching '```. Use escaped double quotes `\\\"` or the variable approach above.

### Verification Gates for Infrastructure Tasks

Every infrastructure task body MUST include verification gates that prove the system works after a reboot, not just while it's running. Use this template:

```
VERIFICATION GATES (must pass before marking done):
1. Reboot test: sudo reboot; wait 2min; docker inspect <container> --format '{{.State.Status}}' → must show 'running'
2. Health check: docker inspect <container> --format '{{.State.Health.Status}}' → must show 'healthy'
3. Restart policy: docker inspect <container> --format '{{.HostConfig.RestartPolicy.Name}}' → must show 'unless-stopped' or 'always'
4. Data persistence: verify data survived restart (e.g., db query returns rows, redis keys still exist)
5. Service accessibility: curl -f http://127.0.0.1:PORT/health → must return HTTP 200
```

If the task body doesn't include verification gates, add them before marking done. A task is NOT done until ALL gates pass after a reboot test.

#### Deployment Script Verification Patterns

When verifying infrastructure deployed via docker-compose, the deploy script must handle two non-obvious patterns:

**Container name mapping** — Docker compose services with explicit `container_name` overrides break simple prefix naming. If a compose file has `container_name: iacgenie-searxng` for service `lightserp-searxng`, a deploy script that builds names via `iacgenie-${service}` will produce `iacgenie-lightserp-searxng` which doesn't exist. **Always use a hardcoded map** in deployment scripts:
```bash
declare -A CONTAINER_MAP=(
    [lightserp-searxng]=iacgenie-searxng
    [lightserp-nsqd]=iacgenie-nsqd
    [lightserp-pagezen]=iacgenie-pagezen
)
get_container_name() { echo "${CONTAINER_MAP[$1]:-$1}"; }
```

**Per-service timeout configuration** — Services like Keycloak (with realm import) take far longer to start than Docker's default `start_period`. Use a per-service timeout map:
```bash
declare -A HEALTH_TIMEOUT=(
    [keycloak]=300 [gitea]=180 [postgres]=120
    [redis]=60 [minio]=120 [openbao]=120
)
```

**Integration health checks** — Post-deploy verification must check cross-service connectivity, not just individual health. Different containers have different tool sets:
- Alpine: `wget` ✅, `curl` ❌, `bash` ❌
- Gitea (BusyBox): `wget` ✅, `bash -c 'echo >/dev/tcp/...'` ✅ for TCP port checks (not HTTP spider on raw DB ports)
- Node.js containers: `curl` ✅, `wget` ❌
- Keycloak (Java/JBoss): neither `curl` nor `wget` — use `bash -c 'echo >/dev/tcp/localhost:8080'`

For the full deployment script template with all these patterns, see `scripts/deploy-verification-pattern.sh`.

### Retry Diagnostics

Read prior runs' `outcome`/`summary`/`error` before retrying:
- `timed_out` → chunk the work
- `crashed` → reduce memory footprint
- `spawn_failed` → profile config issue, ask human
- `blocked` → check comment thread for unblock reason

For the full crash diagnosis tree (API failure vs protocol violation vs PID death), see `references/kanban-worker-crash-diagnosis.md`.

When a profile is broken and the user does the work manually:
- Mark the task `done` after confirming artifacts exist on disk
- The kanban board may now have stale parent references — remove them with `kanban unlink`
- Create new downstream tasks if the manual work was a prerequisite for other tasks
- Always verify artifacts before marking done: check file paths exist and have content

When verifying infrastructure-deployment tasks (Docker, systemd, nginx, TLS), don't just check files — SSH into the target and verify services are actually running and reachable. The full audit checklist is in `references/kanban-verify-done-task.md`.

---

### Common Patterns

| Pattern | Description |
|---------|-------------|
| Fan-out + Fan-in | N research cards → 1 synthesis card depending on all of them |
| Pipeline with Gates | planner → implementer → reviewer — each stage parents to previous |
| Migration Decomposition | Foundation → Parallel App Migrations → Validation Fan-in → Cutover |
| Research Project | Literature → Corpus → Retrieval → Baseline → Data Gen → Fine-tune → Evaluate → Write |

See `references/multi-board-restructure.md` for the complete workflow for splitting merged boards into focused ones (infra vs research, etc.), migrating tasks, handling immutable state resets, and the graveyard board strategy.
See `references/migration-decomposition-pattern.md` for a production-grade kanban decomposition pattern used for infrastructure consolidation projects.
See `references/research-project-kanban.md` for kanban task decomposition, body templates, and dependency patterns for academic/research projects.
See `references/kanban-worker-crash-diagnosis.md` for a diagnostic tree distinguishing API failures, protocol violations, and PID death in kanban workers.
See `references/phase-based-infra-planning.md` for phase-based task decomposition (Phase 0→5: Stabilize → Harden → Backup → CI/CD → Monitor → Document) used when planning infrastructure + CI/CD setups across multiple repos.
See `references/kanban-verify-done-task.md` for the step-by-step audit workflow to verify that tasks marked "done" by crashed workers actually produced working infrastructure before proceeding with downstream tasks like cutover.
See `references/deployment-verification-patterns.md` for container name mapping pitfalls, per-service timeout configuration, integration health check patterns with correct tools per container type, and crash detection in deploy scripts.
See `references/infra-drift-diagnosis.md` for kanban-vs-actual-state drift diagnosis, immutable terminal states, and the verification gates prevention pattern.
See `references/infra-verification-workflow.md` for the step-by-step workflow to systematically verify that "done" tasks actually reflect working infrastructure on the target VM (SSH probe → Docker state comparison → documentation check → archive stale duplicates).
See `references/kanban-board-troubleshooting.md` for multi-board operations: switching, comparing boards, old vs. fresh board patterns, and the graveyard board strategy.

### Recovery Actions

When a worker keeps crashing:
1. **Reclaim** — reset to ready
2. **Reassign** — switch to different profile
3. **Change model** — edit profile config, reclaim to retry

### CLI Equivalents

| Tool | CLI |
|------|-----|
| `kanban_list` | `hermes kanban list` |
| `kanban_list(assignee="name")` | `hermes kanban list --assignee <name>` |
| `kanban_show` | `hermes kanban show <id> --json` |
| **PITFALL: Task IDs are hash-based** — IDs look like `t_dfe79f21`, NOT `t_1`, `t_2`. Always get IDs from `hermes kanban list` output. `hermes kanban show t_1` will fail with "no such task". |
| **PITFALL: `kanban show --json` may return empty** — If `show <id> --json` returns nothing, use `kanban list --json` and grep for the task title to get the full record including body. |
| `kanban_complete` | `hermes kanban complete <id> --summary "..."` |
| **PITFALL: `kanban status` action does NOT exist** — There is no `hermes kanban status` action. To mark a task *done*, use `hermes kanban complete <id>` (optionally `--summary "..."`). Running `hermes kanban status <id> done` errors with `invalid choice: 'status' (choose from ...)`. Other status transitions use `block`/`unblock`/`edit`/`promote`/`archive` — never `status`. |
| `kanban_block` | `hermes kanban block <id> "reason"` |
| `hermes kanban create` | `hermes kanban create "title" --assignee <profile> --body "<body>" --priority <N>` |
| `kanban_link` | `hermes kanban link <parent_id> <child_id>` |
| `kanban_unlink` | `hermes kanban unlink <task_id> <parent_id>` |
| `kanban_assign` | `hermes kanban assign <task_id> <profile>` |
| `kanban_reclaim` | `hermes kanban reclaim <task_id>` |
| `kanban_reassign` | `hermes kanban reassign <task_id> <new_profile>` |
| `kanban_comment` | `hermes kanban comment <task_id> "message"` |
| `kanban_unblock` | `hermes kanban unblock <task_id>` |
| `kanban_promote` | `hermes kanban promote <task_ids...>` — list of IDs, space-separated |

**Completing grand-tasks with done sub-tasks.** When a Phase N (or Milestone X)
grand-task has all its sub-tasks already marked `done`, completing the
grand-task is a formality — no actual work is needed. Check that all sub-task
IDs show `status=done`, then complete the grand-task in a single call:
`hermes kanban complete t_parent_id t_parent2_id t_parent3_id`. This avoids
unnecessary triple-claiming and execution loops for identical wrapper tasks.

**Completing a grand-task cascades its sub-tasks back to `ready`.** When you
complete a PHASE / milestone grand-task, the kanban CLI resets its child
sub-tasks to `ready` (so they can be re-executed). If you want the sub-tasks
to stay marked `done`, **re-complete them *after* the grand-task completion**:
`hermes kanban complete t_child1 t_child2 ...` immediately following the
grand-task call. Otherwise the sub-tasks reappear as `ready` even though the
underlying work is finished and verified — a common source of "my done tasks
disappeared" confusion. Order matters: grand-task first, then re-complete
children.

**Batch completing identical grand-task duplicates.** Decomposition sometimes
creates 2–3 copies of the same Phase N grand-task. Check all variants have the
same title. If so, complete them all together — they represent the same work.
Do NOT claim and execute each separately.

### Board Management

| Action | CLI |
|--------|-----|
| List boards | `hermes kanban boards list` |
| Create board | `hermes kanban boards create <name>` |
| Rename board | `hermes kanban boards rename <old-slug> <new-name>` (display name only; slug unchanged) |
| Switch board | `hermes kanban boards switch <slug>` |
| Current board | `hermes kanban boards current` |

**When creating a new infra plan, always rename the board** from "project-work" to something specific: `hermes kanban boards rename project-work <project-name>`.

- **`--body` single-quote trap** — When passing `--body` via CLI, single quotes inside the value break bash parsing (`unexpected EOF while looking for matching '`). Use escaped double quotes `\\\\\\\"` instead, or rewrite the text to avoid single quotes entirely (e.g., use `->` instead of `'->'`, or `don't` → `do not`). Test the command in a dry-run first if the body is long.
- **`--body` ampersand trap** — The `&` character in heredocs or `--body` values is interpreted by bash as a backgrounding operator, causing foreground commands to fail with "Foreground command uses '&' backgrounding". When task bodies contain `&` (e.g., in URLs, commands, or text), either: (a) avoid heredocs entirely and pass `--body` directly on the command line, or (b) write the body to a temp file and use `--body "$(cat /tmp/task_body)"` — but test that the temp file approach works before using it at scale. The safest pattern: create kanban tasks one at a time with `--body` on the command line, avoiding heredocs entirely.
- **`--body` complex text workaround** — When task bodies contain URLs with `@`, colons, parentheses, or other shell-special characters, the safest approach is to write the body to a temp file and pass it via command substitution:
  ```bash
  cat > /tmp/task_body.md << 'EOF'
  Steps:
  1. SSH to VM and run: cloudflared tunnel login
     (Creates ~/.cloudflared/cert.pem — requires Cloudflare CLI auth)
  EOF
  hermes kanban create "Y.4 Create Cloudflare tunnel credentials" --body "$(cat /tmp/task_body.md)" --priority 1
  ```
  The heredoc delimiter must be single-quoted (`'EOF'`) so bash does NOT expand variables inside it. Always use heredoc (`cat >`), not `echo`, for multi-line content. Clean up temp files after use.

`--priority` accepts integer values: `1` (highest) through `5` (lowest). NOT string labels — `--priority high` will error with `invalid int value`.

- **`--board` does NOT exist on `hermes kanban create`** — Tasks always go to the *active* board. To create on a specific board, switch first: `hermes kanban boards switch <slug>`, then `hermes kanban create ...`. There is no `--board` flag on create. This is a frequent mistake: `hermes kanban create "title" --board myboard` errors with `unrecognized arguments: --board`.
- **`boards create` vs `boards rename`** — `boards rename old new` keeps the old slug (display name only changes). `boards create new` creates a fresh board with the new slug. After a rename, always verify with `hermes kanban boards list` to confirm the actual slug. Use `boards create` when you need a genuinely new board; use `boards rename` when just changing the display name of an existing one.
- **Board rename preserves the slug** — `hermes kanban boards rename <old-slug> <new-name>` changes the display name only. The underlying slug (used by `switch`, `list`, and internal references) stays unchanged. After renaming, always verify with `hermes kanban boards list` to see the actual slug. Always use the slug with `switch`, never the display name. This is a common source of "board does not exist" errors after a rename.

- **`kanban link` is positional: `hermes kanban link <parent_id> <child_id>`** — After creating tasks with dependencies, use `hermes kanban link <parent_id> <child_id>` to set up dependency chains. NOT `--parent`. This is a frequent mistake source: `hermes kanban link t_xxx --parent t_yyy` will error with `unrecognized arguments: --parent`.

- **PITFALL: `--parent` flag on `hermes kanban create` does NOT work** — Passing `--parent` when creating a task silently fails: the task is created with empty `parents: []`. After creation, `kanban link` will then fail with "would create a cycle" (even though no links exist). This is a **known bug** in the kanban CLI.

  **Correct pattern:** Always create tasks first, THEN link them:
  ```bash
  # Step 1: Create parent task
  hermes kanban create "title of parent task" --priority 1
  
  # Step 2: Create child task (NO --parent flag)
  hermes kanban create "title of child task" --priority 2
  
  # Step 3: Link them after both exist
  hermes kanban link <parent_id> <child_id>
  ```

  **If you already created tasks with `--parent`:**
  ```bash
  # Verify: the task will show parents: []
  hermes kanban show t_xxx --json | python3 -c "import json,sys; t=json.load(sys.stdin); print(t['parents'])"
  # Link manually
  hermes kanban link <parent_id> <child_id>
  ```
- **`kanban list --json` feeds into `python3 -m json.tool`** — Raw kanban list output is verbose; pipe through Python for readability.
- **PITFALL: `kanban list --json` key is `id` not `task_id`** — When parsing `kanban list --json` output in python, the task identifier key is `id` (not `task_id`). Use `t["id"]` to get the task ID. This is a frequent mistake: `t["task_id"]` raises `KeyError`.
- **PITFALL: `kanban list --json` does NOT surface `parents`** — After a *successful* `kanban link <parent> <child>`, `kanban list --json` still reports `parents: null` / `None` for *every* task. The link IS stored (the link command prints `Linked t_xxx -> t_yyy`), but the list output does not render the parent relationship. Do **not** read `parents=None` as "the link failed" — it does not mean that.
  - Verify a parent chain via the `kanban link` command's own `Linked ...` output. `kanban show <id> --json` also returns empty for hash-based IDs, so treat it as a last resort.
  - To enumerate a grand-task's sub-tasks, filter `kanban list --json` for tasks whose title matches the phase pattern (e.g. `"3.1"`, `"PHASE 3"`); there is no usable `children` field (it is `null`).
- **Before creating sub-tasks, check the active board for existing cards with the same title.** A board frequently already contains sub-tasks from an earlier session (sometimes created hours ago, with richer bodies). Creating new ones produces duplicates. Inspect the board first with `kanban list --json`; keep the cards that already have well-formed bodies and **archive the redundant new ones** (`kanban archive <id>`) instead of leaving duplicate cards as dead artifacts. This is the reverse of the "archive duplicate stale tasks" pattern — here the *newly created* cards are the redundant copies to discard.
- **PITFALL: SSH + python3 f-strings with quotes get mangled** — When running python3 via SSH with f-strings containing quotes (e.g., `f'  {w.get("name",?)}'`), bash interprets the quotes and corrupts the python code. Workaround: use `chr()` codes instead of quotes, or avoid f-strings entirely, or write the python script to a temp file and run it locally.
- **Profile names must exist** — `hermes profile list` must show the assigned name; silently fails on unknown names.
- **Default tasks are `blocked`** — New tasks show as `blocked` by default. Use `hermes kanban unblock` or `hermes kanban reclaim` to start work.
- **One `link` call per parent** — To link multiple parents, call `kanban link` separately for each parent, not all at once.
- **`kanban list` output includes task IDs as `t_xxx`** — Always capture the returned task ID from `kanban create` for use in `link` and other operations.
- **`--body` for kanban create supports multi-line text** — Use `--body "Scope: ...\n\nDeliverables:\n1. ..."` for detailed task descriptions. This becomes the task body visible to workers.
- **`kanban unblock` before claiming work** — Tasks default to `blocked` status. Use `hermes kanban unblock <task_id>` before a worker can start. The worker cannot proceed while blocked.
- **`kanban complete --summary` captures context** — Always include a summary with verification results when completing. Future agents reading the board will see what was actually done.
- **Scope recurring monitors to active tasks, not the full board** — When scheduling a cron job to monitor kanban progress, target only the actively running tasks the user cares about (e.g., specific migration tasks). A full-board scan every 10 minutes is noisy and rarely useful. Ask the user what to monitor, or scope to the subset of tasks marked `running`. A general daily summary (e.g. morning report) is fine; real-time polling should be narrow.

- **All terminal states are immutable: `done`, `blocked` too** — Not just `archived`. Once a task reaches `done` (completed) or `blocked` (blocked), you CANNOT revert it to `ready` or reset its status. `hermes kanban reclaim` refuses with "not running or unknown id", and `hermes kanban block/edit` also refuse. The only option is to create new replacement tasks and leave the old ones as dead artifacts on the board. This means **always verify actual infrastructure state before marking any infra task as `done`** — if services go down after a reboot, you can't un-mark the task. See `references/infra-drift-diagnosis.md` for the full pattern.
- **Fresh board strategy when old tasks are stuck** — When a kanban board has accumulated old tasks in terminal states (done/blocked) and you need a clean start, don't fight with immutable tasks. Create a new board (rename `default` or `project-work` to the clean name), create fresh tasks with proper verification gates, and leave old tasks alone. The old tasks will be visible but dead weight. See `references/infra-drift-diagnosis.md`.

- **Manual file cleanup can cause mass rebase conflicts** — When corpus cleanup or similar manual file operations are done locally while the remote has different changes, `git pull --rebase` may produce 45+ rename/delete conflicts. See `references/research-corpus-validation.md#git-rebase-after-manual-cleanup` for the resolution pattern.

- **Gitea Actions prerequisites must complete before CI/CD tasks** — Gitea tasks (PHASE 3.1-3.8) have hard dependencies: runner must be installed and registered before runner tokens are useful, tokens must exist before CI workflows can reference them, and the Actions feature flag must be enabled in `app.ini` (enabled=False by default) before any API/CLI Actions operations work. Block downstream tasks on upstream completion, and check `ENABLED = true` in the `[actions]` section of app.ini before attempting any Actions operations.

- **Archive duplicate stale tasks instead of leaving them** — When the same phase/task appears both as `done` and `blocked` (from failed worker retries), the `done` entry usually represents actual completed work. **Archive the stale duplicates** (all variants) with `kanban archive t_xxx` rather than leaving them as dead artifacts. They pollute the board and create confusion about what's actually in progress. Always verify actual state before deciding which entry is the real one.

- **Workflow task decomposition pattern (lint → build → test → deploy per project)** — When creating CI/CD workflow tasks, decompose per-project × per-stage: each project needs its own lint, build, test, deploy task. This produces clean parallel lanes (all lints can run first, all builds next) rather than a single monolithic CI task. Assign to `developer` profile; each task body should include: target repo name, workflow file path (`.gitea/workflows/<name>.yaml`), steps, and expected gates.

- **Dual-remote push with non-existent Gitea repo** — When pushing to GitHub + Gitea dual remotes, if the Gitea repo doesn't exist on the remote, the push fails with "repository not found." **Fix: create the repo on Gitea first** (via Gitea web UI or API) before pushing. The GitHub push succeeds independently. The dual-remote sync hook reports Gitea failure as non-blocking but you should verify both remotes have the commit.

- **Board slug vs display name mapping** — Boards may have a different slug than their display name. The `boards list` output shows: `SLUG | NAME | COUNTS`. Always use the **slug** (left column) with `switch`, `list`, and internal references. Display name changes via `boards rename` only affect the NAME column — the slug is immutable. Common trap: renaming a board to "infra" still gives the slug `project-work` or whatever it was originally. Always verify with `boards list` after any rename.

- **Task marked "done" ≠ work actually completed** — Tasks can be manually set to `done` status when a worker crashes (multiple attempts) and the user marks it done without actual results. The task's `events` may show `crashed`/`gave_up` with no summary, but `status=done`. **Always verify** by checking the task's `events` for crashes with no summary, and independently verify the actual artifacts (e.g., containers running, config deployed, services responding) before treating a "done" task as a valid dependency for downstream work like cutover. See `references/kanban-verify-done-task.md` for the audit workflow.

- **Board listing requires switching first** — `hermes kanban list` only lists the *active* board. There is NO `--board` flag. To inspect another board, run `hermes kanban boards switch <slug>` first, then `hermes kanban list --json`. This is a frequent mistake: `hermes kanban list --board default` errors with `unrecognized arguments: --board`. See `references/kanban-board-troubleshooting.md` for the full multi-board workflow.

- **PITFALL: Tasks can get stuck in "todo" state and refuse all operations** — A task may show `status=todo` in `kanban list` but `kanban complete`, `kanban reclaim`, and `kanban block` all fail with "unknown id or terminal state" / "not running or unknown id" / "not blocked/scheduled?". This is a known CLI bug where the task enters an internal state that prevents manipulation. **Workaround (best effort first):** Try archiving the task's children — this can cause the parent to transition from `todo` to `ready`, at which point `kanban complete` succeeds. If no children exist or archiving doesn't help, add an audit comment documenting the actual state and proceed. Do not waste time trying to force-complete. The task will appear in the board but won't block future work. If it becomes a problem, create a fresh replacement task on a new board. See `references/kanban-stuck-task-recovery.md` and `references/kanban-audit-workflow.md` for the full pattern.

- runbook, INFRA-DESIGN.md update)\\n- See `references/openbao-repair-pattern.md` for the full OpenBao repair and hardening playbook.\\n\\n- **User preference: sequential execution over parallel delegation.** When the user says "execute one task at a time" or "no sub agents", respect it completely. Do NOT propose parallel subagent delegation. The kanban board is for task tracking; the orchestrator executes tasks sequentially unless the user explicitly asks for parallel work. This is a HARD constraint from the user, not a suggestion.\\n\\n- **Service security audit methodology.** When auditing infrastructure services for hardening, use the structured approach in `references/service-security-audit.md`: review Docker Compose config, Ansible role templates, backup scripts, network isolation, security capabilities, and produce findings in Critical/Medium/Good categories with a fix plan. See the full reference for the audit template.\\n\\n- **Board audit workflow.** When auditing kanban task claims against actual source code and VM state, use the structured process in `references/kanban-audit-workflow.md`: list tasks, audit each phase (infrastructure, code, frontend), update tasks with audit comments, and report completion status. See the full reference for the step-by-step process.

## Board Troubleshooting

### Board switching is MANDATORY before listing

There is NO `--board` flag on `hermes kanban list`. To inspect a board other than the active one:

```bash
# Switch to the target board first
hermes kanban boards switch <slug>

# THEN list tasks
hermes kanban list --json
### Task Commenting

When adding comments to tasks:

```bash
hermes kanban comment t_<task_id> "Summary of changes"
```

**Pitfall:** The `hermes kanban comment` command passes the body through bash, which interprets special characters like `$`, `(`, `)`, `|`, etc. If your comment contains YAML snippets, shell commands, or variable references with `$`, they will be mangled.

**Workaround:** Keep comments concise and avoid embedding code blocks. For detailed technical notes, write to a file and reference it, or use the `edit` action to update the task body instead.

Shows each board's slug, name, and count by status (blocked/done/ready/todo/archived).

### Comparing boards efficiently

When comparing two boards (old planning board vs. fresh board), list tasks with a concise summary. Note: `assignee` can be `None` — always use `.get('assignee') or '(unassigned)'` to avoid `TypeError`:

```bash
hermes kanban list --json 2>/dev/null | python3 -c "
import json, sys
tasks = json.load(sys.stdin)
for t in tasks:
    assignee = t.get('assignee') or '(unassigned)'
    print(f'  [{t[\"status\"]:8s}] P{t[\"priority\"]} {assignee:20s} {t[\"title\"][:70]}')
"
```

### Old vs. fresh boards

Common pattern: the original planning board has coarse-grained PHASE tasks (e.g., PHASE 3) that are hard to track, while a fresh board has granular sub-tasks (e.g., PHASE 3.1, 3.2, 3.3). The fresh board typically has more completed tasks and is the source of truth.

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
