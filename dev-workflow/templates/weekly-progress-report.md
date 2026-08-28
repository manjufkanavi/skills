# 📊 {Project Name} Weekly Production Readiness Report

**Date:** {YYYY-MM-DD} (Day of Week)
**Review Type:** Weekly automated check
**Previous Report:** {YYYY-MM-DD}

---

## 1. Overall Project Readiness Score: {X.Y}/10 (↑/↓/→ from {prev})

{_one sentence on score movement and reason_}

---

## 2. Tasks Completed Since Last Check

{_table of completed or in-progress tasks with evidence_}

| Task | Status | Evidence |
|------|--------|----------|
| T-XXX | 🟡 In Progress | {commit SHA, file diff, etc.} |

**New commits since last check:**
```
{git log --oneline -5 output}
```

**SPRINT{N} status:** {N} of {total} critical P0 tasks completed.

---

## 3. Current Focus Area: Phase {N} — {Theme}

{_state which phase the project is in, with evidence from AGENTS.md or docs_}

**Phase progress:**
| Task | Priority | Status |
|------|----------|--------|
| T-001 | P0 | {emoji} {status with details} |
| T-002 | P0 | ⬜ Not started |
| ... | | |

---

## 4. Blockers and Risks

| # | Risk | Severity | Details |
|---|------|----------|---------|
| 1 | {_description_} | 🔴/🟡 | {_impact_} |
| 2 | ... | | |

---

## 5. Recommended Actions for This Week

### Priority 1 — {_task_} ({_day_})
1. {_action step_}
2. {_action step_}

### Priority 2 — {_task_} ({_day_})
1. {_action step_}

### Quick Wins (parallel)
- **T-XXX** ({_effort_}): {_brief description_}

---

## 6. Health Summary

| Area | Status |
|------|--------|
| Infrastructure | {emoji} {_state_} |
| Documentation | {emoji} {_state_} |
| Security | {emoji} {_state_} |
| Testing | {emoji} {_state_} |
| UI/UX | {emoji} {_state_} |
| Architecture | {emoji} {_state_} |

---

**Next review scheduled in 7 days ({date}).**

---

## Scoring Guidelines

- **9-10**: Production-ready, minor polish remaining
- **7-8**: Feature-complete, needs hardening (security, reliability)
- **5-6**: Working prototype, significant gaps remain
- **3-4**: Working prototype, critical blockers identified
- **0-2**: Early development, foundational work in progress

## Phase Key

| Phase | Theme | Focus |
|-------|-------|-------|
| Phase 0 | Security Stabilization | Critical security vulnerabilities |
| Phase 1 | Reliability & Testing | Resilience, test coverage, CI/CD |
| Phase 2 | UX, Compliance & Polish | User experience, legal compliance |
| Phase 3 | Scale & Observability | Horizontal scaling, monitoring |
