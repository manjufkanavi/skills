#!/usr/bin/env python3
"""
telegram_monitor.py — Watches for UNAUTHORIZED users on a Telegram bot.

Polls getUpdates, checks sender against ALLOWED_USERS, sends alert
via Telegram Bot API when unauthorized activity is detected.

Usage:
    export TELEGRAM_BOT_TOKEN="your_bot_token"
    export TELEGRAM_ALERT_CHAT_ID="target_chat_id"   # optional
    python3 telegram_monitor.py

Features:
- Handles all update types: message, edited_message, channel_post,
  callback_query, inline_query, channel_post edits, etc.
- Deduplication via seen update_id tracking
- Conflict-aware offset management (handles 409 from Hermes gateway)
- Structured Markdown alert output
- Runs in background via Hermes process management

Compatible with: macOS, Linux, any Python 3.8+ environment.
"""

import json
import os
import sys
import time
import logging
import urllib.request
import urllib.error

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
ALLOWED_USERS = {5349625423}  # <-- change these

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set.")
    sys.exit(1)

ALERT_CHAT_ID = os.environ.get("TELEGRAM_ALERT_CHAT_ID", "")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S UTC",
)
log = logging.getLogger("telegram_monitor")

# ------------------------------------------------------------------
# State
# ------------------------------------------------------------------
seen_update_ids = set()

# ------------------------------------------------------------------
# API helpers
# ------------------------------------------------------------------

def api_get_updates(offset=0, limit=1, timeout=10):
    """Fetch updates with limit=1 to minimize conflict with other pollers."""
    url = f"{API_BASE}/getUpdates?offset={offset}&limit={limit}&timeout={timeout}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        if data.get("ok"):
            return data.get("result", []), data.get("offset", offset + 1)
        elif "Conflict" in data.get("description", ""):
            return [], offset
        else:
            log.warning("API error: %s", data.get("description"))
            return [], offset
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        if "Conflict" in body:
            log.warning("409 Conflict — another bot instance active")
            return [], offset
        log.error("HTTP %d: %s", e.code, body)
        return [], offset
    except Exception as e:
        log.error("Request failed: %s", e)
        return [], offset


def send_alert(text: str) -> None:
    """Send alert via Telegram Bot API."""
    if not ALERT_CHAT_ID:
        print("\n" + "=" * 60)
        print(text)
        print("=" * 60 + "\n")
        return

    payload = {
        "chat_id": ALERT_CHAT_ID,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "text": text,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API_BASE}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
        result = json.loads(body)
        if result.get("ok"):
            log.info("✅ Alert sent to chat %s", ALERT_CHAT_ID)
        else:
            log.error("❌ Alert send failed: %s", result.get("description"))
    except Exception as e:
        log.error("❌ Alert send failed: %s", e)


# ------------------------------------------------------------------
# Extract sender from any update type
# ------------------------------------------------------------------
def extract_sender(upd):
    """Walk through all update types and extract sender info."""
    # Regular/edited message
    for key in ("message", "edited_message"):
        obj = upd.get(key)
        if not obj:
            continue
        sender = obj.get("from") or obj.get("sender_chat")
        if sender:
            return {
                "user_id": sender.get("id"),
                "user_obj": sender,
                "event_type": key,
                "message_id": obj.get("message_id"),
                "message_text": obj.get("text") or obj.get("caption"),
                "chat_id": obj.get("chat", {}).get("id", ""),
                "chat_title": obj.get("chat", {}).get("title", ""),
                "chat_type": obj.get("chat", {}).get("type", ""),
                "timestamp": obj.get("date", obj.get("edit_date", "N/A")),
            }

    # Channel posts
    for key in ("channel_post", "edited_channel_post"):
        obj = upd.get(key)
        if not obj:
            continue
        sender = obj.get("sender_chat")
        if sender:
            return {
                "user_id": sender.get("id"),
                "user_obj": sender,
                "event_type": key,
                "message_id": obj.get("message_id"),
                "message_text": obj.get("text") or obj.get("caption"),
                "chat_id": obj.get("chat", {}).get("id", ""),
                "chat_title": obj.get("chat", {}).get("title", ""),
                "chat_type": obj.get("chat", {}).get("type", ""),
                "timestamp": obj.get("edit_date", obj.get("date", "N/A")),
            }

    # Callback query
    cb = upd.get("callback_query")
    if cb:
        sender = cb.get("from")
        if sender:
            return {
                "user_id": sender.get("id"),
                "user_obj": sender,
                "event_type": "callback_query",
                "message_id": cb.get("message", {}).get("message_id") or "N/A",
                "message_text": "[Callback] " + (cb.get("data") or "[no data]"),
                "chat_id": "", "chat_title": "", "chat_type": "",
                "timestamp": cb.get("date", "N/A"),
            }

    # Inline query
    iq = upd.get("inline_query")
    if iq:
        sender = iq.get("from")
        if sender:
            return {
                "user_id": sender.get("id"),
                "user_obj": sender,
                "event_type": "inline_query",
                "message_id": "N/A",
                "message_text": "[Inline Query] " + (iq.get("query") or "[empty]"),
                "chat_id": "", "chat_title": "", "chat_type": "",
                "timestamp": "N/A",
            }

    return None


# ------------------------------------------------------------------
# Build alert message
# ------------------------------------------------------------------
def build_alert(info):
    """Build a Markdown alert string from extracted info."""
    uid = info["user_id"]
    uobj = info["user_obj"]
    first = uobj.get("first_name", "N/A")
    last = uobj.get("last_name", "")
    uname = uobj.get("username", "")
    is_bot = uobj.get("is_bot", False)
    lang = uobj.get("language_code", "")
    premium = uobj.get("is_premium", False)
    text = info["message_text"]

    if text and len(text) > 1500:
        text = text[:1500] + "..."

    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    lines = [
        "🚨 **UNAUTHORIZED USER ALERT** 🚨",
        "",
        "*⚠️ Unauthorized activity detected!*",
        "",
        "*── User Details ──*",
        f"*User ID:* `{uid}`",
        f"*First Name:* {first}",
    ]
    if last:
        lines.append(f"*Last Name:* {last}")
    if uname:
        lines.append(f"*Username:* @{uname}")
    if lang:
        lines.append(f"*Language:* {lang}")
    if is_bot:
        lines.append("*Is Bot:* Yes")
    if premium:
        lines.append("*Premium:* Yes")

    lines += [
        "",
        "*── Activity Details ──*",
        f"*Event Type:* {info['event_type']}",
        f"*Chat ID:* `{info['chat_id']}`",
        f"*Chat Title:* {info['chat_title']}",
        f"*Chat Type:* {info['chat_type']}",
        f"*Message ID:* `{info['message_id']}`",
        f"*Timestamp:* {info['timestamp']}",
        "",
        "*── Message Content ──*",
    ]

    if text:
        lines.append(f"```")
        lines.append(f"{text}")
        lines.append(f"```")
    else:
        lines.append("*[No text — media/reaction/etc.]*")

    lines += [
        "",
        f"*Alerted at:* {now}",
        "",
        "⚠️ This user is NOT in the allowed list.",
    ]

    return "\n".join(lines)


# ------------------------------------------------------------------
# Main loop
# ------------------------------------------------------------------
def main():
    log.info("=" * 50)
    log.info("  Telegram Unauthorized User Monitor")
    log.info("=" * 50)
    log.info("Allowed users: %s", ALLOWED_USERS)
    log.info("Bot: ****%s...", BOT_TOKEN[-10:])
    log.info("Alerts to: %s", ALERT_CHAT_ID or "stdout")
    log.info("=" * 50)

    offset = 0
    while True:
        updates, new_offset = api_get_updates(offset=offset)

        if updates:
            for upd in updates:
                update_id = upd.get("update_id", 0)
                if update_id in seen_update_ids:
                    continue
                seen_update_ids.add(update_id)

                info = extract_sender(upd)
                if not info:
                    continue

                if info["user_id"] in ALLOWED_USERS:
                    log.info("✅ Authorized user %s", info["user_id"])
                    continue

                alert_text = build_alert(info)
                log.warning("🚨 ALERT: Unauthorized user %s (%s)", info["user_id"], info["event_type"])
                send_alert(alert_text)

            offset = new_offset
            time.sleep(2)
        else:
            time.sleep(45)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Stopped by user")
    except Exception as e:
        log.error("Fatal: %s", e, exc_info=True)
        sys.exit(1)
