# Kanban Worker Crash — Diagnosis Tree

When a kanban task crashes repeatedly, there are two distinct failure patterns. Diagnose before taking action.

## Pattern A: API / Provider Failure

**Symptom:** Every run fails within seconds (10-15s), no output produced, same error each time.

**How to detect:** Run `hermes kanban log <task_id>` — look for `API call failed` / HTTP errors in the logs.

**Common causes:**
1. **Wrong model/provider for the profile** — The profile's `model` is set to a local model but `provider` points to an API endpoint that doesn't support it (e.g., `local/Qwen3.6-35B-A3B-UD-MLX-4bit` configured under `provider: gemini`).
2. **Missing API key** — `hermes config show -p <profile>` to check keys.
3. **Endpoint down / model not found** — HTTP 404 on the provider endpoint.

**Fix:**
```bash
# Check the profile config
hermes config show -p <profile_name>

# Fix model or provider
hermes model -p <profile_name>
# Or edit config directly
hermes config edit -p <profile_name>
```

**Verify:** `hermes --profile <name> chat -q "test"` before retrying the task.

## Pattern B: Protocol Violation

**Symptom:** Worker runs for ~60s, produces output, then exits with "worker exited cleanly (rc=0) without calling kanban_complete or kanban_block — protocol violation".

**How to detect:** `hermes kanban log <task_id>` shows `protocol_violation` with `exit_code: 0`.

**Root cause:** The agent produced its output but the kanban protocol runner didn't receive the completion signal. Usually caused by:
1. **Context window overflow** — the response was too long and got truncated before the protocol handshake
2. **Worker killed by timeout** — the runner process was terminated before it could finish
3. **Agent crash mid-response** — OOM, memory pressure, or other termination

**Fix:**
1. **Chunk the work** — break the task body into smaller steps
2. **Increase max turns** — if the task needs many turns
3. **Use goal_mode** for complex multi-step work
4. **If the work actually completed** (check filesystem for artifacts), manually mark done: `hermes kanban complete <id>`

## Pattern C: PID Not Alive

**Symptom:** "pid XXXX not alive" — the worker process was terminated externally.

**How to detect:** `hermes kanban log <task_id>` shows `crashed` with `pid XXXX not alive`.

**Common causes:**
1. **System OOM killer** — especially on memory-constrained machines
2. **Agent running out of context** — model fails to produce output
3. **Profile has no working model** — falls through to default which may not be available

**Fix:** Same as Pattern A — check the profile's model/provider config first.

## Decision Flow

```
Task crashes repeatedly?
  │
  ├── Log shows API errors (HTTP 400/404/500)?
  │     → Pattern A: Fix profile model/provider config
  │
  ├── Log shows protocol_violation + exit_code 0?
  │     → Pattern B: Chunk the work; check for context overflow
  │
  ├── Log shows "pid XXXX not alive"?
  │     → Pattern C: Check system resources (OOM?) and profile config
  │
  └── Unknown?
        → Run: hermes kanban log <task_id> | tail -40
           Then check: hermes config show -p <assignee_profile>
```

## Post-Fix: Recovering the Board

After fixing the root cause:
1. **Reclaim** the task to clear the crash count: `hermes kanban reclaim <id>`
2. **Unblock** if still blocked: `hermes kanban unblock <id>`
3. Let the dispatcher re-spawn the worker, OR manually start: `hermes -p <profile> chat -q "work kanban task <id>"`

## Manual Work Outside Kanban

When a profile is broken and the user does the work manually:
- Mark the task `done` after confirming artifacts exist on disk
- The kanban board may now have stale parent references — remove them with `hermes kanban unlink`
- Create new downstream tasks if the manual work was a prerequisite for other tasks
- Always verify artifacts before marking done: check file paths exist and have content
