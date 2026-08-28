---
name: agy-harness
description: Full harness for Google Antigravity CLI (agy) — execute complex coding tasks, image generation, visual UI mockups, usage/quota checks, research, and multi-agent workflows using agy targeted at /Users/manjunathkanavi/.nanobot/workspace/git_clone_dir.
metadata:
  nanobot:
    requires:
      bins:
        - agy
---

# Google Antigravity CLI (`agy`) Full Harness

This skill teaches the agent how to harness the full power of `agy` (Google Antigravity CLI) to delegate complex coding tasks, image generation, visual asset creation, usage/quota checking, and system operations directly through `agy`.

---

## 📍 Primary Target Workspace

All `agy` execution, code generation, git operations, and image output must default to or target:
**`/Users/manjunathkanavi/.nanobot/workspace/git_clone_dir`**

Always pass `--add-dir /Users/manjunathkanavi/.nanobot/workspace/git_clone_dir` or set the working directory (`cwd`) to `/Users/manjunathkanavi/.nanobot/workspace/git_clone_dir` when executing `agy` commands.

---

## 1. When to Use `agy` Harness

Use `agy` when:
1. **Coding Tasks**: You need high-speed code generation, refactoring, building whole projects, running unit tests, or multi-file edits powered by Antigravity's Gemini engine without consuming external API quotas.
2. **Image & Asset Generation**: You need to generate visual UI mockups, graphics, icons, or design assets using Antigravity's `generate_image` tool inside the target workspace.
3. **Usage & Quota Checking**: You need to check the active model, quota usage, rate limits, or account status for Antigravity/Gemini.
4. **Complex Multi-Step Operations**: You want to execute interactive or planned developer workflows using `--mode accept-edits` or `--mode plan`.
5. **Offline / Free Tier Offloading**: Offloading heavy reasoning or generation tasks to `agy` using the user's active Google AI Pro / Google Account authentication.

---

## 2. Command Execution Patterns

### A. Usage & Quota Check (`agy -p "/usage"`)
Query `agy` to report current usage limits, quota, and model status:
```bash
/Users/manjunathkanavi/.local/bin/agy -p "/usage"
```

### B. Default Non-Interactive Prompt in Workspace
Run a prompt targeting the primary workspace directory:
```bash
cd /Users/manjunathkanavi/.nanobot/workspace/git_clone_dir && /Users/manjunathkanavi/.local/bin/agy --add-dir /Users/manjunathkanavi/.nanobot/workspace/git_clone_dir -p "Create a modern React landing page with dark mode"
```

### C. Specifying Reasoning Effort (`--effort`)
Control reasoning depth (`low`, `medium`, `high`):
```bash
/Users/manjunathkanavi/.local/bin/agy --add-dir /Users/manjunathkanavi/.nanobot/workspace/git_clone_dir --effort high -p "Refactor authentication system to use JWT refresh tokens"
```

### D. Specifying Execution Mode (`--mode`)
- `accept-edits`: Direct execution and file modification mode.
- `plan`: Research and strategic planning mode (generates `implementation_plan.md`).
```bash
/Users/manjunathkanavi/.local/bin/agy --add-dir /Users/manjunathkanavi/.nanobot/workspace/git_clone_dir --mode plan -p "Plan migration from SQLite to PostgreSQL"
```

### E. Image & Asset Generation via `agy`
Ask `agy` explicitly to generate images, UI designs, or visual assets inside the workspace:
```bash
cd /Users/manjunathkanavi/.nanobot/workspace/git_clone_dir && /Users/manjunathkanavi/.local/bin/agy -p "Generate a high quality dark-mode dashboard mockup image for a cloud analytics platform and save it as cloud_dashboard.png"
```

---

## 3. Recommended Workflows for Nanobot

1. **Target Workspace**: Always execute `agy` commands with `cwd=/Users/manjunathkanavi/.nanobot/workspace/git_clone_dir` or with `--add-dir /Users/manjunathkanavi/.nanobot/workspace/git_clone_dir`.
2. **Usage Checks**: When the user asks about Gemini/Antigravity quota or usage, run `/Users/manjunathkanavi/.local/bin/agy -p "/usage"` and parse the response.
3. **Delegate Heavy Coding**: When a Telegram or channel request requires deep coding, execute `agy -p "<detailed instructions>"`.
4. **Image Generation**: When requested to create mockups, diagrams, or visual assets, invoke `agy -p "generate an image for..."` inside the target workspace.
5. **Capture Outputs & Status**: Inspect standard output and check generated files/artifacts upon command completion to report back to the user.
