# AGENTS.md Template

Template for per-project context files. Every project in the workspace should have an AGENTS.md at its root.

```markdown
# <ProjectName> — Project Context

## Project Overview
<One-paragraph description of what this project does and why it exists.>

## Tech Stack
- **Language:** ...
- **Framework:** ...
- **Build:** ...
- **Test:** ...
- **Lint:** ...
- **Deploy:** ...
- **Database:** ...

## Key Features
- Feature 1
- Feature 2
- Feature 3

## Current State
**Active** / **Planning** / **Suspended** / **Sprint N**
<One line on what's being worked on right now.>

## Important Paths
- `src/` — Main source code
- `tests/` — Test suite
- `docker/` — Docker configs
- `docs/` — Documentation
- ...

## Rules for Agents
- Rule 1: e.g., TypeScript strict mode enabled
- Rule 2: e.g., No hardcoded API keys
- Rule 3: e.g., All API routes must have rate limiting
- ...

## Agent Permissions
- **developer:** Full write access to ...
- **architect:** Review all ... changes
- **tester:** Run ..., check ...
- **devops:** Docker builds, ... deployment

## Agent Working Directory
Use `--worktree <path>` when delegating to a profile:
```bash
hermes -p developer --worktree <project-path> "describe task"
```
```

## Usage Notes

1. **Always create AGENTS.md before delegating work** — agents will work blind without it
2. **Keep it concise** — 20-50 lines is the sweet spot. The file loads into every agent's context.
3. **Update current state** — keep the "Current State" line current so agents know what to work on
4. **Be specific with permissions** — don't say "full access" unless you mean it
5. **Include the exact command** — agents follow the --worktree command pattern exactly

## Pitfall

A common mistake is writing AGENTS.md as a README replacement. It is NOT a project overview — it is **agent instructions**. Focus on what agents need to know to work in this project, not general project documentation. General docs belong in README.md or docs/
