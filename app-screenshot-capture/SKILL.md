---
name: app-screenshot-capture
category: mobile
description: Screenshot Android app screens via adb and send to Telegram.
version: 1.1.0
author: Hermes Agent
tags: [app-screenshot-capture, adb, android, telegram, screenshot]
license: MIT
created: 2026-10-13
updated: 2026-10-13
---

# App Screenshot Capture (Android → Telegram)

Capture every screen of a running Android app and deliver the images to Telegram. Works for an emulator or USB-connected device through `adb`.

## When to Use

Use this skill when the user wants screenshots of a running Android app's screens, states, or flows delivered to Telegram — e.g. "send me all screen screenshots of this app" or "capture the screens and post them to Telegram".

## When NOT This Skill

- Automated E2E test suites → use `testing` or `playwright-e2e`.
- Driving a website in the browser → use the `browser` skill (web-only).

## Procedure

### 1. Attach to a device
```bash
adb devices          # expect the emulator or phone listed as "device"
```
If nothing is attached, launch an AVD (`emulator -avd <name>`) and wait for boot before continuing.

### 2. Launch the app cleanly
```bash
adb shell am force-stop <package>   # reset state first; bottom-nav apps collapse the back stack
adb shell am start -W -n <package>/<MainActivity>
```
Relaunching with `force-stop` between screens avoids stale-state confusion that hides bugs.

### 2b. Seed demo content (recommended before capturing)
If a list screen loads empty, the app built its own database. Seed real content first so screens show rows (see `references/room-db-seeding.md` for building a Room-compatible database).

### 3. Navigate with verification (never tap-and-capture blindly)
For each target screen:
1. Dump the hierarchy and pull it locally:
   ```bash
   adb shell uiautomator dump /sdcard/ui.xml && adb pull /sdcard/ui.xml ./ui.xml
   ```
2. Parse `bounds="[x1,y1][x2,y2]"` and tap element **centers** (not corners) with `adb shell input tap <cx> <cy>`.
3. Re-dump and confirm the target screen's **expected markers are actually present** (a title, a unique button label) before capturing. If they are missing, fix navigation first — see `references/compose-debugging.md`. Do not capture a wrong or crashed screen.

### 4. Capture and pull
```bash
adb shell screencap -p /sdcard/screen.png && adb pull /sdcard/screen.png ./screen.png
```

### 5. Send to Telegram
Send each screenshot as its own message with a caption, using the `MEDIA:` prefix on an absolute path:
```
Caption describing this screen.

MEDIA:/absolute/path/to/screen.png
```
One image per response section equals one Telegram message. If the user needs them in order, verify each arrives before sending the next.

## Pitfalls (always-on rules)
- **Verify a screen before capturing.** A tap that returns to the previous screen, or an app crash (which drops you back to the launcher), wastes a capture. Confirm target markers via dump first — one extra `uiautomator dump` is cheap versus sending the wrong image.
- **Bottom-nav apps use popUpTo.** Tapping a nav item often replaces the whole stack, so pressing BACK does not walk back through screens. Use `am force-stop` + relaunch to reset state between screens rather than relying on BACK.
- **Emulator status-bar chrome is normal.** The time/signal/battery overlay on an emulator screenshot is system UI, not a failed capture.
- **`screencap` takes `-p`, not `-png`.** The flag is a single-letter format switch (`-p` = PNG). Passing `-png` parses as several invalid flags and returns a usage message — you then pull a few hundred bytes of text, not an image. Always verify the PNG signature (`\x89PNG`) before trusting a capture.
- **Single-activity Compose apps keep `MainActivity` on top.** In-app navigation swaps composables, not activities, so dumpsys reports the same `MainActivity` for every screen and cannot tell them apart. Detect which screen you are on by screenshot content or a stable hash, not by top-activity name.
- **The keyboard shifts the layout after `input text`.** While the IME is up, everything below it has moved, so a tap at pre-keyboard coordinates lands in the keyboard area and silently misses (the tap "succeeds" but does nothing). Dismiss with `input keyevent 4`, re-dump, read the target's current bounds, then tap.
- **`input text` can inject stray characters, and DEL edits at the cursor, not the end.** Verify entered values in the uiautomator dump after typing; if a field is wrong, move the cursor to the end (`input keyevent 123`), delete per extra char (`input keyevent 67`) and retype — or clear the field wholesale and retype.

See `references/compose-debugging.md` for crashes and navigation gaps that block reaching a screen.
See `references/room-db-seeding.md` for seeding a Room-compatible database so demo screens show real content instead of an empty list.
