# Playwright MCP with Lightpanda Browser — Persistent Sessions on macOS

**Research Date:** 2026-07-10  
**Topic:** Using Playwright MCP with Lightpanda browser, non-headless mode, persistent sessions across restarts on macOS

---

## Executive Summary

There are **two distinct approaches** to this setup, and understanding the distinction is critical:

1. **Playwright MCP Server** (Microsoft's official `@playwright/mcp`) — an MCP server that uses Playwright under the hood to automate browsers (Chrome, Firefox, WebKit, Edge).
2. **Lightpanda MCP** (Lightpanda's built-in MCP server) — Lightpanda has its own native MCP server (`lightpanda mcp`), separate from Playwright.

Additionally, **Playwright can connect to Lightpanda via CDP** (Chrome DevTools Protocol), allowing Playwright's automation tools to control a Lightpanda browser instance.

This report covers all three approaches with a focus on **non-headless mode** and **session persistence** on macOS.

---

## 1. Playwright MCP Server (Microsoft Official)

### Installation

```bash
npm install -g @playwright/mcp@latest
```

### Configuration in MCP Client

Add to your MCP client config (e.g., Claude Desktop, Cursor, Windsurf):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

### Non-Headless Mode (Default)

Playwright MCP runs in **headed (non-headless) mode by default** — the browser window is visible on screen. This is ideal for macOS with a display.

To explicitly run headed (no flag needed — it's the default):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

To run headless instead:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless"]
    }
  }
}
```

### Browser Selection

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--browser=chrome"]
    }
  }
}
```

Supported browsers: `chrome` (default), `firefox`, `webkit`, `msedge`.

### Session Persistence — The Key Feature

**Playwright MCP persists login state, cookies, and localStorage between sessions by default.** This is its standout feature.

#### How It Works

By default, Playwright MCP uses a **persistent profile mode**. Each project/workspace gets a separate profile directory where browser data is stored on disk:

| Platform | Default Profile Location |
|----------|-------------------------|
| **macOS** | `~/Library/Caches/ms-playwright/mcp-{channel}-profile` |
| Linux | `~/.cache/ms-playwright/mcp-{channel}-profile` |
| Windows | `%LOCALAPPDATA%\ms-playwright\mcp-{channel}-profile` |

This means:
- Login to a website → close MCP server → restart MCP server → you're still logged in
- Cookies, localStorage, and session data survive server restarts and system reboots
- Each MCP client workspace gets its own isolated profile

#### Custom Profile Directory

Override the default profile location:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--user-data-dir=/path/to/custom/profile"]
    }
  }
}
```

Or via CLI:

```bash
npx @playwright/mcp@latest --user-data-dir=/Users/you/playwright-profile
```

#### Isolated Mode (No Persistence)

If you want fresh state every time:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--isolated"]
    }
  }
}
```

#### Storage State Workflow

For explicit control over saved state:

```
# Save current auth state
→ browser_storage_state
  State saved to: auth-state.json

# Next session: restore state
→ browser_set_storage_state { path: "./auth-state.json" }
→ browser_navigate { url: "https://app.example.com/dashboard" }
  // Already logged in
```

Or load state automatically on startup:

```bash
npx @playwright/mcp@latest --caps=storage --isolated --storage-state=./auth-state.json
```

### HTTP Transport for Persistent Server

For a long-running MCP server (survives client reconnections):

```bash
# Start as HTTP server
npx @playwright/mcp@latest --port 8931

# Connect from MCP client
{
  "mcpServers": {
    "playwright": {
      "url": "http://localhost:8931/mcp"
    }
  }
}
```

Use `--shared-browser-context` to share a single browser context between multiple connected clients.

### macOS-Specific Notes

- **No Xvfb needed** — macOS has a native display server (WindowServer). Headed mode works out of the box.
- **Permissions** — macOS may prompt for Accessibility permissions. Grant in System Settings → Privacy & Security → Accessibility.
- **Screen Recording** — If using Vision Mode (screenshots), grant Screen Recording permission.
- **No sandbox** — If running in a container or restricted environment, use `--no-sandbox`.

### Advanced Configuration File

For complex setups, use a JSON config file:

```bash
npx @playwright/mcp@latest --config path/to/config.json
```

```json
{
  "browser": {
    "browserName": "chromium",
    "isolated": false,
    "userDataDir": "/Users/you/playwright-profile",
    "launchOptions": {
      "headless": false,
      "args": ["--start-maximized"]
    },
    "contextOptions": {
      "viewport": { "width": 1280, "height": 720 }
    }
  },
  "saveSession": true,
  "sharedBrowserContext": true,
  "capabilities": ["core", "storage", "network", "testing"]
}
```

---

## 2. Lightpanda MCP Server (Native)

Lightpanda has its **own built-in MCP server** — no Playwright needed.

### Installation

```bash
# Homebrew
brew install lightpanda-io/lightpanda/lightpanda

# Or download from https://lightpanda.io/docs/run-locally/installation/package-managers
```

### Starting the MCP Server

```bash
lightpanda mcp
```

### Configuration in MCP Client

```json
{
  "mcpServers": {
    "lightpanda": {
      "command": "/usr/local/bin/lightpanda",
      "args": ["mcp"]
    }
  }
}
```

With robots.txt compliance:

```json
{
  "mcpServers": {
    "lightpanda": {
      "command": "/usr/local/bin/lightpanda",
      "args": ["mcp", "--obey-robots"]
    }
  }
}
```

### Lightpanda MCP Features

- **25+ tools**: goto, click, fill, evaluate, extract, search, markdown, html, etc.
- **Resources**: `mcp://page/html` and `mcp://page/markdown` for reading page state
- **Session persistence**: Lightpanda maintains state (cookies, localStorage) within a single MCP session
- **PandaScript**: Save sessions as reusable `.js` files via the `save` tool

### HTTP Transport with Stateful Sessions

Lightpanda MCP natively supports only stdio. For HTTP transport with persistence:

```bash
npx -y supergateway \
  --stdio "lightpanda mcp" \
  --outputTransport streamableHttp \
  --stateful --sessionTimeout 180000 \
  --port 8000
```

The `--stateful --sessionTimeout 180000` flag keeps the browser alive for 3 hours across HTTP requests.

### Debugging

```bash
lightpanda mcp --log-level info --log-format pretty
# Or pipe logs to file
lightpanda mcp --log-level info 2>lightpanda.log
```

---

## 3. Playwright + Lightpanda via CDP (Hybrid Approach)

This is where Playwright **controls** a Lightpanda browser instance via Chrome DevTools Protocol.

### Step 1: Start Lightpanda as a CDP Server

```bash
lightpanda serve --host 127.0.0.1 --port 9222
```

This starts Lightpanda listening on CDP port 9222.

### Step 2: Connect Playwright to Lightpanda

```javascript
import { chromium } from 'playwright-core';

const browser = await chromium.connectOverCDP('ws://127.0.0.1:9222');
const context = await browser.newContext({});
const page = await context.newPage();

await page.goto('https://wikipedia.com/');
const title = await page.locator('h1').textContent();
console.log(title);

await page.close();
await context.close();
await browser.close();
```

### Session Persistence with CDP

To persist state across restarts:

1. **Start Lightpanda with a user data directory:**
   ```bash
   lightpanda serve --host 127.0.0.1 --port 9222 --user-data-dir=/Users/you/lightpanda-profile
   ```

2. **Connect Playwright and save state:**
   ```javascript
   const browser = await chromium.connectOverCDP('ws://127.0.0.1:9222');
   const context = await browser.newContext({});
   const page = await context.newPage();
   
   // ... do login ...
   
   // Save storage state
   await context.storageState({ path: 'auth-state.json' });
   ```

3. **Next session — restore state:**
   ```javascript
   const browser = await chromium.connectOverCDP('ws://127.0.0.1:9222');
   const context = await browser.newContext({ storageState: 'auth-state.json' });
   ```

### Non-Headless Mode with CDP

Lightpanda's `serve` command runs in **headed mode by default** on macOS — the browser window is visible. No special flags needed.

To verify:

```bash
lightpanda serve --host 127.0.0.1 --port 9222 --log-level info
```

The `--log-level info` flag shows that the browser launches with a visible window.

---

## 4. Recommended Architecture for Your Use Case

For **persistent sessions across multiple restarts on macOS (non-headless)**, here's the recommended setup:

### Option A: Playwright MCP Server (Simplest)

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--user-data-dir=/Users/manjunath/playwright-mcp-profile"]
    }
  }
}
```

**Pros:**
- Zero configuration for persistence — works out of the box
- Visible browser window (headed by default)
- Full Playwright toolset (40+ tools)
- Profile survives reboots automatically

**Cons:**
- Uses Chromium under the hood (not Lightpanda)

### Option B: Playwright + Lightpanda via CDP (Full Control)

```bash
# Start Lightpanda CDP server (add to launch agent for auto-start)
lightpanda serve --host 127.0.0.1 --port 9222 --user-data-dir=/Users/manjunath/lightpanda-profile
```

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--browser=chrome", "--user-data-dir=/Users/manjunath/playwright-mcp-profile"]
    }
  }
}
```

Then use Playwright's `chromium.connectOverCDP()` in custom scripts to control Lightpanda.

**Pros:**
- Uses Lightpanda browser (faster, lighter, open-source)
- Full Playwright API for automation
- Persistent state via user-data-dir

**Cons:**
- More complex setup
- Requires managing two processes

### Option C: Lightpanda Native MCP (Lightweight)

```json
{
  "mcpServers": {
    "lightpanda": {
      "command": "/usr/local/bin/lightpanda",
      "args": ["mcp"]
    }
  }
}
```

**Pros:**
- Single binary, no dependencies
- Built-in MCP support
- Lightweight

**Cons:**
- Fewer tools than Playwright MCP
- Session state is per-session (not cross-restart by default)
- No Playwright API

---

## 5. Making It Survive System Restarts on macOS

### Auto-Start Lightpanda CDP Server

Create a `launchd` agent:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.lightpanda.cdp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/lightpanda</string>
        <string>serve</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>9222</string>
        <string>--user-data-dir</string>
        <string>/Users/manjunath/lightpanda-profile</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/lightpanda-cdp.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/lightpanda-cdp-error.log</string>
</dict>
</plist>
```

Save as `~/Library/LaunchAgents/io.lightpanda.cdp.plist` and run:

```bash
launchctl load ~/Library/LaunchAgents/io.lightpanda.cdp.plist
```

### Auto-Start Playwright MCP Server

For a persistent Playwright MCP HTTP server:

```bash
# Start in background
npx @playwright/mcp@latest --port 8931 --shared-browser-context &
```

Or use the same `launchd` approach with the npx command.

---

## 6. Comparison Table

| Feature | Playwright MCP | Lightpanda MCP | Playwright + Lightpanda CDP |
|---------|---------------|----------------|----------------------------|
| **Browser** | Chromium (default) | Lightpanda | Lightpanda |
| **Non-headless** | ✅ Default | ✅ Default | ✅ Default |
| **Session Persistence** | ✅ Auto (disk profile) | ⚠️ Per-session | ✅ Via user-data-dir |
| **Tools Available** | 40+ | 25+ | Full Playwright API |
| **Setup Complexity** | Low | Low | Medium |
| **Cross-Restart State** | ✅ Yes | ⚠️ Limited | ✅ Yes |
| **macOS Display** | Native (no Xvfb) | Native (no Xvfb) | Native (no Xvfb) |

---

## 7. Key Takeaways

1. **Playwright MCP runs headed by default** on macOS — no headless flag needed.
2. **Session persistence is automatic** with Playwright MCP — profiles are stored in `~/Library/Caches/ms-playwright/mcp-{channel}-profile`.
3. **Lightpanda has its own MCP server** (`lightpanda mcp`) — separate from Playwright MCP.
4. **Playwright can control Lightpanda via CDP** — start Lightpanda with `lightpanda serve` and connect via `chromium.connectOverCDP()`.
5. **No Xvfb needed on macOS** — the native display server handles headed mode.
6. **For cross-restart persistence**, use `--user-data-dir` with a persistent path, or use `launchd` to auto-start the browser server.
7. **Lightpanda is faster and lighter** than Chromium — it's a Go-based browser with a WebKit rendering engine, designed for automation.

---

## References

- Playwright MCP Docs: https://playwright.dev/mcp/introduction
- Playwright MCP Configuration: https://playwright.dev/mcp/configuration/options
- Playwright MCP User Profile: https://playwright.dev/mcp/configuration/user-profile
- Playwright MCP Storage: https://playwright.dev/mcp/tools/storage
- Playwright MCP GitHub: https://github.com/microsoft/playwright-mcp
- Lightpanda MCP: https://lightpanda.io/docs/usage/mcp
- Lightpanda Playwright via CDP: https://lightpanda.io/docs/usage/cdp/playwright
- Lightpanda Serve Command: https://lightpanda.io/docs/run-locally/commands/serve
- Lightpanda Architecture: https://lightpanda.io/blog/posts/web-automation-stack-explained
