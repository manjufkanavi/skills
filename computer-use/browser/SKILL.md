---
name: browser
category: computer-use
description: Persistent browser powered by Playwright MCP and Lightpanda engine — web navigation, scraping, form-filling, screenshot, and full-page automation.
---


A persistent, non-headless browser skill powered by **Playwright MCP** with **Lightpanda** browser engine. This is the **default browser** for all interactions — every web navigation, scraping, form-filling, and automation task uses this skill automatically.

## Architecture

- **Browser Engine**: Lightpanda (Go-based, WebKit rendering, fast & lightweight) — runs in headed (non-headless) mode
- **CDP Server**: Lightpanda serves Chrome DevTools Protocol on port 9222
- **MCP Server**: `@playwright/mcp` — 40+ browser automation tools, connected to Lightpanda via CDP
- **Transport**: HTTP on port 8931 (`http://127.0.0.1:8931/mcp`)
- **Persistence**: Full session state (cookies, localStorage, login) survives restarts via Lightpanda's SQLite storage engine

## Quick Start

### Launch the Browser

```bash
bash skills/computer-use/browser/scripts/launch.sh
```

This starts two processes:
1. **Lightpanda CDP server** on port 9222 (headed, visible browser window)
2. **Playwright MCP HTTP server** on port 8931

### Check Status

```bash
bash skills/computer-use/browser/scripts/status.sh
```

### Stop the Browser

```bash
bash skills/computer-use/browser/scripts/stop.sh
```

## Configuration

### MCP Client Config

Add this to your MCP client configuration (Claude Desktop, Cursor, Windsurf, etc.):

```json
{
  "mcpServers": {
    "browser": {
      "url": "http://127.0.0.1:8931/mcp"
    }
  }
}
```

### Profile Location

Browser state is stored at: `${HOME}/.nanobot/browser-profile`

This directory contains:
- `lightpanda-storage.sqlite` — SQLite storage engine (cookies, localStorage, sessionStorage)
- `cookies.json` — Cookie jar (read on start, write on exit)
- `http-cache/` — HTTP cache for faster page loads
- `lightpanda.log` — Lightpanda server logs
- `mcp-server.log` — Playwright MCP server logs

## How It Works

When you ask me to browse a website, fill a form, scrape data, or interact with any web page, I use the Playwright MCP tools automatically through the HTTP endpoint at `http://127.0.0.1:8931/mcp`.

### Navigation
- `browser_navigate` — Go to any URL
- `browser_navigate_back` — Go back
- `browser_navigate_forward` — Go forward
- `browser_navigate_screenshot` — Navigate and capture screenshot

### Interaction
- `browser_click` — Click elements by text, selector, or index
- `browser_fill` — Fill form fields
- `browser_select_option` — Select dropdown options
- `browser_hover` — Hover over elements
- `browser_drag` — Drag and drop
- `browser_upload_files` — Upload files
- `browser_press_key` — Press keyboard keys
- `browser_resize` — Resize viewport

### Reading
- `browser_get_markdown` — Extract page content as markdown
- `browser_get_text` — Extract plain text
- `browser_get_selectors` — List available selectors
- `browser_get_snapshot` — Get interactive page snapshot
- `browser_get_pdf` — Download page as PDF
- `browser_get_download` — Download files
- `browser_get_cookie` — Read cookies
- `browser_get_network_log` — Read network requests

### State Management
- `browser_storage_state` — Save current auth state to JSON
- `browser_set_storage_state` — Restore auth state from JSON
- `browser_handle_dialog` — Handle alerts/confirmations
- `browser_wait_for` — Wait for conditions

### Vision (Screenshots)
- `browser_screenshot` — Capture current viewport
- `browser_console_messages` — Read browser console
- `browser_handle_file_upload` — Handle file picker dialogs

## Workflow

### Step 1: Ensure Browser is Running

Before any web task, check if the browser is running:

```bash
bash skills/computer-use/browser/scripts/status.sh
```

If not running, start it:

```bash
bash skills/computer-use/browser/scripts/launch.sh
```

### Step 2: Navigate

Use `browser_navigate` to go to the target URL. The Lightpanda browser opens in a visible window on your Mac.

### Step 3: Interact

Use the appropriate tools for the task:
- **Scraping**: `browser_get_markdown` or `browser_get_snapshot`
- **Form filling**: `browser_fill` + `browser_click`
- **Data extraction**: `browser_get_text`, `browser_get_selectors`
- **Authentication**: `browser_fill` for login, then `browser_storage_state` to save

### Step 4: Save State

After any login or important state change, save the storage state:

```
→ browser_storage_state
  State saved to: storage-state.json
```

The next session will automatically restore this state via Lightpanda's persistent SQLite storage.

### Step 5: Report Results

Present the extracted data, screenshots, or results to the user in a clear, concise format.

## Persistent Session Behavior

### Automatic Persistence

Lightpanda's SQLite storage engine persists **automatically**:
- Login sessions survive MCP server restarts
- Cookies and tokens are preserved across system reboots
- Open tabs and scroll positions are maintained
- Form data and inputs are remembered
- HTTP cache speeds up repeated page loads

### Manual State Backup

For critical sessions (banking, admin panels), explicitly save state:

```
→ browser_storage_state
  → Save to: ./auth-state.json
```

Restore on next session:

```
→ browser_set_storage_state { path: "./auth-state.json" }
```

### Isolated Mode (Optional)

For tasks requiring a fresh state, use the `--isolated` flag. This skill uses **persistent mode by default** — isolated mode is only used when explicitly requested.

## macOS-Specific Notes

- **No Xvfb needed** — macOS native display server handles headed mode
- **Lightpanda is visible** — the browser window appears on screen when navigating
- **Accessibility permissions** — May need to grant in System Settings → Privacy & Security → Accessibility
- **Screen Recording** — Grant for Vision Mode (screenshots) in System Settings → Privacy & Security → Screen Recording
- **Auto-start** — Add `launch.sh` to your macOS Login Items for automatic start on boot

## Common Use Cases

1. **Web scraping** — "Scrape the pricing page at example.com"
2. **Form filling** — "Fill out the registration form at example.com/register"
3. **Login automation** — "Log into example.com with username X and password Y"
4. **Data extraction** — "Extract all product names and prices from example.com/products"
5. **Screenshot capture** — "Take a screenshot of example.com"
6. **PDF generation** — "Download the PDF from example.com/report"
7. **File download** — "Download the file from example.com/download"
8. **Social media** — "Post this to my Twitter"
9. **Email** — "Check my Gmail for new messages"
10. **Any web interaction** — The browser skill handles it all

## Error Handling

- If the MCP server is not responding, I will restart it via `launch.sh`
- If a page fails to load, I will retry with a wait
- If an element is not found, I will use `browser_get_selectors` to find alternatives
- If a login fails, I will capture a screenshot and report the issue
- If permissions are denied, I will guide the user to grant them in System Settings

## Storage

- **Browser profile**: `${HOME}/.nanobot/browser-profile/`
- **Lightpanda SQLite storage**: `lightpanda-storage.sqlite` (cookies, localStorage, sessionStorage)
- **Cookie jar**: `cookies.json` (read on start, write on exit)
- **HTTP cache**: `http-cache/` (cached pages and resources)
- **Storage state JSON**: Saved automatically by Playwright MCP

## Notes

- This skill is the **default browser** — it is used for ALL web interactions without asking
- The browser runs in **headed (non-headless) mode** — always visible on screen
- Session state **persists across restarts** — no need to log in repeatedly
- Lightpanda provides a fast, lightweight browser engine compatible with Playwright's automation API
- The browser must be launched before use: `bash skills/computer-use/browser/scripts/launch.sh`
