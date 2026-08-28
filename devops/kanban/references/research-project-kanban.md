# Research Project Task Management — Kanban Pattern

When managing research/PhD-style projects via kanban, use this pattern:

## Task Decomposition Pattern

Research projects map well to 7 phases:

```
Literature Review → Corpus Curation → Retrieval Pipeline → Baseline Harness →
Data Generation → Fine-tuning → Evaluation → Dissertation
```

### Example: Solvarch (RAG + SLM for Cloud Arch Decision Support)

| Task | Type | Phase |
|------|------|-------|
| Literature review on RAG, code LLMs, PEFT, IaC eval | Research | 1 |
| Curate domain corpus (AWS docs, pricing, ADRs) | Research | 2 |
| Build hybrid retrieval (BM25 + dense + reranker) | Engineering | 3 |
| Implement baseline evaluation harness | Engineering | 3 |
| Generate synthetic training data (Evol-Instruct, OSS-Instruct) | Research | 4 |
| Execute LoRA/QLoRA fine-tuning with ablations | Engineering | 5 |
| Evaluate Solvarch vs baselines on Well-Architected benchmark | Research | 6 |
| Write dissertation manuscript | Writing | 7 |

### Dependency Structure

```
literature ──→ corpus ──→ retrieval
              ↘         ↙
               data gen → fine-tuning → evaluation → dissertation
                   ↘                     ↗
                baseline harness ────────┘
```

Link via: `hermes kanban link <parent_id> <child_id>` (positional args! Note: NOT `--parent`.)

## Related Patterns

- When corpus is collected manually (outside kanban), see `references/research-corpus-validation.md` for the integration pattern.
- When kanban workers crash repeatedly, see `references/kanban-worker-crash-diagnosis.md` for the diagnostic tree.

## Body Template

Every task body should include:
1. **Scope** — What needs to be done
2. **Deliverables** — Concrete outputs (documents, code, configs)
3. **Technical Decisions Needed** — Explicitly call out decisions the worker needs to make
4. **Constraints** — Hardware limits, format requirements, deadlines
5. **Deadline** — Date by which this must complete

## Scheduling Tips

- Set **Priority 1** for phase-gate items (literature review, dissertation)
- Set **Priority 2-3** for supporting work (corpus, baselines)
- Leave dependent tasks as **blocked** until predecessors are marked done
- Free-running tasks auto-transition to **running** when their blockers complete

## Task Status Verification (Before Marking Done)

When the user says a task is complete, **never trust the kanban status alone**. Always verify against actual artifacts:

1. **Check git log** — `git log --oneline -- <path>` for relevant directories
2. **Check output files** — `ls -la` for expected output files, read their content to verify correctness
3. **Verify completeness** — For benchmark/evaluation tasks: check that ALL baselines listed in the task body were actually executed (not just defined in config)
4. **Read scoring output** — For benchmark evaluation: check `per_baseline` keys in report JSON — they must match the baselines the task asked for
5. **Only then** update the kanban task with a detailed summary

**Why**: Kanban `done` status can be stale. Git artifacts are the source of truth. Task bodies may reference baselines or steps that were defined but never actually run.

## Task Editing in Terminal State

When a kanban task is already `done` (terminal state), you CANNOT use `hermes kanban complete` — it will fail with "unknown id or terminal state". Instead:

```bash
hermes kanban edit <task_id> --result "done" --summary "<detailed updated summary>"
```

The `--result "done"` is required even though the task is already done; this updates the summary without changing the status.

## Common Research Project Pitfalls

6. **Worker crashes don't mean the work failed** — Always check `hermes kanban log <id>` to distinguish API errors (profile config issue) from protocol violations (context overflow). For the full diagnosis tree, see `references/kanban-worker-crash-diagnosis.md`.
7. **Phantom parent chains** — When a parent task gets archived or GC'd, child tasks retain links to it. This causes `claim_rejected: parents_not_done` errors and tasks stuck in blocked state. Remove stale links with `hermes kanban unlink <child_id> <parent_id>` or restructure the board.
8. **Archived tasks block the board** — When tasks crash and give up, the dispatcher may set `status=archived`. Archived tasks are invisible to `complete` and `edit`. Archive deliberately after you're done with a pattern, or recreate the task if you need it on the board.
2. **Include "Technical Decisions" in task bodies** — Research always has choices; surface them explicitly so the worker documents why they chose option A over B.
3. **Leave DPO as optional** — Supervisor note: when both synthetic data generation AND fine-tuning pack the same window, make preference optimization optional.
4. **Write dissertation last but plan first** — The dissertation task should exist from day one; all other tasks feed into it.
