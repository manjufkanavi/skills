# Playwright MCP — tool cheat sheet for video recording

Verified against `@playwright/mcp` v0.0.75 (playwright-core unified tools).
Tools are gated by capabilities: **video + tracing tools require `--caps=devtools`**,
**screenshot image responses require `--caps=vision`**. Core tools
(navigate/click/snapshot/...) are always present.

## Recording (capability: devtools)

| Tool | Args | Notes |
|---|---|---|
| `browser_start_video` | `filename?` (string), `size?` `{width,height}` | Starts recording on **all existing pages** and on **any page created afterwards** (new tabs are recorded automatically, saved as `filename-1.webm`, `filename-2.webm`, ...). Cannot be called twice without a stop. |
| `browser_stop_video` | — | Stops all recordings; returns the file names produced (one per page). Files land in the server's `--output-dir`. |
| `browser_video_chapter` | `title`, `description?`, `duration?` (ms) | Renders a **full-screen chapter card with blurred backdrop** into the live recording — great for training-style section breaks. |
| `browser_start_tracing` / `browser_stop_tracing` | — | DevTools trace (HAR-like debug), not needed for the video pipeline. |

## Navigation & interaction (core)

| Tool | Typical args |
|---|---|
| `browser_navigate` | `{url}` |
| `browser_navigate_back` | — |
| `browser_tabs` | `{index?}` — list/switch tabs; new tabs appear here |
| `browser_click` | `{target}` text or selector (also `button: "left"|"right"`, `modifiers`) |
| `browser_double_click` / `browser_drag` | — |
| `browser_fill_form` | `{fields: [{name|target, value}]}` |
| `browser_type` | `{text, submit?}` |
| `browser_hover` | `{target}` |
| `browser_press_key` | `{key}` e.g. `"Enter"`, `"Tab"` |
| `browser_select_option` | `{target, value}` |
| `browser_file_upload` | `{paths}` |
| `browser_handle_dialog` | — |
| `browser_wait_for` | `{time?}` (s) or `{text?}` (appears) or `{textGone?}` |
| `browser_resize` | `{width, height}` |

## Reading (core / vision)

| Tool | Purpose |
|---|---|
| `browser_snapshot` | Accessibility snapshot — **the primary way to find click targets** (returns a text tree with refs) |
| `browser_take_screenshot` | PNG of the viewport (image content; `--caps=vision`) — for verifying what the recording looks like |
| `browser_get_markdown` / `browser_get_text` | Page content for writing narration |
| `browser_console_messages` | Spot JS errors mid-recording |
| `browser_network_requests` | Confirm a flow actually hit the API you expect |

## How `target` resolves (v0.0.75 — read before using click/hover/fill)

`targetLocator` accepts exactly two forms:

1. **Snapshot ref** — `eN` / `fN` (regex `^(f\d+)?e\d+$`): resolved as an
   `aria-ref=` locator against the latest snapshot, optionally refined with the
   `element` description field. If the ref is stale: "Ref … not found in the
   current page snapshot. Try capturing new snapshot."
2. **Anything else → JavaScript/CSS selector** via Playwright's locator syntax.
   A plain human phrase like `"Learn More"` is NOT a fuzzy text search: it is
   parsed as a selector and must match via `page.$()`. Text split across child
   elements (very common: `<span>Learn</span> <span>More</span>`) can fail to
   match even though the a11y snapshot shows it as one node, and case matters
   in some engines ("Learn More" ≠ "Learn more").

**Reliable patterns for flaky/JS-heavy pages:**

- Snapshot first, then act by **ref** from that snapshot (re-snapshot if the
  page changes).
- Or **`browser_evaluate`** — the most deterministic option:

```json
{"tool": "browser_evaluate", "args": {"function": "() => {
  const a = [...document.querySelectorAll('a')].find(x => x.href.includes('services'));
  if (!a) return false; a.scrollIntoView({block: 'center'}); a.click(); return true;
}"}}
```

The result comes back as text (`true`/`false`) so the agent can verify each
step. Use the same pattern for highlights (`a.style.outline = '3px solid …'`)
when `browser_highlight` target resolution fails.

- `browser_route` / `browser_route_list` / `browser_unroute` — mock API responses
  (deterministic demo data: fixed customer lists, no flaky production state).
  `browser_network_state_set` — offline/slow-3G emulation.
- `browser_highlight` / `browser_annotate` / `browser_hide_highlight` — draw attention
  on an element or region while narrating it (training videos).
- `browser_verify_*` (`verify_element_visible`, `verify_text_visible`, `verify_value`, `verify_list_visible`) —
  assertions that a step succeeded before moving on.
- `browser_storage_state` / `browser_set_storage_state` — save/restore login JSON.
- `browser_close` — end of run; releases the browser.

## Pacing guidance (what a good demo looks like)

- `browser_wait_for {time: 1.2–2}` between meaningful actions so the viewer sees cause→effect.
- Hover before clicking (`browser_hover` then `browser_click`) reads as deliberate.
- Narration drives length: after recording, merge pads/freezes to audio length, so aim to
  spend roughly the narration duration per scene — don't pad with dead time in the recording.
