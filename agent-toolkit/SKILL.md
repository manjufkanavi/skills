---
name: agent-toolkit
description: "Integrates graphify (knowledge graphs), headroom (tool output compression), and mem0 (persistent memory) into nanobot's default workflow. All three tools are initialized on startup and used automatically during every interaction."
---

# Agent Toolkit — Graphify + Headroom + Mem0

This skill integrates three tools that run **by default on every nanobot interaction**:

1. **Graphify** — Builds and queries persistent knowledge graphs of the workspace/corpus
2. **Headroom** — Compresses large tool outputs before they enter context window
3. **Mem0** — Maintains persistent memory across sessions (user preferences, facts, context)

## Installation (done)

All three are installed in the nanobot venv:
- Python: `~/.nanobot/venv/bin/python`
- Graphify: `~/.nanobot/venv/bin/graphify` (library: `import graphify`)
- Headroom: `~/.nanobot/venv/bin/headroom` (library: `from headroom import compress`)
- Mem0: `from mem0 import Memory` (config: `~/.nanobot/mem0_config.json`)

## Auto-Initialization — Run on Every Startup

When nanobot starts or a new conversation begins, **always** run these steps:

### 1. Load Mem0 Memory

```python
import json, os
from mem0 import Memory

config_path = os.path.expanduser("~/.nanobot/mem0_config.json")
if os.path.exists(config_path):
    with open(config_path) as f:
        config = json.load(f)
    mem0_client = Memory.from_config(config)
else:
    # Fallback: in-memory only
    mem0_client = Memory()
```

- Always check `mem0_client` for relevant memories before answering (use `mem0_client.search(query, user_id="nanobot")`)
- Always store new facts using `mem0_client.add(fact, user_id="nanobot")` after each interaction
- Store: user preferences, answered questions, project facts, technical decisions

### 2. Enable Headroom Compression

```python
from headroom import compress

# After any tool call that produces >2000 tokens of output, compress it:
# compressed = compress(messages, model="claude-sonnet-4-5-20250929")
# if compressed.tokens_saved > 0:
#     use compressed content instead of raw output
```

- Automatically compress any tool output that exceeds ~2000 tokens
- Headroom identifies and removes redundant/verbose content while preserving meaning

### 3. Check/Create Graphify Knowledge Graph

```bash
# If graphify-out/graph.json doesn't exist or is stale (>24h old), build the graph:
GRAPHIFY="$HOME/.nanobot/venv/bin/graphify"
PYTHON="$HOME/.nanobot/venv/bin/python"

# Check if graph exists
if [ ! -f "$WORKSPACE/graphify-out/graph.json" ]; then
    # Build knowledge graph (with no-semantic for speed on code-only)
    cd "$WORKSPACE"
    $GRAPHIFY . --no-viz
fi
```

- On startup, check if `graphify-out/graph.json` exists in workspace root
- If missing or older than 24 hours, rebuild the graph
- After rebuild, query the graph when relevant to understand project structure

## Usage During Interaction

### Always-On Memory (Mem0)

Before answering the user:
1. Search mem0 for relevant context: `mem0_client.search(user_message, user_id="nanobot")`
2. Use matching memories to personalize the response

After answering the user:
1. Extract key facts from the interaction
2. Store them: `mem0_client.add("User prefers X", user_id="nanobot")`

### On-Demand Compression (Headroom)

Use automatically when:
- A tool output exceeds ~2000 tokens
- The context window is getting full (>60% of limit)
- Before passing large data to another tool or subagent

### On-Demand Knowledge Graph (Graphify)

When the user asks about project structure, architecture, or code relationships:
1. Check if `graphify-out/graph.json` exists
2. If yes, run: `$GRAPHIFY query "<question>"`
3. If no, build first: `$GRAPHIFY . --no-viz` then query

When working on a new topic/subdirectory:
- Build focused graph: `$GRAPHIFY <path>` for targeted analysis

### Periodic Maintenance (via HEARTBEAT.md)

- Knowledge Graph Refresh (weekly): Check if graphify-out/graph.json is older than 7 days; if stale, rebuild it; if major new directories exist, build focused sub-graphs.
- Headroom Compression Stats (weekly): Verify headroom is available and log any errors.
- Mem0 Health Check (weekly): Verify Mem0 is functioning properly.
- All-Tools Verification (every heartbeat): Verify all integrated tools are working correctly.

## Tool-Specific Configurations

### Mem0 Config (~/.nanobot/mem0_config.json)
- Embeddings: fastembed (bge-small-en-v1.5)
- LLM: openai at 127.0.0.1:1234/v1
- Vector store: Qdrant at ~/.nanobot/mem0_store/
- History DB: SQLite at ~/.nanobot/mem0_history.db

### Headroom
- Compression target: claude-sonnet-4-5-20250929 (default model)
- Applied automatically on outputs >2000 tokens
- Can be used via CLI: `headroom proxy` or `headroom mcp`

### Graphify
- CLI: `~/.nanobot/venv/bin/graphify`
- MCP server: `~/.nanobot/venv/bin/graphify-mcp`
- Installed as Claude Code skill at `~/.claude/skills/graphify/SKILL.md`

## Verification

Run these checks periodically:
```bash
# Verify all three tools import correctly
$HOME/.nanobot/venv/bin/python -c "from headroom import compress; print('headroom OK')"
$HOME/.nanobot/venv/bin/python -c "from mem0 import Memory; print('mem0 OK')"
$HOME/.nanobot/venv/bin/python -c "import graphify; print('graphify OK')"
```
