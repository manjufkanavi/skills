# getUpdates Conflict with Hermes Gateway — Session Case Study

## Context (2026-07-11)

Tried to build a standalone Telegram unauthorized-user monitor by polling `getUpdates` on the same bot token (`895134...`) that the Hermes integration gateway already uses. Result: relentless 409 Conflict errors despite trying every offset management trick (reset to 0, `limit=1`, staggered intervals, `seen_id` deduplication).

## Root Cause

The Hermes gateway (`gateway.platforms.telegram`) holds an active `getUpdates` long-polling session on the same bot token. This is **not a stale script** — it's the Hermes integration itself, running as PID 10068 (`hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace`).

**Key discovery:** The `.env` file at `~/.hermes/.env` contains both `TELEGRAM_BOT_TOKEN=895134...GLHI` and `TELEGRAM_ALLOWED_USERS=5349625423`. The Hermes gateway already enforces the allowed-users check natively — it logs unauthorized users with `WARNING gateway.run: Unauthorized user: <id> (<name>) on telegram`.

## Diagnostic Pattern

```bash
# Check if Hermes gateway owns the bot token
grep "inbound message.*platform=telegram" ~/.hermes/logs/gateway.log | wc -l
# If > 0, the gateway is receiving messages — it owns the poll session

# Check the allowed users configured
grep TELEGRAM_ALLOWED_USERS ~/.hermes/.env

# Find the gateway process
ps aux | grep -i "hermes.*gateway" | grep -v grep

# List all Telegram senders from logs
grep "inbound message.*platform=telegram" ~/.hermes/logs/gateway.log | grep -o 'user=[^ ]*' | sort -u

# Count messages per user
grep "inbound message.*platform=telegram" ~/.hermes/logs/gateway.log | grep -o 'user=[^ ]*' | sort | uniq -c | sort -rn

# Find unauthorized user attempts
grep "Unauthorized user" ~/.hermes/logs/gateway.log
```

## Resolution Paths

1. **Hercha's integration already handles the use case** — the gateway logs and enforces `TELEGRAM_ALLOWED_USERS`. A separate monitor is redundant.
2. **Separate bot token** — create a new bot via @BotFather for any additional monitoring needs.
3. **Webhook mode** — switch Hermes to webhooks to free the `getUpdates` session.

## Lessons Learned

- **Never assume** a Telegram bot token is free to poll — check the Hermes `.env` first
- **The Hermes gateway IS the conflicting process** when you get persistent 409s despite killing old scripts
- **Look at the logs** (`gateway.log`) before writing monitoring tools — the data may already be there
- **Hermes's `TELEGRAM_ALLOWED_USERS` is already an access control mechanism** — leverage it before building new ones
