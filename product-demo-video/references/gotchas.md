# Gotchas & lessons

## Recording

- **`--caps=vision,devtools` is mandatory.** Video tools (`browser_start_video`,
  `browser_stop_video`, `browser_video_chapter`) are filtered out unless the
  `devtools` capability is enabled; screenshots return no image without `vision`.
  The `--caps` flag or `PLAYWRIGHT_MCP_CAPS` env var sets it.
- **Video is per-page.** `browser_start_video` records every open page and every
  page created afterwards; `browser_stop_video` returns multiple file names
  (`name.webm`, `name-1.webm`, ...) if the flow opened tabs. Prefer in-tab
  navigation; when multiple webms come back, merge each with its scene audio
  share or concat them in order before merging.
- **Scrolling has no dedicated tool** — use `browser_mouse_wheel
  {deltaY: 600}` or `browser_press_key {key: "End"|"PageDown"}`.
- **`target` is not fuzzy text search** — it is a snapshot ref (`eN`) or a
  JS/CSS selector. Split text nodes and case differences make phrase targets
  fail; prefer refs or `browser_evaluate` (href/textContent matching). See
  "How target resolves" above.
- One recording at a time. Calling `browser_start_video` while one is active
  throws "Video recording has already been started." — always stop first.
- **Headless works for video** (Chromium new headless). No screen-recording
  permission needed on macOS. The user's default is headless; `--headed`
  (launch-mcp.sh) is available for live watching.
- **Never record via the Lightpanda/CDP-endpoint setup** (the `computer-use/browser`
  skill). `browser_start_video` drives Playwright's own browser launch; a
  `--cdp-endpoint`-attached session is a different code path and the
  `browser` skill's Lightpanda engine is for scraping, not video. This skill
  always runs its own Chrome (`--browser=chrome`).
- **Pacing inside the recording matters less than it seems** — merge pads or
  freezes to the narration length. But dead air at the *start* of a scene shows
  a blank first frame when frozen; keep the scene starting on a settled page.

## Multi-client / fallback driver

- **`--shared-browser-context` is required for multi-call flows.** Without it
  every MCP client session (and every reconnection) gets its own fresh browser:
  navigations, routes, and any active recording vanish. With it, all clients
  share one browser+context. This applies to the HTTP fallback AND to the
  stdio-registered server (a dropped connection = new client session).
- **Video filenames must be ABSOLUTE paths.** A bare `filename: "scene.webm"`
  lands in the *server process CWD*, not `--output-dir` (output-dir only
  governs server-generated artifacts like snapshots). Use the full run-dir
  path: `"/abs/…/record/scene_01.webm"`.
- **`target` must resolve.** Text targets are looked up on the live page; a
  text that isn't present falls through to CSS-selector parsing and errors
  ("Unexpected token ... css selector"). Ground targets in `browser_snapshot`
  output (element text or `[ref=eN]`) before recording.
- **HTTP mode needs `--host 127.0.0.1 --allowed-hosts '*'`.** The server's
  default "localhost" binds IPv6 ::1 only (127.0.0.1 clients can't reach it),
  and its host-allowlist check additionally demands a literal `localhost`
  Host header. launch-mcp.sh sets both; it is loopback-only so disabling the
  check is safe.
- Each `mcp-client.py` call performs a fresh MCP `initialize`, but the server
  keeps the browser (and its state: cookies, tabs, routes, active recording)
  across sessions — that's by design. Do NOT restart the server mid-run.
- `mcp-client.py` exits 2 on tool `isError`, 3 on connection error. A "No video
  files were returned" text result is not an error exit — check for webm files
  on disk in the run dir (and the `-1` suffix variants).
- Ports: the recording MCP uses 8971 (`PDV_MCP_PORT`) so it never collides with
  the `computer-use/browser` skill (8931+). `launch-mcp.sh` kills whatever is
  on the port before starting.

## Merging

- ffmpeg's `concat` demuxer with `-c copy` requires identical encoding params —
  merge-scene.py enforces them (w/h/fps/pix_fmt/sar + AAC 44.1k stereo). If a
  clip came from elsewhere, re-encode it to the same params first.
- `tpad=stop_mode=clone` freezes the **last** frame; it can't add motion. Long
  audio over a short action is the main case; for >5 s of freeze, prefer to
  write more narration-matching actions into the scene instead.
- Variable-fps webm + `-r 30` can produce tiny timestamp jitter; harmless for
  this use case (UI content). If concat complains, re-encode clips with
  `-vsync cfr` (or `-fps_mode cfr`).

## Delivery (Telegram)

- Bot upload limit is **50 MB** for `sendVideo`. Budget 48 MB (`max_size_mb`).
  The concat script auto-re-encodes (crf 27 → 960x540 crf 27).
- Deliver with `MEDIA:/absolute/path/final.mp4` — H.264/AAC yuv420p +
  faststart plays inline as a video message.
- WhatsApp has similar caps; if the user wants it there, keep under 16 MB
  (re-encode harder).

## TTS

- Kokoro pause behavior follows punctuation: use commas/periods/ellipses in the
  narration text to shape timing. Write narration the way a voiceover artist
  would read it.
- Speed 0.85–0.95 sounds more human than 1.0 (both skills document this).
- Local `kokoro-tts` is offline and instant; `--production` (kokoro-tts-production)
  needs network to the hosted API and fetches a key over SSH per run — use it
  only when the user wants a different voice.
- Very long narration strings: pass as a positional argv (tts.py handles
  segmentation at ~380 chars/sentence); avoid shell-quoting hell by always
  going through `tts-narration.py` (subprocess list, not a shell string).

## Scenario authoring

- One scene ≈ one idea ≈ 15–60 s of audio. 3–6 scenes is the sweet spot for a
  product demo; >8 scenes usually means the video is a manual, not a demo.
- If a step depends on login, record the login into the **profile** first
  (persistent `--user-data-dir`), then scenes can assume an authenticated app.
  Alternatively `browser_set_storage_state` at the top of the run.
- Flaky/dynamic sites: mock the data sources with `browser_route` so every
  re-render of the video shows the same data.
