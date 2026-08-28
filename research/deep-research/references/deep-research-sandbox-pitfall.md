# Deep Research Sandbox Pitfall: Git-Tracked Files Don't Update

## Symptom

Running `python3 deep_research.py "<query>"` in a sandboxed background process produces no visible output for several minutes. When the process exits with code 0, the `research_data.json` file remains unchanged from its previous state.

## Cause

The `deep_research.py` script reads from a **git-tracked** copy of `research_data.json` (e.g., in a clone at `~/.nanobot/workspace/git_clone_dir/personal_bot/skills/deep-research/`). The sandboxed environment has its own filesystem layer that doesn't propagate writes back to the original git-tracked file. The script may succeed silently but the updates are lost.

## Fix

1. **Run in foreground** instead of background if you need immediate output:
   ```bash
   cd ~/.hermes/skills/research/deep-research && python3 deep_research.py "<query>" 2>&1
   ```

2. **Copy the research_data.json** from the sandbox output location back to your working directory after the script runs.

3. **Prefer direct generation** — For interview preparation, topic lists, or structured data, generate the content directly using terminal commands or execute_code instead of relying on the sandboxed research script when you need the output immediately.

## When Deep Research Works Well

- Long-running research that can complete asynchronously
- When you can review the output file after the process exits
- When the research_data.json is in a non-git-tracked location (e.g., `~/.hermes/shared/`)

## When to Skip Deep Research

- Immediate output needed (use direct generation instead)
- The script reads from git-tracked files (sandbox won't propagate writes)
- You need structured interview questions or cheat sheets (craft directly)
