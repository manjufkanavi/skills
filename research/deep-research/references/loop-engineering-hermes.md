# Loop Engineering with Hermes Agent — Structured Reference

Derived from: `reports/loop-engineering-hermes-agent-20260711-193300/` (28 KB report).

## What Is Loop Engineering

Loop engineering replaces linear prompt-and-response with **continuous feedback loops** where AI agents iteratively:
1. Receive a task
2. Produce output
3. Evaluate against criteria
4. Self-correct or escalate

This is fundamentally different from prompt engineering (static, single-turn instructions).

## Architecture: 3-Loop Model

```
Inner Loop (micro):  Review → Code → Test → Fix (seconds)
Middle Loop (macro): Design → Implement → Review → Refactor (minutes)
Outer Loop (strategic): Plan → Build → Validate → Ship (hours)
```

## Agent Profiles for Loop Engineering

Each profile has explicit role, skills, constraints, and output format:

| Profile | Responsibility | Skills | Constraints |
|---------|---------------|--------|-------------|
| **Architect** | System design, module boundaries, technology selection | Architecture, API design, scalability | No code implementation |
| **Developer** | Implementation, coding, debugging | Languages, frameworks, testing | Follows architect specs exactly |
| **Tester** | Quality assurance, edge cases, regression | Test design, automation, bug analysis | No code changes — reports only |
| **DevOps** | CI/CD, deployment, infrastructure | Docker, GitHub Actions, cloud | Immutable infrastructure |
| **PM** | Requirements, priorities, stakeholder alignment | PRDs, user stories, metrics | No technical decisions |

## Loop Engineering vs Prompt Engineering

| Aspect | Prompt Engineering | Loop Engineering |
|--------|-------------------|------------------|
| Interaction model | Single-turn prompt → response | Multi-turn iterative feedback loop |
| Agent role | Passive executor | Active evaluator and self-corrector |
| Output quality | Depends on prompt clarity | Depends on feedback loop quality |
| Error recovery | Rewrite prompt | Loop iteration with specific fix |
| Context management | Context window limits | Structured context via profiles |
| Best for | Simple, well-defined tasks | Complex, evolving, multi-step tasks |

## Common Problems & Fixes

- **Token cost explosion**: Each iteration costs tokens. Track and cap iterations. Use progressive refinement (broad → narrow).
- **Agent hallucination in role-specific tasks**: Constrain agents with explicit profiles and validation gates.
- **Error propagation**: Errors cascade across loops. Add error boundaries at each loop transition.
- **Context window overflow**: Use structured context — only pass relevant files/tools per agent, not everything.
- **Stalled loops**: Agent gets stuck in retry loops. Add maximum iteration count + human escalation trigger.

## Tooling Ecosystem

- **Hermes Agent** — multi-profile orchestration
- **Claude Code** — loop-based CLI coding agent
- **Aider** — AI pair programmer with git-aware loops
- **Cursor** — editor with code-aware agent loops
