---
name: telegram-bot
description: Telegram Bot development and management — polling getUpdates, webhooks, security monitoring, and integration patterns.
---

# telegram-bot

Telegram Bot development and management — building bots, polling getUpdates, webhooks, security monitoring, and integration patterns.

## When to use
- Building a new Telegram bot or adding functionality to an existing one
- Polling `getUpdates` (long-polling) or configuring webhooks
- Monitoring bot for unauthorized users, spam, or abuse
- Integrating a bot with an external service (database, API, chat platform)
- Debugging bot API issues (409 conflicts, rate limits, stuck offsets)

## Core concepts

### Two modes of receiving updates
1. **Long-polling (`getUpdates`)** — The bot polls `https://api.telegram.org/bot<TOKEN>/getUpdates`. Simple, no server needed. Only ONE instance can poll per bot token (409 Conflict on overlap).
2. **Webhook** — Telegram sends POST to your URL when new updates arrive. Requires a public HTTPS endpoint. Can coexist with other bots but not multiple long-pollers.

### Critical pitfall: `getUpdates` conflict
Two long-polling sessions on the same bot token will conflict. The Telegram API returns HTTP 409 with "Conflict: terminated by other getUpdates request". Resolution:
- **The Hermes gateway ITSELF is often the conflicting process** — it holds an active `getUpdates` session on the same bot token configured in `~/.hermes/.env` (`TELEGRAM_BOT_TOKEN`). Don't assume old scripts are the culprit if 409s persist after killing all monitoring processes.
- **Check the gateway logs** first: `grep "inbound message.*platform=telegram" ~/.hermes/logs/gateway.log | wc -l`. If > 0, the Hermes gateway is actively receiving messages and owns the poll session.
- **The Hermes gateway already enforces `TELEGRAM_ALLOWED_USERS`** (set in `.env`) and logs unauthorized attempts: `grep "Unauthorized user" ~/.hermes/logs/gateway.log`. A separate monitor is often redundant.
- Use only one long-polling process per bot token
- Switch to webhook mode if multiple consumers are needed
- Use a separate bot token for each independent service
- Poll with short `limit=1` and infrequent intervals to reduce overlap window

### Offset management
- `getUpdates` uses an `offset` parameter to resume from where you left off
- On success, the response includes a new `offset` — use `offset + 1` for next poll
- On 409 Conflict, reset to `offset=0` and process from scratch
- Always track seen `update_id`s to avoid duplicates after conflict resets

### Supported update types
The monitor script handles: `message`, `edited_message`, `channel_post`, `edited_channel_post`, `callback_query`, `inline_query`, `chosen_inline_result`, `shipping_query`, `pre_checkout_query`.

### Accessing @Userinfobot
@Userinfobot is a built-in Telegram bot that returns user details when messaged. To query it programmatically, send a message to @Userinfobot with the user's ID or username. This is a workaround since the Bot API has no direct "get user info" endpoint.

## Common patterns
- **Security monitor**: Poll getUpdates, filter by allowed user IDs, alert on unauthorized senders
- **Webhook handler**: HTTPS endpoint that receives POST updates, processes and acknowledges
- **Multi-bot architecture**: Separate bot token per service to avoid polling conflicts

### Resources
- `references/getUpdates-conflict.md` — Detailed 409 conflict handling and recovery recipes
- `references/getUpdates-conflict-hermes-case-study.md` — Session case study: the Hermes gateway itself as the conflicting process, diagnostic patterns, and lessons learned
- `scripts/telegram_monitor.py` — Removed (could not run due to Hermes gateway 409 conflict; see case study for alternatives)
