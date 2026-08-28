# ZeroClaw Replacement of TinyHuman/OpenHuman (2026-08-11)

## Context

User replaced TinyHuman (OpenHuman) Telegram bot + AI runtime with ZeroClaw on a Docker-composed VM (`192.168.0.118`).

## What Was Removed

| Item | Location | Action |
|---|---|---|
| `tiny-human-bot.service` | `/etc/systemd/system/` | `systemctl stop/disable`, `sudo rm`, `daemon-reload` |
| `openhuman-core` container | Docker | `docker stop/rm` |
| `openhuman-workspace` | `/home/mkanavi/` | `sudo rm -rf` (Docker-owned files need sudo) |
| `bot.py`, `tiny_human_bot.py` | `/home/mkanavi/` | `sudo rm` |
| `bot.log` | `/home/mkanavi/` | `sudo rm` |

**⚠️ Credential loss:** The Telegram bot token was hardcoded in `bot.py` and was deleted without extraction first. The token was `8615881456:...` (full value was truncated in terminal output). It was **not** stored in any `.env` file, docker-compose, or environment variable. **Always extract credentials before deleting config files.**

## What Was Installed

**ZeroClaw v0.8.4** (prebuilt binary, no Rust toolchain needed):
```bash
curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/master/install.sh | sh -s -- --prebuilt
```

Binary installed to `/home/mkanavi/.cargo/bin/zeroclaw` (56M) + `zerocode` (35M).

## Config Structure

ZeroClaw uses `~/.zeroclaw/config.toml` with sections:
- `[providers.models.<type>.<alias>]` — model provider (Ollama, OpenAI, etc.)
- `[agents.<alias>]` — agent config referencing a provider
- `[channels.<type>.<alias>]` — messaging channels (Telegram, Discord, etc.)

## Model Issue

The LFM2.5 2.6B model (`oamazonasgabriel/lfm2.5-2.6b`) was NOT available on the Ollama library despite appearing in web search results. Error: `pull model manifest: file does not exist`.

Only available LFM2.5 models on Ollama: `lfm2.5` (8B) and `lfm2.5-thinking` (8B).

## Remaining Tasks (Unfinished at Session End)

1. Extract or provide Telegram bot token for ZeroClaw config
2. Pull LFM2.5 2.6B model (or choose alternative)
3. Write ZeroClaw config.toml
4. Start ZeroClaw as a systemd service
5. Remove old model from OpenWebUI config