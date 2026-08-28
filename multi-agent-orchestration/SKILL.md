---
name: multi-agent-orchestration
description: >
  Patterns for building and running multi-agent software development systems using
  Hermes Agent profiles. Covers profile creation, SOUL.md authoring, shared workspace
  design, loop engineering (require → design → implement → test → deploy → accept → feedback),
  cross-project coordination, MCP server wiring, and automation with cron.
version: 1.0.0
author: Hermes Agent
tags: [orchestration, multi-agent, loop-engineering, profiles, shared-workspace]
---

# Multi-Agent Orchestration

Patterns for building and running multi-agent software development systems with
Hermes Agent profiles. This skill covers the class of problems around **coordinating
specialized agents across projects** — not single-agent workflows.

## When to Use

Load this skill when:
- Setting up a multi-agent development team (profiles with distinct roles)
- Designing a shared workspace for agent-to-agent communication
- Running a feature through a multi-phase loop (require → design → implement → test → deploy)
- Coordinating work across multiple projects simultaneously
- Wiring MCP servers to give profiles specific tool access
- Automating routine operations (standups, tests, reviews) with cron

## Pattern 1: Profile-Based Teams

### Directory Structure

Each profile gets its own Hermes Agent profile directory with a `SOUL.md`:

```
~/.hermes/profiles/
├── product_manager/
│   └── SOUL.md          # Role definition, scope, output format
├── architect/
│   └── SOUL.md
├── developer/
│   └── SOUL.md
├── tester/
│   └── SOUL.md
└── devops/
    └── SOUL.md
```

### Writing SOUL.md

Each SOUL.md defines:
1. **Role identity** — who this agent is and what they own
2. **Scope** — what the agent should and should NOT do
3. **Output format** — structured deliverables (user stories, ADRs, test reports)
4. **Rules** — project-specific or role-specific constraints
5. **Communication protocol** — how this agent talks to others

### Default Role Set (5 profiles)

| Profile | Responsibility |
|---------|---------------|
| `product_manager` | User stories, acceptance criteria, backlog, PRDs, acceptance review |
| `architect` | System design, ADRs, API contracts, tech decisions, cross-project coordination |
| `developer` | Code implementation, bug fixes, scripts, documentation |
| `tester` | Test suites, security scans, coverage, QA sign-off |
| `devops` | CI/CD, Docker, infrastructure, deployment, monitoring |

See `references/profile-templates.md` for complete SOUL.md templates.

## Pattern 2: Shared Workspace

The shared workspace is the communication bus between profiles. Create it at `~/.hermes/shared/`:

```
~/.hermes/shared/
├── backlog/              # Product manager output
├── architecture/         # Architect output (ADRs, API contracts)
├── api_contracts/        # API spec files
├── designs/              # Visual/architectural designs
├── test_results/         # Tester output
├── deployments/          # DevOps output
├── security/             # Security scan results
├── status.json           # Global state (active loop, current phase, project registry)
└── updates.json          # Event log of all agent actions
```

**Key files:**

**`status.json`** — Global state registry:
```json
{
  "framework_version": "1.0.0",
  "active_loop": "feature-123",
  "current_phase": "implement",
  "projects": { "ProjectName": { "path": "...", "status": "...", "tech": "..." } },
  "agents": { "name": { "role": "...", "status": "ready|working|blocked" } }
}
```

**`updates.json`** — Append-only event log:
```json
[{"timestamp": "ISO", "agent": "developer", "action": "implemented", "details": "..."}]
```

## Pattern 3: Loop Engineering (7 Phases)

Every feature/task goes through a mandatory phase gate:

```
REQUIREMENT → DESIGN → IMPLEMENT → TEST → DEPLOY → ACCEPT → FEEDBACK
     ↑_________________________________________________________↓
                            (route back on failure)
```

| Phase | Agent | Input | Output |
|-------|-------|-------|--------|
| 1. Requirement | product_manager | User request | `backlog/story-NNN-<name>.md` |
| 2. Design | architect | Backlog stories | `architecture/ADR-NNN-<name>.md`, `api_contracts/<name>.json` |
| 3. Implement | developer | Architecture + contracts | Code changes, PRs, `updates.json` entry |
| 4. Test | tester | Implementation | `test_results/` report, pass/fail |
| 5. Deploy | devops | Passed tests | Deployment confirmation, `deployments/` entry |
| 6. Accept | product_manager | Deployment | Pass/fail against acceptance criteria |
| 7. Feedback | orchestrator | Accept result | Route back or mark complete |

**Failure routing:**
- Test failure → back to IMPLEMENT
- Security failure → back to IMPLEMENT (with fix requirements)
- Design mismatch → back to DESIGN
- Requirements mismatch → back to REQUIREMENT

## Pattern 4: Cross-Project Coordination

When a feature spans multiple projects:

1. **Product Manager** writes a **shared user story** that describes the cross-project impact
2. **Architect** creates a **cross-project design** with integration points between repos
3. **Developer** works in **parallel** using `--worktree` for each project
4. **Tester** runs suites across all affected projects
5. **DevOps** deploys all affected projects (with dependency ordering)

## Pattern 5: Per-Project Context

Every project gets an `AGENTS.md` file that tells any profile:
- Tech stack and version info
- Important file paths and directories
- Project-specific rules and conventions
- Which agents have which permissions
- Current state and phase priorities

See `references/agents-template.md` for the AGENTS.md template.

## Pattern 6: MCP Server Configuration

Different profiles benefit from different MCP servers:

```bash
# Add a command-based MCP server
echo "y" | hermes mcp add <name> --command "npx" --args "-y" "<package>"

# For filesystem access scoped to project dir
echo "y" | hermes mcp add file-server --command "npx" --args "-y" "@modelcontextprotocol/server-filesystem" "<project-dir>"

# List and test
hermes mcp list
hermes mcp test <name>

# Reload after adding
hermes mcp reload
```

**Recommended server set:**
- `file-server` — All profiles (read/write project files)
- `sequential-thinking` — Architect, Product Manager (structured planning)
- `github` — Developer, Tester (repository operations)
- `docker` — DevOps, Developer (container management)

See `references/mcp-setup.md` for detailed MCP configuration patterns.

## Pattern 7: Automation with Cron

Automate recurring operations:

```bash
# Daily standup — project status summary
hermes cron create --name "Daily Standup" --schedule "0 9 * * *" --prompt "..."

# Nightly test suite — run tests across all projects
hermes cron create --name "Nightly Tests" --schedule "0 2 * * *" --prompt "..."

# Weekly review — trends, recommendations
hermes cron create --name "Weekly Review" --schedule "0 10 * * 1" --prompt "..."
```

## Pattern 8: Per-Project Agent Roles (.agent Directory)

Beyond `~/.hermes/profiles/`, projects can define their own agent roles in a `.agent/` directory at the repo root. Each role gets a `SOUL.md` following the same structured format as Hermes profile SOULs:

```
<project>/.agent/
├── devops-engineer/SOUL.md    # Project-specific DevOps AI role
├── secops-engineer/SOUL.md    # Project-specific SecOps AI role
└── ...
```

### When to Use Per-Project `.agent/` Roles

- The project needs AI agent roles that are **project-specific** (not shared across all projects)
- You're building an agentic platform where roles are defined as code in the repo
- You want roles to be **version-controlled** alongside the project they serve
- The roles need project context (tech stack, paths, rules) baked in

### SOUL.md Structure for Project Roles

Each `SOUL.md` should contain:
1. **Frontmatter** — `name`, `title`, `description`, `version`, `created`
2. **Role Summary** — who this agent is, what they own
3. **Mission** — the agent's core purpose
4. **Core Responsibilities** — numbered categories of work
5. **Technical Skills** — categorized skills and tools
6. **Tools & Technologies** — table of tools by category
7. **Operational Guidelines** — principles, constraints, quality gates
8. **Performance Metrics** — measurable targets

### Creating a Project Role — Workflow

1. **Research the role domain** — run deep research on the role's responsibilities, skills, and tools
2. **Synthesize findings** — extract key patterns from research data
3. **Write SOUL.md** — follow the structure above, include project-specific context
4. **Place in `.agent/<role-name>/SOUL.md`** — one directory per role
5. **Commit to repo** — version control the role definition

### Pitfall: Research Data Staleness

The `deep-research` skill's `research_data.json` is **overwritten** on each run. If researching multiple roles, save each dataset to a temp file before running the next topic. The script's background process also **does not propagate writes** to the git-tracked `research_data.json` — always run `python3 -u deep_research.py` in the **foreground terminal** to capture results.

## Pitfalls

- **Profile name collision** — don't use names that conflict with built-in Hermes profiles or common tools
- **Missing project AGENTS.md** — agents will work blind without per-project context. Always write one before delegating work.
- **Phase gate skipping** — never let a developer start implementing without an architect's design. Phase gates exist for a reason.
- **Shared workspace stale state** — `status.json` and `updates.json` must be updated after every loop phase. Stale state corrupts cross-agent coordination.
- **Overlapping agent permissions** — don't give every agent write access to every directory. Principle of least privilege per role.
- **Cross-project coupling** — minimize dependencies between projects. When they must connect, document it in the architect's design.
- **MCP server connectivity** — MCP servers require a new session after configuration. Use `hermes mcp reload` or start a new session.

## See Also

- `references/profile-templates.md` — SOUL.md templates for all 5 default profiles
- `references/project-role-soul-template.md` — Project-level `.agent/` role SOUL.md template with full example
- `references/agents-template.md` — AGENTS.md template for per-project context
- `references/mcp-setup.md` — MCP server configuration patterns
- `references/cron-scripts.md` — Reference scripts for daily standup, nightly tests, weekly review

## Related Skills

- `dev-workflow` — Single-agent development workflow (TDD, architecture review, spike, dogfood)
- `kanban` — Kanban-style multi-agent task decomposition and task lifecycle
- `hermes-agent` — Hermes Agent configuration and profile management
- `testing` — Test suite orchestration: nightly multi-project runs, parallel execution, structured reporting
