# Hermes Agent Profiles — Multi-Agent Orchestration Reference

Derived from: `reports/how-to-harness-hermes-agent-with-local-llm-20260711-015653/` (15 KB report).

## What Is a Hermes Agent Profile

A profile is a self-contained workspace (`~/.hermes/profiles/<name>/`) with its own:
- **SOUL.md** — personality, role definition, behavior constraints
- **SKILL.md** — skills loaded for this profile
- **AGENTS.md** — agent-specific instructions
- **memories/** — persistent memory scoped to this profile
- **cron/** — scheduled jobs scoped to this profile

## Creating Profiles

```bash
# Clone the default profile (inherits base config)
hermes profile create <name> --clone

# Create from scratch
hermes profile create <name> --init
```

## Profile Design Patterns

### 1. Role-Splitting Pattern (Recommended for Teams)
Create separate profiles for distinct roles. Each has a focused SOUL.md:

```
hermes profile create architect --clone
hermes profile create developer --clone
hermes profile create tester --clone
hermes profile create devops --clone
hermes profile create product_manager --clone
```

### 2. Environment-Splitting Pattern
Separate profiles by environment:
```
hermes profile create dev --clone
hermes profile create staging --clone
hermes profile create production --clone
```

### 3. Capability-Splitting Pattern
Separate profiles by technical capability:
```
hermes profile create data_engineer --clone
hermes profile create security_auditor --clone
hermes profile create tech_writer --clone
```

## SOUL.md Design

Each profile's SOUL.md should define:
1. **Identity**: Name, role, what it does
2. **Expertise**: What it's good at
3. **Constraints**: What it MUST NOT do
4. **Output format**: How it structures responses
5. **Communication style**: Tone, verbosity, formatting preferences

### Example: Architect Profile SOUL.md

```markdown
# Architect Profile

You are the System Architect for this project.
You design system boundaries, technology choices, API contracts, and data flows.

## Responsibilities
- Define module boundaries and interfaces
- Select technology stack
- Design database schemas and APIs
- Review developer implementations for architectural compliance

## Constraints
- Do NOT write implementation code (that's the Developer's job)
- Do NOT make deployment decisions (that's DevOps's job)
- Always validate against existing architecture decisions
- Document all design decisions with rationale
```

## Cross-Profile Collaboration

Profiles communicate through shared files:
- **Architecture decisions**: Written by Architect, read by Developer
- **Implementation code**: Written by Developer, reviewed by Architect and Tester
- **Test results**: Written by Tester, reviewed by Developer and PM
- **Deployment manifests**: Written by DevOps, read by all

Files are shared via the workspace directory — each profile reads/writes to the same project files but with different behavioral constraints from their SOUL.md.

## Agent Profile Template

```markdown
# <Role> Profile

You are the <Role> for this project.

## Identity
<purpose statement>

## Expertise
- <skill 1>
- <skill 2>
- <skill 3>

## Constraints
- What you MUST do
- What you MUST NOT do

## Output Format
- How you structure your work

## Communication
- Tone, verbosity, audience
```

## Pitfalls

- **Overlapping responsibilities**: When two profiles can do the same task, define priority (e.g., "Developer writes code, but Architect approves all architectural changes").
- **Context bloat**: Each profile should only load the skills it needs, not clone everything from default.
- **Shared state corruption**: Profiles writing to the same files can conflict. Use clear ownership: "Architect owns architecture/, Developer owns src/".
- **Secrets in profiles**: Never put API keys or credentials in SOUL.md — use environment variables or a secrets manager.
- **Profile drift**: SOUL.md files diverge over time. Regularly review and align profiles with project evolution.
