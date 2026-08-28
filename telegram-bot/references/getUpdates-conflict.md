# getUpdates Conflict (409) — Detailed Reference

## The Problem
When two processes long-poll the same Telegram bot token via `getUpdates`, only one can hold the session. The other receives HTTP 409:

```json
{"ok":false,"error_code":409,"description":"Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"}
```

## Why It Happens
Telegram's Bot API uses a long-polling mechanism where the API connection stays open until an update is available or a timeout is reached. When a second process starts polling, Telegram **terminates the first process's connection** to prevent duplicate processing. This is by design.

## Symptoms
- Every few seconds/minutes, the script logs "409 Conflict" errors
- Updates are processed then lost when conflict occurs
- Offsets become stale, causing duplicate processing or missed updates

## Diagnosis
1. Check for running processes: `ps aux | grep -i telegram | grep -v grep`
2. Common culprits:
   - Previous monitoring script instances still running
   - The Hermes integration gateway (which also uses `getUpdates`)
   - Any other bot client (CLI tools, testing scripts)

## Solutions

### Solution 1: Use a separate bot token (recommended for independent services)
Create a new bot via @BotFather. Each bot token can have one long-polling session.

### Solution 2: Switch to webhook mode
Configure webhook in the Hermes integration:
```
TELEGRAM_WEBHOOK_URL=https://my-app.fly.dev/telegram
TELEGRAM_WEBHOOK_PORT=8443
```
Webhooks can serve multiple consumers; the conflict only applies to `getUpdates`.

### Solution 3: Stagger polling intervals
If using the same token is unavoidable:
- Use `limit=1` and `timeout=10`
- Poll every 45-60 seconds
- Handle 409 by resetting offset to 0
- Track seen `update_id`s to avoid duplicates

### Solution 4: Kill conflicting processes
Before starting a new monitor, kill all stale instances:
```bash
pkill -f telegram_monitor
# Also check for Hermes gateway polling the same bot
ps aux | grep "getUpdates" | grep -v grep
```

## Offset Recovery Pattern
```python
offset = 0
seen_ids = set()

while True:
    updates, new_offset = api_get_updates(offset=offset)
    if not updates:
        time.sleep(45)  # long wait to reduce conflict chance
        continue
    
    for upd in updates:
        uid = upd.get("update_id", 0)
        if uid in seen_ids:
            continue
        seen_ids.add(uid)
        # process update...
    
    offset = new_offset + 1
```

## Prevention Checklist
- [ ] Before starting any new bot polling process, check `ps aux` for stale instances
- [ ] Use separate bot tokens for independent services
- [ ] Prefer webhook mode when multiple consumers are needed
- [ ] Always track `update_id`s for deduplication
- [ ] Log 409 occurrences to detect recurring conflicts
