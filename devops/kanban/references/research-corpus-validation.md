# Research Project — Corpus Validation & Manual Work Patterns

When corpus collection is done manually (outside the kanban agent workflow), use this pattern to integrate it into the board.

## The Pattern

Research projects often collect corpus data via non-kanban tools (web scraping, Tiny Fish API, wget, manual curation). This work exists **outside** the kanban system but **blocks** downstream kanban tasks.

### Step 1: Do the collection manually
Use whatever tool works (Tiny Fish, browser scraping, APIs). Save output to a known path.

### Step 2: Verify before creating validation tasks
```bash
ls -la /path/to/corpus/
wc -l /path/to/corpus/*.md | tail -1  # total line count
head -20 /path/to/corpus/README.md     # scope doc
```
If nothing exists, don't create a validation task yet — redo the collection.

### Step 3: Create a corpus validation task (not a "corpus curation" task)
The validation task checks:
- **Document count and sizes** — are there enough docs?
- **Pillar/service coverage** — do all 6 AWS pillars appear?
- **Quality filtering** — are there docs < 500 chars (likely too short)?
- **Metadata completeness** — is the category_index.json accurate?
- **Duplicate detection** — any near-duplicates?

### Step 4: Link validation to downstream tasks
```
hermes kanban link <validation_id> <retrieval_pipeline_id>
hermes kanban link <validation_id> <baseline_harness_id>
```
Both retrieval and baseline can run in parallel after validation.

## Why Not Create a "Corpus Curation" Task?

A "corpus curation" task tells the agent to collect documents. If the agent's API is broken (wrong profile config, missing keys), it will crash repeatedly while the user already has the data. The correct split is:
- **Manual collection** (user does it with whatever tool works)
- **Kanban validation** (agent checks quality, coverage, indexing)

## Phantom Parent Chains

When parent tasks are archived/deleted (common with crashed tasks that get GC'd), children retain links to them. This causes:
- `claim_rejected: parents_not_done` — the dispatcher checks parents that no longer exist
- Tasks stuck in blocked state with no way to progress

**Fix:** Remove stale links after the parent is no longer relevant:
```bash
hermes kanban unlink <child_id> <parent_id>
```
Or restructure the board by archiving stale tasks and creating clean replacements.

## After Manual Work: Board Reconciliation

When the user has done the work manually:
1. **Verify artifacts exist** on disk before marking the task done
2. **Mark done**: `hermes kanban complete <id>` with a summary of what was produced
3. **Check downstream dependencies** — archived phantom parents may block children
4. **Create/fix the dependency chain** — link new tasks properly
5. **GC stale workspaces** — `hermes kanban gc` cleans up orphaned workspace directories

## Example: Solvarch Board State

After restructuring, the board looked like:

```
✓ t_d53b8d36  done      Lit review (RAG, code LLMs, PEFT, IaC)
◻ t_31eb3204  todo      Corpus validation (670 docs collected)
  ├─▶ t_d6c6f93b  blocked  Retrieval pipeline
  └─▶ t_af41a41c  blocked  Baseline eval harness
        │
        ▼
◻ t_5d7215db  blocked   Synthetic data generation
        │
        ▼
◻ t_ea8c023e  blocked   LoRA/QLoRA fine-tuning
        │
        ▼
◻ t_7b59ec37  blocked   Solvarch benchmark
        │
        ▼
◻ t_b059af8f  blocked   Dissertation manuscript
```

Key insight: literature review was done manually (agent couldn't run due to profile config), but the board state was updated to reflect reality. Corpus validation became the active task.

## Git Rebase After Manual Cleanup

When corpus validation (or any file cleanup) is done manually and the remote already has different changes, `git pull --rebase` may produce 45+ rename/delete conflicts if both sides operated on the same files (local renamed to backup, remote deleted outright).

**Resolution:** List conflicts with `git status --short | grep "rename/delete" | awk '{print $2}'`. For each path, check if the file exists on disk (`[ -f "$path" ]`). If yes, `git add "$path"` (keep local version). If no, `git rm --cached "$path"` (clear remote deletion). Then `git add -A && GIT_EDITOR=true git rebase --continue`.
