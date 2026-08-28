---
name: antigravity-cli
description: Harness all capabilities of Google Antigravity CLI (`agy`) — AI coding assistant and text generation via Gemini models. CLI-only skill using the agy command for non-interactive text tasks.
tags: [antigravity, agy, google-ai, gemini, coding-assistant, cli]
---

# Antigravity CLI (`agy`)

## When to Use
- Non-interactive text generation: `agy -p "prompt"` via helper script (never inline)
- Code review, editing, and explanation
- Text analysis, summarization, translation
- Research synthesis and expert analysis
- **Kannada poetry analysis** — stanza-by-stanza meaning via `scripts/agy_synthesize.py`

## What Is agy?
Antigravity CLI is Google's AI coding assistant — similar to Claude Code or Codex CLI. It runs in a TUI for interactive use and supports `--print` (`-p`) for non-interactive mode. Uses Gemini 3.5 Flash as default model.

## Installation
Already installed at `/Users/manjunathkanavi/.local/bin/agy` (v1.1.1).

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

## Authentication
Google Sign-In via browser (no API key needed). Uses system keyring.

## Available Models
| Model | Use Case |
|-------|----------|
| gemini-3.5-flash-medium | Default — best balance |
| gemini-3.5-flash-high | Higher quality, slower |
| gemini-3.1-pro-high | Pro tier |
| claude-sonnet-4.6-thinking | Claude for complex reasoning |
| claude-opus-4.6-thinking | Claude for deep analysis |
| gpt-oss-120b-medium | GPT OSS alternative |

## Commands

### Non-Interactive (Print Mode)
```bash
agy --dangerously-skip-permissions -p "Your prompt" --model gemini-3.5-flash-medium
```

**CRITICAL:** Never pass `-p` with shell inline strings using single quotes — shell consumes the prompt. **ALWAYS use a helper script with stdin piping.**

### Interactive Mode
```bash
agy                        # Start TUI
agy --continue             # Resume last session
```

### Other Commands
```bash
agy models          # List available models
agy agents          # List available agents
agy plugin          # Manage plugins
agy update          # Update CLI
agy --help          # Show help
```

## Common Pitfalls

1. **agy wraps JSON in single quotes** — Output looks like `'{"key": "value"}'` with escaped characters. Must strip outer quotes and unescape before parsing.
2. **agy wraps JSON in single quotes with escaped chars** — The output string has `\\n` (literal backslash-n) and `\\"` (literal backslash-quote). Unescape these: `output.replace("\\n", "\n").replace("\\\"", '"')`
3. **agy -p with shell single quotes fails** — Shell consumes everything between `'...'`. The agy agent sees a truncated or empty prompt. **Always pipe via stdin.**
4. **agy may add prefix text** — Sometimes prepends prose before JSON (e.g., "ಪ್ರಣಾಮಗಳು"). Extract JSON by finding first `{` to last `}`+1.
5. **agy is an AI coding assistant** — Not a simple text generator. For pure text output, write descriptive prompts asking for JSON only.
6. **Timeouts** — agy can take 30-120 seconds. Set timeout >= 180s for complex prompts.
7. **agy @file reference** — Use `@/path/to/file` to read file content into prompts (e.g., `@/tmp/lyrics.md`).

## Helper Script Pattern

For reliable agy calls from Python, use this pattern:

```python
import subprocess, sys, json

prompt = sys.stdin.read()
result = subprocess.run(
    ["agy", "--dangerously-skip-permissions", "-p", prompt, "--model", "gemini-3.5-flash-medium"],
    capture_output=True, text=True, timeout=180
)

output = result.stdout.strip()
if output.startswith("'") and output.endswith("'"):
    output = output[1:-1]
    output = output.replace("\\n", "\n").replace("\\\"", '"')

start = output.find('{')
end = output.rfind('}') + 1
if start != -1 and end > start:
    data = json.loads(output[start:end])
    print(json.dumps(data))
```

Usage: `python3 main.py | python3 helper.py`

## Integration with Other Skills
- **kannada-poet**: Uses agy for stanza-by-stanza Kannada/English poetry analysis via `scripts/agy_synthesize.py`
- **deep-research**: agy can synthesize research findings into reports

## Supporting Files
- `references/agy-quirks.md` — Detailed quirks, pitfalls, and comparison with Gemini CLI

## Typical Usage
For any task requiring agy via Python:
1. Write the helper script (copy from antigravity-cli skill or reuse kannada-poet's version)
2. Pipe prompt via stdin: `echo "prompt" | python3 helper.py`
3. Parse clean JSON from stdout
