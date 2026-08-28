# ZeroClaw Config Structure Reference

Complete TOML configuration reference for ZeroClaw agent framework with Ollama backend and Telegram channel.

## Minimal Working Config

```toml
schema_version = 3

[agents.zeroclaw]
enabled = true
model_provider = "ollama"
risk_profile = "default"

[agents.zeroclaw.precheck]
enabled = true
timeout_secs = 5

[agents.zeroclaw.identity]
format = "openclaw"

[agents.zeroclaw.memory]
backend = "sqlite"

[agents.zeroclaw.workspace]
unrestricted_filesystem = false

[agents.zeroclaw.a2a]
published = false

[risk_profiles.default]
block_high_risk_commands = false
require_approval_for_medium_risk = false
workspace_only = true

[risk_profiles.default.delegation_policy]
mode = "forbidden"

[provider.ollama]
base_url = "http://127.0.0.1:11434"
num_ctx = 131072

[channels.telegram.zeroclaw_bot]
enabled = true
name = "zeroclaw-bot"
bot_token = "YOUR_BOT_TOKEN_HERE"
```

## Config Section Reference

### `[agents.<alias>]` — Agent Configuration

| Property | Type | Description |
|----------|------|-------------|
| `enabled` | bool | Whether the agent is active |
| `model_provider` | string | Provider name (e.g., `ollama`, `openai`, `anthropic`) |
| `risk_profile` | string | Alias referencing a `[risk_profiles.<alias>]` entry |
| `channels` | array | List of channel references this agent uses |
| `memory.backend` | string | Storage backend (`sqlite`, etc.) |
| `precheck.enabled` | bool | Enable pre-flight checks |
| `precheck.timeout_secs` | int | Precheck timeout |

### `[provider.<name>]` — Provider Configuration

Used for local providers (Ollama, vLLM, etc.):

```toml
[provider.ollama]
base_url = "http://127.0.0.1:11434"
num_ctx = 131072
```

| Property | Type | Description |
|----------|------|-------------|
| `base_url` | string | Ollama server endpoint |
| `num_ctx` | int | Context window size (default 4096, max per model) |

### `[channels.telegram.<alias>]` — Telegram Channel

```toml
[channels.telegram.zeroclaw_bot]
enabled = true
name = "zeroclaw-bot"
bot_token = "8263914026:***"
```

| Property | Type | Description |
|----------|------|-------------|
| `enabled` | bool | Channel active |
| `name` | string | Display name |
| `bot_token` | secret | Telegram bot token (get from @BotFather) |
| `stream_mode` | string | `off` or `on` (streaming responses) |
| `mention_only` | bool | Only respond when @mentioned |
| `draft_update_interval_ms` | int | Draft update frequency |

### `[risk_profiles.<alias>]` — Risk/Security Profile

Controls which commands the agent can execute:

```toml
[risk_profiles.default]
allowed_commands = ["git", "npm", "ls", "cat", "grep", "python", "python3"]
auto_approve = ["file_read", "memory_recall", "web_search_tool"]
block_high_risk_commands = false
forbidden_paths = ["/etc", "/root", "/home"]
level = "supervised"
require_approval_for_medium_risk = false
workspace_only = true
```

| Property | Type | Description |
|----------|------|-------------|
| `allowed_commands` | array | Shell commands the agent can run directly |
| `auto_approve` | array | Operations that don't need approval |
| `block_high_risk_commands` | bool | Block dangerous shell commands |
| `forbidden_paths` | array | File paths the agent cannot access |
| `level` | string | `"permissive"`, `"supervised"`, `"restricted"` |
| `workspace_only` | bool | Restrict operations to workspace directory |

### `[risk_profiles.<alias>.delegation_policy]`

```toml
[risk_profiles.default.delegation_policy]
mode = "forbidden"  # "forbidden", "allowed", "conditional"
```

## Config CLI Limitations

The `zeroclaw config set` CLI has these limitations:

1. **Secret fields require terminal** — Cannot set `bot_token`, `api_key`, etc. via CLI in non-interactive mode. Write TOML directly.

2. **Property path mismatches** — Expected CLI paths like `providers.models.ollama.default.base_url` may not exist. The TOML format uses `[provider.ollama]` instead.

3. **Risk profile must exist** — Setting `agents.<alias>.risk_profile = "default"` fails if `[risk_profiles.default]` is not defined.

4. **Provider resolution** — Setting `model_provider = "ollama"` alone may not resolve. The `[provider.ollama]` section with `base_url` is needed, or pass `--provider ollama` on the CLI.

## Common Config Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "no model providers configured" | `[provider.ollama]` section missing | Add `[provider.ollama]` with `base_url` |
| "risk_profile does not name a configured risk_profiles entry" | `[risk_profiles.default]` not defined | Define the risk profile section |
| "Secret input requires a terminal on stdin and stderr" | CLI can't prompt for secret | Write TOML file directly |
| "Unknown property 'providers.models.ollama.default.base_url'" | CLI path doesn't match TOML structure | Use `[provider.ollama]` in TOML |
| Telegram shows ❌ | `bot_token` not set or invalid | Verify token with @BotFather |
