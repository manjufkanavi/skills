# Gotchas & lessons

## Quality: the "it looks like screenshots" failure mode

- **Narration FIRST, then record to fill it.** tts-narration.py runs before
  recording; each scene's audio duration is the target recording length
  (aim 1.0–1.3×). If the merge log shows a >3 s freeze pad
  ("freezing last frame for 6.5s"), the recording was too short — re-record
  the scene with more interaction (hovers, scrolls, settle time), never ship
  the freeze.
- **Record the real interaction, not keyframes.** Nav hovers, card hovers,
  full-page scrolls, CTAs, the URL load. A 15 s narration needs ~15 s of
  actual mouse work in the footage.
- Scene 1 must start on a blank tab and record THROUGH the navigation load;
  the URL-bar card (concat-final `--url`) supplies the literal "entering the
  URL" beat.

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
- **`--fresh` (isolated in-memory profile) for public sites; the persistent
  profile for logged-in products.** The shared profile accumulates cookies from
  other runs and can change what a marketing page shows; `--isolated` keeps
  re-runs reproducible.
- **Never record via the Lightpanda/CDP-endpoint setup** (the `computer-use/browser`
  skill). `browser_start_video` drives Playwright's own browser launch; a
  `--cdp-endpoint`-attached session is a different code path and the
  `browser` skill's Lightpanda engine is for scraping, not video. This skill
  always runs its own Chrome (`--browser=chrome`).
- **For scenes after the first, start on a settled page:** dead air at a
  scene's start becomes a frozen first frame when the merge pads to the audio
  length. (Scene 1 is the exception — it records blank→load on purpose; see
  the Quality section above.)

## Multi-client / fallback driver

- **`--shared-browser-context` is required for multi-call flows.** Without it
  every MCP client session gets its own browser. Set it on both the HTTP
  fallback and the stdio registration. Caveat: when the last client
  disconnects the server closes the browser, so a later reconnection still
  gets a fresh browser — state only survives while clients remain connected
  (hence `--script` for long flows).
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
- **When the last client disconnects, the server closes the browser**
  (client count → 0). One-shot `mcp-client.py` calls therefore each get a
  fresh browser — earlier navigations/routes/recording are gone no matter what
  flags you pass. Multi-step flows MUST run in `--script` mode (one client,
  one persistent session). Do NOT restart the server mid-run.
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
- `tpad=stop_mode=clone` freezes the **last** frame; it can't add motion. A
  freeze pad means the recording came in shorter than the narration —
  re-record with more interaction (Quality section: >3 s freeze = defect).
- Variable-fps webm + `-r 30` can produce tiny timestamp jitter; harmless for
  this use case (UI content). If concat complains, re-encode clips with
  `-vsync cfr` (or `-fps_mode cfr`).

## QA without vision

vision_analyze can be unavailable (connection errors); verify a finished video
programmatically:

- Extract one frame per segment + the title card:
  `ffmpeg -ss T -i final.mp4 -frames:v 1 f.png`.
- PIL grayscale stats per frame: real page content has high stdev; a
  blank/black frame ≈ 0. The bottom 96 px (caption bar) mean settles near
  ~120 when a dark 84%-alpha bar overlays a bright page, with stdev > 10
  (bar text present).
- Compare stats across scene frames — near-identical frames mean the same page
  was recorded twice (a navigation failed).
- Audio: `ffmpeg -i final.mp4 -af volumedetect -f null -` → `mean_volume`
  ≈ -20 to -25 dB for narration; near -91 dB = silent track.
- ffprobe the final file: h264 + aac + yuv420p, else Telegram won't play it inline.

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
