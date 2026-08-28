---
name: hermes-configuration
description: "Hermes configuration and troubleshooting — auxiliary providers, config paths, model routing, and common setup patterns."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
---

# Hermes Configuration

Common configuration patterns, troubleshooting steps, and setup procedures for Hermes Agent.

## Auxiliary Providers (Vision, Compression, Session Search)

Auxiliary tasks (vision, compression, session_search) use the `auto` provider by default. When `auto` can't find a backend, tasks fail silently.

### Symptoms

```
Error: No LLM provider configured for task=vision provider=auto.
```

### Fix

Explicitly configure the provider and model:

```bash
hermes config set auxiliary.vision.provider <provider_name>
hermes config set auxiliary.vision.model <model_name>
```

### Provider Options

| Provider | Requirement | Example |
|----------|-------------|---------|
| `omlx` (local) | Model running on 127.0.0.1:1234 | `Qwen3-VL-4B-Instruct-MLX-4bit` |
| `openrouter` | `OPENROUTER_API_KEY` in `.env` | `anthropic/claude-sonnet-4` |
| `google` | `GOOGLE_API_KEY` in `.env` | `gemini-2.0-flash` |

### Config Location

```yaml
# ~/.hermes/config.yaml
auxiliary:
  vision:
    provider: omlx
    model: Qwen3-VL-4B-Instruct-MLX-4bit
```

### Verification

```bash
grep -A3 auxiliary ~/.hermes/config.yaml
```

### After Changes

Config changes take effect on a new session:
- **CLI**: exit and relaunch
- **Gateway**: `/restart` or `/new`

## Config Quick Reference

| Command | Purpose |
|---------|---------|
| `hermes config show` | Display current config |
| `hermes config edit` | Open config.yaml in $EDITOR |
| `hermes config set KEY VAL` | Set a config value |
| `hermes config path` | Print config.yaml path |
| `hermes auth list` | List stored credentials |
| `hermes doctor` | Check dependencies and config |

## Common Config Paths

| Setting | Config Key |
|---------|-----------|
| Model | `model.default`, `model.provider` |
| Vision provider | `auxiliary.vision.provider` |
| Vision model | `auxiliary.vision.model` |
| Compression enabled | `compression.enabled` |
| Compression threshold | `compression.threshold` |
| STT enabled | `stt.enabled` |
| TTS provider | `tts.provider` |

## Troubleshooting

### Vision fails after model change

The auxiliary config may still point to an old model. Update both provider and model:

```bash
hermes config set auxiliary.vision.provider <new_provider>
hermes config set auxiliary.vision.model <new_model>
```

### Auxiliary tasks fail silently

Check if `auto` can find a backend. Set `auxiliary.vision.provider` explicitly (see above).

### Config changes not taking effect

- Tools/skills: `/reset` starts a new session
- Config changes: gateway `/restart`, CLI exit and relaunch
- MCP servers: `/reload-mcp`

## References

- Full config reference: https://hermes-agent.nousresearch.com/docs/user-guide/configuration
- Providers guide: https://hermes-agent.nousresearch.com/docs/integrations/providers