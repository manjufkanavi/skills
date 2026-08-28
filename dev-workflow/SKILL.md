---
name: dev-workflow
description: >
  Complete software development workflow toolkit. Covers architecture review,
  throwaway experiments (spikes), test-driven development, pre-commit code review,
  parallel code simplification, and exploratory QA (dogfood). Each module handles
  a distinct phase of the dev lifecycle.
version: 2.2.0
author: Hermes Agent
tags: [dev-workflow, architecture, spike, tdd, code-review, simplify, qa, dogfood]
created: 2026-07-11
updated: 2026-08-03
---

# Dev Workflow Toolkit

## Overview

Six distinct skills for different phases of the software development lifecycle.
Each is loaded independently based on the trigger. The `plan` skill handles
the planning phase separately (slash-command entry point, see `plan` skill).

**Related skills:** `plan` (architecture review findings feed into plans), `spike` (validate deferred components)

---

### 1. Architecture Review (load this when...)

Review an existing project's architecture before committing to more work.

**Load this when:** "review this project", "what's the state of X", "is this over-engineered", "review architecture"

**Core method:**
1. Understand the project (README, architecture docs, code, tests, deployment)
2. Service inventory audit — classify every dependency as needed/deferred/unnecessary
3. "One thing" test — find the project's real moat
4. Alignment review — code vs docs, build vs run, phase breakdown
5. Deliver verdict: ✅ Good, ⚠️ Tighten, 🎯 Real moat, 📋 Next steps

**Pitfalls:** Don't just list problems — pair with recommendations. Don't assume minimalism is always right. Distinguish "I would do differently" from "actively harmful."

**See:** `references/architecture-review-pattern.md` for the detailed workflow.

---

### 2. Spike (load this when...)

Throwaway experiments to validate feasibility before committing to build.

**Load this when:** "spike this out", "let me try this", "is this even possible?", "compare A vs B", "before I commit to Y", "quick prototype"

**Core method (5-step loop):**
```
decompose → research → build → verdict
   ↑__________________________________________↓
                  iterate on findings
```

1. **Decompose** — Break idea into 2-5 independent feasibility questions (Given/When/Then). Order by risk.
2. **Align** — Present spike table, confirm order
3. **Research** — Brief each spike, surface competing approaches, pick one
4. **Build** — One dir per spike. Standalone. Bias toward interactive output.
5. **Verdict** — VALIDATED / PARTIAL / INVALIDATED. Document surprises, recommendations.

**Parallel comparison spikes:** Use `delegate_task` batch mode for 002a/002b variants.

**See:** `references/spike-methodology.md` for detailed spike patterns.

---

### 3. Test-Driven Development (load this when...)

Enforce RED-GREEN-REFACTOR. Write tests before code.

**Load this when:** "TDD this", "write tests first", "red-green-refactor"

**Core method:**
1. Write a failing test that expresses the desired behavior
2. Run the test — verify it fails (RED)
3. Write minimal code to make the test pass (GREEN)
4. Refactor with confidence (tests ensure no regression)
5. Repeat

**Pitfalls:**
- Don't write too many tests at once — one at a time
- Tests must be fast (< 1s) or they break the flow
- If you can't write a failing test, the requirement isn't clear enough
- Refactoring after GREEN must be driven by test suite passing

**See:** `references/tdd-patterns.md` for TDD workflow examples.

---

### 4. Pre-commit Code Review (load this when...)

Security and quality gate before committing.

**Load this when:** "code review this", "review before commit", "security scan", "quality check"

**Core method:**
1. Capture the diff to review
2. Run security scan (hardcoded secrets, SQL injection, XSS, path traversal, auth bypass)
3. Run quality gates (complexity, code smells, anti-patterns)
4. Apply auto-fixes for low-hanging fruit
5. Present remaining findings to user for manual review

**Pitfalls:**
- **Ansible collections get staged with `git add -A`** — The `collections/ansible_collections/` directory contains installed Ansible collections (full Python packages). Running `git add -A` will pick up hundreds of files. **Always use explicit file paths** or `git add roles/ ansible.cfg inventory/` instead of `-A`. Check `git status` before staging to verify only source files are included.
- Don't skip the security scan for config files (YAML, .env, HCL) — they may contain secrets in comments or template variables.

**See:** `references/pre-commit-review-pattern.md` for the review checklist.

---

### 5. Parallel Code Simplification (load this when...)

Three focused reviewers running in parallel for cleanup of recent changes.

**Load this when:** "simplify", "simplify my changes", "review my code"

**Core method:**
1. Identify changes (git diff, staged, last commit, etc.)
2. Launch three reviewers in parallel:
   - **Code Reuse** — existing utils, constants, patterns that could be reused
   - **Code Quality** — redundant state, parameter sprawl, copy-paste, leaky abstractions
   - **Efficiency** — unnecessary work, missed concurrency, hot-path bloat, memory issues
3. Aggregate findings, deduplicate, apply fixes
4. Verify nothing broke

**Pitfalls:** Give the WHOLE diff to each reviewer. Reviewers search, they don't guess. Apply ≠ rewrite.

---

### 6. Exploratory QA / Dogfood (load this when...)

Systematic QA testing of web applications.

**Load this when:** "test this app", "QA this", "dogfood", "find bugs in"

**Core method (5-phase):**
1. **Plan** — Create output dirs, identify scope, build rough sitemap
2. **Explore** — Navigate, snapshot, check console errors, click interactives
3. **Collect** — Take screenshots, record details, classify issues
4. **Categorize** — Deduplicate, assign severity (Critical/High/Medium/Low)
5. **Report** — Executive summary, per-issue sections, summary table

**Key tip:** Always check `browser_console()` after navigating and after significant interactions. Silent JS errors are high-value findings.

**See:** `references/dogfood-checklist.md` for the systematic testing checklist.

---

## Workflow Integration

The typical development lifecycle:

```\nspike (validate feasibility)\n  → architecture-review (assess existing code)\n  → plan (write actionable plan)\n  → tdd / code development (implement)\n  → requesting-code-review (pre-commit gate)\n  → simplify-code (post-commit cleanup)\n  → dogfood (system-level QA)\n  → parallel-infra (multi-phase deployment)\n```\n
## File Organization

Support files are in this skill's `references/` directory:

- `references/architecture-review-pattern.md` — Full architecture review methodology
- `references/spike-methodology.md` — Spike patterns and verdict formats
- `references/tdd-patterns.md` — TDD examples and anti-patterns
- `references/pre-commit-review-pattern.md` — Security scan checklist
- `references/patch-tool-avoid-replace_all.md` — Critical pitfall: `replace_all=True` on template files with duplicate blocks
- `references/cross-repo-doc-sync.md` — Pattern for syncing documentation across multiple related repos (LightSerp, iacgenie, unified-infra). Also see `references/multi-repo-doc-sync.md` in `infra-consolidation` for service-specific doc update patterns.
- `references/dogfood-checklist.md` — Systematic QA workflow
- `references/mcp-file-server-outage-recovery.md` — Recovery when MCP file server is unreachable, terminal fallback patterns
- `references/git-merge-safety.md` — Branch merge + stash verification workflow with real session example. Covers `git diff HEAD..stash@{N}` verification pattern to prevent silent loss of unique changes during merge conflict resolution.
- `references/nextjs-dockerfile-output-mismatch.md` — Pitfall: `output: 'export'` in next.config.js vs Dockerfile expecting `.next/standalone`. The build succeeds but the container fails because static export produces no `server.js`.
- `templates/weekly-progress-report.md` — Report template for weekly production readiness progress checks
- `references/ansible-deployment-workflow.md` — Ansible infrastructure deployment pattern: template changes → playbook deploy → service restart → verification → documentation → commit. Covers 6 common failure modes plus multi-service Docker debugging methodology (LightSerp pattern: internal connectivity tests, config sync audit, proxy routing verification, gap classification).
- `references/platform-auth-analysis.md` — Systematic method for analyzing an existing platform's authentication implementation (backend + frontend) and creating a migration plan. Covers Keycloak OIDC, JWT tokens, auth-wrapper integration patterns across multi-platform stacks.

---

### 7. Production Readiness Audit (load this when...)

Assess a codebase for production readiness and generate a role-assigned remediation plan.

**Load this when:** "evaluate this codebase", "is this production ready", "audit for launch", "create production roadmap"

**Core method (4 stages):**
```
locate project → delegate frontend eval → delegate backend eval (fresh context) →
create task plan → assign roles → set up monitoring
```

**Pitfalls:** Context contamination between frontend/backend evaluations — always clear context for backend. Zod v4 pre-release risk. Cron jobs can't use `execute_code` — use `terminal()`.

**See:** `references/12-category-audit-framework.md` for the evaluation framework.

---

### 8. Weekly Production Progress Check (load this when...)

Recurring progress review of a production-readiness effort. Reads the task tracker, sprint plan, git log, and evaluation reports, then produces a structured status report.

**Load this when:** "weekly progress check", "production readiness check", "what's the status of the prod readiness work", "check on project X's production progress"

**Core method:**
1. **Read the task tracker** — e.g., `TASK_TRACKER.md`. Check completion count, overall score, last updated date. If missing, create it from `PRODUCTION_READINESS_TASK_PLAN.md`.
2. **Read the sprint plan** — e.g., `SPRINT0_SECURITY_STABILIZATION.md`. Look for `[x]` markers to detect completed tasks.
3. **Check git status** — `git status --short` and `git log --oneline -5`. Identify meaningful commits (not just config-sync).
4. **Read evaluation reports** — `EVALUATION_REPORT.md` (frontend), `BACKEND_EVALUATION_REPORT.md` (backend). Load scores and key findings for reference.
5. **Compare & report** — Identify any new completed/in-progress tasks vs. last check. Produce structured output:
   - Overall readiness score (out of 10)
   - Tasks completed or in progress since last check
   - Current focus area (Phase 0/1/2/3)
   - Blockers and risks detected
   - Recommended actions for this week
6. **Update the tracker** — If any tasks are partially in progress, mark them with `[~]` and add a progress note.

**Pitfalls:**
- MCP file server may be unreachable. Always have a terminal fallback: read files with `terminal` + `cat`, search with `grep`.
- A "no progress" result is valid — don't fabricate changes. If the tracker hasn't changed, report: "No changes since last check. Project is on Phase X. Next review in 7 days."
- The git config sync commits (e.g., `daily-config-sync`) are noise — filter them out when assessing meaningful progress.
- Confidence level: if the git log shows PRs merged or issues closed, check those for task completion evidence.
- Don't confuse infrastructure migration commits with production-hardening task completion. Infrastructure work (docker compose, nginx setup) is not the same as the tracked security/reliability tasks.

**See:** `templates/weekly-progress-report.md` for the report template.\n\n---\n\n### 9. Parallel Infra Deployment (load this when...)\n\nManage complex multi-phase infrastructure work by splitting into parallel subagents.\n\n**Load this when:** implementing multiple independent phases of infrastructure work (monitoring, logging, security, deployment), fixing multiple unrelated bugs simultaneously, or doing a large refactoring across config files.\n\n**Core pattern (2 parallel subagents):**\n- **Subagent A: Infrastructure changes** — docker-compose edits, config files, scripts. Commits after its changes.\n- **Subagent B: Bug fixes + documentation** — config file fixes (app.ini, nginx.conf), docs updates. Commits on top of A's changes.\n\n**Rules:**\n- Both subagents work on the **same repo path** (e.g., `git_workspace/iacgenie-unified-infra`). Pass the exact path in context.\n- Subagent A goes first (infrastructure changes are bulk); Subagent B adds on top.\n- Each subagent commits independently so changes are traceable.\n- The orchestrator verifies with `git log --oneline` to confirm both commits exist.\n- Use `terminal` toolset for subagents — they need file write + git commit capability.\n- **When NOT to parallelize:** Single-phase work, or changes to the same file (file conflicts). If both subagents need to edit the same file (e.g., both change `docker-compose.yml`), use sequential delegation instead.\n\n## Workflow Integration

## Related Skills

- `plan` — Actionable markdown planning (separate slash-command skill)
- `production-readiness-audit` — End-to-end production hardening workflow (standalone skill)
- `testing` — Test suite orchestration across multi-project portfolios
- `github` — PR/issue management, code reviews
- `ansible-iac-patterns` — Convert manual Docker infrastructure into production-grade Ansible IAC. Use after architecture review identifies infrastructure gaps that need automation.

---

### 10. Git Branch Merge & Stash Safety (load this when...)

Safe branch merge workflow with post-merge stash verification. Prevents silent loss of unique changes during merge conflict resolution.

**Load this when:** merging a feature branch into main, applying stashed changes after a merge, deciding whether to discard a stash post-merge.

**Core pitfall (CRITICAL):** When a stash was created as WIP on main, then a feature branch (devops) is merged into main, the stash's changes are NOT automatically captured. If merge conflicts were resolved by keeping main's version, the stash content is silently discarded. **Always verify stash content against main after merge.**

**Core method (3 steps):**

1. **Pre-merge stash audit**
   ```bash
   git stash list
   # For each stash: git stash show --stat stash@{N}
   # Note which files each stash touches
   ```

2. **Post-merge verification**
   ```bash
   # For each stash: check if its changes are already in HEAD (main)
   git diff HEAD..stash@{N} --stat
   # If the diff shows meaningful changes (not just base-diff noise), the stash has unique content
   # Check specific key files: git diff HEAD..stash@{N} -- <key-file> | head -20
   ```

3. **Decision gate**
   - **Stash changes already in main** → `git stash drop stash@{N}`
   - **Stash has unique changes** → User must decide: apply on top, rebase, or discard
   - **Mixed** → apply via `git stash apply stash@{N}` (non-destructive), resolve conflicts manually

**Safe merge pattern:**
1. Merge feature branch into main (resolving conflicts keeping the DESIRED outcome — not blindly keeping HEAD)
2. **Before pushing or deleting the feature branch**, run `git diff HEAD..stash@{N} --stat` for every stash
3. Only delete stash/branch after confirming unique content is either in main or user-approved for discard

**Pitfalls:**
- `git diff HEAD..stash@{N} --stat` on an old stash shows huge diffs because the stash's BASE was an older main. Look at KEY files, not the full diff. Check specific files: `git diff HEAD..stash@{N} -- <critical-file>`
- Stash@{0} is the most recent stash. `git stash pop` is destructive (removes the stash). Use `git stash apply` to test first.
- During a merge, if you resolve ALL conflicts by keeping HEAD (main), you may silently discard unique changes from the merged branch AND from any stashes on top of that branch. Always review what HEAD kept vs what was lost.
- After `git stash pop` during a merge, if there are conflicts, resolving them by keeping HEAD means the stash content is gone. Use `git stash drop` only after CONFIRMING the content is in HEAD.
