---
name: multi-model-service-audit
description: >
  Reference to ansible-service-audit skill. This is a convenience alias
  that delegates to the full ansible-service-audit skill.
version: 2.0.0
tags: [audit, service, multi-model, reference]
---

# Multi-Model Service Audit (Reference)

This skill is a **thin reference** to `ansible-service-audit`.

## How to Use

Load the full skill:

```
skill_view(name='ansible-service-audit')
```

## What It Does

`ansible-service-audit` performs a full automated service audit:

1. **Gathers** all Ansible role files, docker-compose entries, nginx/cloudflare configs
2. **Launches 6 parallel audits** using 3 models × 2 roles:
   - Self (this agent) + DevOps Engineer
   - Self (this agent) + SecOps Engineer
   - Antares (`antares-1b-mlx-8bit`) + DevOps Engineer
   - Antares (`antares-1b-mlx-8bit`) + SecOps Engineer
   - VibeThinker (`VibeThinker-3B-OptiQ-4bit`) + DevOps Engineer
   - VibeThinker (`VibeThinker-3B-OptiQ-4bit`) + SecOps Engineer
3. **Consolidates** all 6 JSON reports, deduplicates findings
4. **Validates** each finding against actual code/live state
5. **Fixes** genuine issues in Ansible templates
6. **Redeploys** service and verifies health
7. **Commits** and pushes all changes

## Key Architecture

- **Self** uses `delegate_task` with full tool access (file, terminal, search)
- **Antares/VibeThinker** use `curl` (text-only, no tool calling)
- 4 remote calls run in parallel via `ThreadPoolExecutor`
- All 6 reports saved to `/tmp/<service>_<role>_<model>_audit.json`

## Files

- **Main skill:** `ansible-service-audit` (load with `skill_view`)
- **Remote model wrapper:** `~/.hermes/skills/ansible-service-audit/scripts/remote_model_caller.py`
- **This file:** Reference alias (do not modify)
