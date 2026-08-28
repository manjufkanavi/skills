# Integrating nanobot with Antigravity CLI for Agentic Coding from Telegram

**Research date:** 2026-08-05 · **Sources:** 73 pages (67 web, 18 research) · **Queries:** 71

## Executive Summary

There is no single official "nanobot ↔ Antigravity" integration. The ecosystem has converged on **three viable patterns**, all of which work with your existing setup (nanobot gateway on Telegram + `agy` CLI 1.1.9 + Antigravity IDE). Ranked by fit for your stack:

1. **Subprocess bridge (simplest, recommended)** — nanobot already has an `antigravity-cli` skill that shells out to `agy -p`. Wire that into the Telegram channel and you get agentic coding from Telegram with zero new infrastructure.
2. **MCP server bridge** — expose Antigravity's native MCP + Artifact system to nanobot via `tools.mcpServers` in `~/.nanobot/config.json`. Bi-directional, real-time, approval buttons.
3. **CDP remote-control bot** — a standalone Telegram bot (e.g. `antigravity-telegram-remote`) drives the Antigravity IDE via Chrome DevTools Protocol. Most feature-rich but runs as a *separate* bot, not through nanobot.

---

## Pattern 1 — Subprocess bridge (recommended for you)

You already have `skills/antigravity-cli/SKILL.md`, which documents exactly this:

```python
import subprocess
result = subprocess.run(
    ["agy", "-p", "Your prompt", "--model", "gemini-2.0-flash"],
    capture_output=True, text=True, timeout=300
)
return result.stdout
```

**Key facts from your skill:**
- `agy -p` = non-interactive/print mode (scripted usage) — perfect for a bot.
- `--dangerously-skip-permissions` auto-approves edits; `--print-timeout 5m` caps runtime.
- Modes: `default` (TUI), `accept-edits` (auto-edit), `plan` (no edits).
- Persistent sessions via `/continue`; multi-model (Gemini, Claude, GPT OSS).

**Why this fits:** nanobot's Telegram channel already routes messages to your normal model, tools, memory, and workspace. A skill that runs `agy -p` in a subprocess means a Telegram DM becomes a full agentic-coding session. No ports, no CDP, no separate bot. The main caveat is the ~600s subprocess timeout — long agentic runs need chunking or async handling.

---

## Pattern 2 — MCP server bridge (bi-directional, real-time)

Antigravity has **native MCP + Artifact support**. The community `antigravity-telegram` bridge (JacksonFuck, LobeHub) is the reference implementation:

**Architecture:**
```
Telegram App ◄─► Python Bridge ◄─► Antigravity Agent
                        │
                        ▼
                 Artifact Watcher
```

**Setup:**
1. Clone + `pip install -e .`, copy `.env.example` → `.env` with `TELEGRAM_BOT_TOKEN`, `AUTHORIZED_CHAT_IDS`, `ARTIFACTS_PATH=~/.gemini/antigravity/artifacts`.
2. Run `python -m src.main --mode mcp` (MCP server) and `--mode bot` (Telegram bot).
3. Register the bridge in Antigravity's `~/.gemini/mcp_config.json`.
4. Copy `workflows/mobile-command.md` → `~/.agent/workflows/`.

**MCP tools exposed:** `send_telegram_message`, `request_plan_approval`, `request_change_approval`, `send_artifact` (screenshots/recordings), `update_status`, `notify_error`, `await_user_response`.

**To wire into nanobot** (per nanobot's `configure-mcp-tools.md`), add to `~/.nanobot/config.json`:

```json
{
  "tools": {
    "mcpServers": {
      "antigravity-telegram": {
        "command": "python",
        "args": ["-m", "src.main", "--mode", "mcp"],
        "cwd": "/path/to/antigravity-telegram",
        "env": {
          "TELEGRAM_BOT_TOKEN": "...",
          "AUTHORIZED_CHAT_IDS": "...",
          "ARTIFACTS_PATH": "~/.gemini/antigravity/artifacts"
        },
        "enabledTools": ["send_telegram_message", "request_plan_approval", "send_artifact"]
      }
    }
  }
}
```

Then restart the gateway and mention the integration with `@` in a Telegram message. **Note:** your current config has `"tools": {"restrictToWorkspace": false}` and no `mcpServers` yet — this is the cleanest place to add it.

---

## Pattern 3 — CDP remote-control bot (most features, separate bot)

`antigravity-telegram-remote` (hongquandev / optimistengineer) is a mature, standalone option:

- **Install:** `npm install -g antigravity-telegram-remote` (or `brew tap optimistengineer/remoat && brew install antigravity-telegram-remote`).
- **Setup wizard:** `antigravity-telegram-remote setup` (bot token, allowed user IDs, workspace dir).
- **Launch Antigravity with CDP:** `antigravity-telegram-remote open` (ports 9222/9223/9333/9444/9555/9666).
- **Start bot:** `antigravity-telegram-remote start`.

**How it works:** Telegram → bot → CDP (WebSocket) → Antigravity IDE. A response monitor polls the DOM every 2s, detects progress/approval dialogs/errors, streams results back. Auto-accept via MutationObserver clicking Run/Accept/Allow/Continue.

**Notable features:** project isolation via Telegram Forum Topics, local Whisper voice transcription, `/model`, `/mode` (fast/plan), `/screenshot`, `/autoaccept`, `/template` prompt templates, whitelist auth, path-traversal prevention, no port exposure.

**Caveat for you:** this runs as its *own* Telegram bot, not through nanobot. It's the right choice if you want the full IDE experience (editor, terminal, extensions) driven remotely — but it bypasses nanobot's memory/tools/workspace layer.

---

## Recommendation for your stack

Given you already run nanobot on Telegram with the `antigravity-cli` skill and `agy` 1.1.9:

- **Start with Pattern 1** — it's already 90% built. Make the skill's subprocess call the default path for Telegram-triggered coding tasks. Zero new infra, uses your existing gateway, memory, and workspace.
- **Add Pattern 2 later** if you want real-time progress streaming, approval buttons, and artifact (screenshot) delivery back to Telegram — this is the "seamless" upgrade path and slots into nanobot's `tools.mcpServers` cleanly.
- **Use Pattern 3 only** if you specifically need the full Antigravity IDE (not just the CLI agent) driven from your phone, and are OK running a second bot.

## Security notes (from nanobot docs)
- Prefer `enabledTools` over exposing every MCP tool.
- Stdio MCP starts a local process — review the command before enabling.
- Whitelist `AUTHORIZED_CHAT_IDS`; never use `allowFrom: ["*"]`.
- Keep bot tokens in env vars, not command args.
- `--dangerously-skip-permissions` is powerful — gate it behind an explicit user toggle.

## Key sources
- nanobot docs: `docs/guides/telegram-ai-agent.md`, `docs/guides/configure-mcp-tools.md`
- `antigravity-telegram-remote` README (hongquandev/optimistengineer)
- `antigravity-telegram-suite` (emreturkmencom) — dual-app CDP bot
- LobeHub MCP: `jacksonfuck-antigravity-telegram` (Antigravity Mobile Command)
- Real Python / DataCamp / Google Codelabs Antigravity CLI guides
