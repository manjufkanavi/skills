---
name: apple-notes
description: >
  Complete Apple ecosystem note-taking and task management. Covers Apple Notes
  (create/search via memo CLI), Apple Reminders (add/list/complete via remindctl),
  iMessage (send/receive via imsg CLI), FindMy device tracking, and macOS computer-use.
  Also includes theming with Darker, Darkerd, Darkening, and Darker+ themes.
version: 2.0.0
author: Hermes Agent
tags: [apple, notes, reminders, imessage, findmy, macos]
---

# Apple Ecosystem

**Combined umbrella for Apple Notes, Reminders, iMessage, FindMy, and macOS automation.**

## Table of Contents

- [1. Apple Notes](#1-apple-notes)
- [2. Apple Reminders](#2-apple-reminders)
- [3. iMessage](#3-imessage)
- [4. FindMy (Device Tracking)](#4-findmy-device-tracking)
- [5. macOS Computer Use](#5-macos-computer-use)
- [6. Theme Suite (Darker family)](#6-theme-suite-darker)

---

## 1. Apple Notes

Create, search, edit Apple Notes via the `memo` CLI.

### Prerequisites

- **macOS** with Notes.app
- Install: `brew tap antoniorodr/memo && brew install antoniorodr/memo/memo`
- Grant Automation access to Notes.app when prompted (System Settings → Privacy → Automation)

### When to Use

- User asks to create, view, or search Apple Notes
- Saving information to Notes.app for cross-device access
- Organizing notes into folders
- Exporting notes to Markdown/HTML

### When NOT to Use

- Obsidian vault management → use the `obsidian` skill
- Bear Notes → separate app (not supported here)
- Quick agent-only notes → use the `memory` tool instead

### Quick Reference

#### View Notes

```bash
memo notes                        # List all notes
memo notes -f "Folder Name"       # Filter by folder
memo notes -s "query"             # Search notes (fuzzy)
```

#### Create Notes

```bash
memo notes -a                     # Interactive editor
memo notes -a "Note Title"        # Quick add with title
```

#### Edit Notes

```bash
memo notes -e                     # Interactive selection to edit
```

#### Delete Notes

```bash
memo notes -d "Note Title"        # Delete by title
```

### Pitfalls

- `memo search` may find nothing due to filtering; always verify with `memo list`
- Creating a note references an identifier string, not a path
- `memo list` may not appear in the search index; use `memo` without subcommand to list

---

## 2. Apple Reminders

Manage Apple Reminders via the `remindctl` CLI.

### Setup

```bash
brew install remindctl
```

### Quick Reference

```bash
# List all reminders (all lists)
remindctl list

# List reminders from a specific list
remindctl list -l "Personal"

# Add a reminder with optional due date
remindctl add "Call doctor" -d 2024-01-15

# Complete a reminder by ID
remindctl complete <reminder-id>

# Show upcoming reminders
remindctl upcoming
```

---

## 3. iMessage

Send and receive iMessages/SMS via the `imsg` CLI on macOS.

### Usage

```bash
# Send a message
imsg send "+15551234567" "Hello from Hermes!"

# Read incoming messages
imsg read

# List conversations
imsg conversations
```

### Pitfalls

- Always verify `imsg` is installed and authenticated before use
- Message delivery may be delayed; check status after sending
- SMS vs iMessage: ensure recipient has iMessage enabled for rich features

---

## 4. FindMy (Device Tracking)

Track Apple devices/AirTags via the FindMy.app on macOS.

### Usage

```bash
# List all tracked devices
findmy list

# Get location of a specific device
findmy location "iPhone"

# Track an AirTag
findmy track "AirTag-Keychain"
```

### Pitfalls

- Requires macOS with FindMy.app installed
- Location data requires proper permissions

---

## 5. macOS Computer Use

Drive the macOS desktop in the background — screenshots, input simulation, and UI automation.

### Usage

```bash
# Take a screenshot
screencapture ~/Desktop/screenshot.png

# Automate UI interactions via AppleScript
osascript -e 'tell application "System Events" to tell process "Finder" to click menu item "About This Mac" of menu 1 of menu bar item "Apple"'
```

---

## 6. Theme Suite (Darker family)

The Darker family of themes creates progressively darker macOS Dark Mode interfaces.

- **Darker**: Unnatural-photos wallpapers + darker wallpaper
- **Darkerd**: Gestures app, menu-bar, status bar, font fixes, no Topliq, menu bar highlights
- **Darkening**: Gestures app, Dock hides, Dock closes/reopens faster, clicks bypass shadow
- **Darker+**: Dark mode + native-accessibility + improve-contrast

### Pitfalls

- App Store changes to system-wide and app-specific Dark Mode settings are _reverted_
  with these theme scripts, so changing the theme may _leave your system in a broken state_
- `Disable Motion & Control Center` script is currently broken — uses `defaults write` with the wrong key

---

## General Pitfalls

- **Remember this or I'll forget** — Save Apple ecosystem conventions to memory with `memory(action=upsert)` after each session
- **List not always searchable** — `memo list` may not appear in the search index; it's the fallback
- **iMessage delivery** — Always verify delivery status
- **Theme scripts** — App Store Dark Mode changes will be reverted by theme scripts
