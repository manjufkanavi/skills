---
name: product-demo-video
description: "Use when making demo or training videos from any website — Playwright MCP screencast, Kokoro narration, ffmpeg merge, Telegram delivery."
version: 1.0.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [video, screencast, demo, training, playwright, mcp, kokoro, ffmpeg, telegram]
---

# Product Demo Video

Turn **any website** into a narrated product demo / training video:
screencast with Playwright MCP → narrate with Kokoro → merge with ffmpeg →
deliver over Telegram.

Triggers: "make a demo video of X", "record a training video for my product",
"screen recording with narration", "product walkthrough video".

## Pipeline

```
scenario.yaml ──► record (Playwright MCP, per-scene webm)
                 │        └─ Kokoro TTS per-scene mp3
                 └─► merge (ffmpeg: freeze/silence pad, captions, normalize)
                     └─► concat (intro card + scenes, ≤48 MB) ──► MEDIA: final.mp4
```

## Prerequisites (all verified on this machine)

| Piece | Where |
|---|---|
| `@playwright/mcp` (v0.0.75+, has video tools) | global npm, `/opt/homebrew/lib/node_modules/@playwright/mcp` |
| Chrome + Playwright browsers | `/Applications/Google Chrome.app`, `~/Library/Caches/ms-playwright` |
| ffmpeg (libx264) | `/opt/homebrew/bin/ffmpeg` |
| Python `mcp` package (fallback client) | stdlib-adjacent, `pip show mcp` |
| PIL + PyYAML (cards, scenario parsing) | installed |
| `kokoro-tts` sibling skill (default TTS) | `../kokoro-tts/scripts/tts.py` — offline ONNX |
| `kokoro-tts-production` (optional, `--production`) | `../kokoro-tts-production/scripts/kokoro_tts.py` |

## Step 0 — choose the MCP access path

Check whether your toolset contains `mcp_playwright_browser_*` tools:

- **Yes (registered)** — use the MCP tools directly. They run a Chrome launched
  by Hermes with the same flags as `launch-mcp.sh` (caps=vision,devtools,
  output-dir = the run dir).
- **No** — use the fallback driver:

```bash
RUN=~/.hermes/product-demo-video/runs/$(date +%Y%m%d_%H%M%S)
bash <skill>/scripts/launch-mcp.sh --out "$RUN"        # prints RUNDIR= URL= PID=
python3 <skill>/scripts/mcp-client.py "$URL" browser_navigate '{"url":"..."}'
```

Registering for future sessions (one-time, needs gateway restart):

```bash
hermes mcp add playwright --command npx --args -y @playwright/mcp --browser=chrome --headless --caps=vision,devtools --shared-browser-context --output-dir=$HOME/.hermes/product-demo-video/recordings --user-data-dir=$HOME/.hermes/product-demo-video/browser-profile --viewport-size=1280x720
```

After restart, tools appear as `mcp_playwright_browser_navigate`, etc.
(Headless is the default per user preference; pass `--headed` to launch-mcp.sh
or drop `--headless` from the registration to watch it build.)

## Step 1 — author the scenario

Copy `templates/scenario.yaml` into the run dir and fill it in:
`title`, `url`, per-scene `{id, title, url?, narration, actions[]}`.

If the user only gave a URL: explore first — `browser_navigate` +
`browser_snapshot` (and `browser_take_screenshot` saved via
`--save-images`, then `vision_analyze`) to learn the site, then **propose the
scene list + narration drafts to the user and get approval before recording.**
Scene = one idea ≈ 15–60 s of narration; 3–6 scenes for a demo.

## Step 2 — record (one webm per scene)

For scene N (webm name `scene_NN_<id>.webm`):

1. `browser_navigate` to the scene's URL (or continue on the current page)
2. wait for the page to settle (`browser_wait_for {time: 1.5}`)
3. `browser_start_video {"filename": "scene_NN_<id>.webm", "size": {"width": 1280, "height": 720}}`
4. run the scene's actions with human pacing:
   - hover before clicking; `browser_wait_for {time: 1.2–2}` between actions
   - `browser_highlight` on the element you're about to narrate (training style)
   - `browser_video_chapter` for section breaks (renders a styled chapter card)
   - `browser_verify_*` after important steps; if a step fails, `browser_snapshot` and adjust the selector — never let a failed click stay in the footage
5. `browser_stop_video` → the response lists file(s); confirm the webm(s) exist
   in the run dir (new tabs produce `name-1.webm` suffix files — concat those in order if a scene spans tabs)

After all scenes: `browser_close`.

## Step 3 — narrate

```bash
python3 <skill>/scripts/tts-narration.py <run>/scenario.yaml --run-dir "$RUN" \
  [--voice im_nicola] [--speed 0.9] [--production]
# prints a JSON manifest: [{scene, id, file, duration}, ...]
```

## Step 4 — merge per scene

For each scene (use the manifest file path; webm = the recorded file from step 2):

```bash
python3 <skill>/scripts/render-card.py caption --text "N. <Scene Title>" --w 1280 --h 96 --out <run>/caps/capNN.png
python3 <skill>/scripts/merge-scene.py --video <run>/record/scene_NN.webm \
  --audio <run>/audio/scene_NN.mp3 --out <run>/clips/scene_NN.mp4 \
  --caption <run>/caps/capNN.png --caption-dur 4.5
```

Scene length = max(video, audio): audio longer → freeze last frame; video
longer → silence tail. Skip `--caption` if the scenario says `captions: false`.

## Step 5 — assemble + size budget

```bash
python3 <skill>/scripts/concat-final.py --out <run>/final.mp4 \
  --inputs <run>/clips/scene_01.mp4 ... --title "<title>" --subtitle "<subtitle>" \
  --max-mb 48
# prints JSON: {"path", "size_mb", "duration_s"}
```

## Step 6 — deliver

Reply with `MEDIA:<absolute path to final.mp4>` (inline Telegram video) plus a
short summary: scene list, total duration, size. If >50 MB survives the
re-encode ladder, split or shorten instead of uploading.

## Pitfalls (full list in references/gotchas.md)

- `--caps=vision,devtools` is required for video tools to exist.
- Video is per-page; multi-tab scenes yield suffixed webms.
- Don't use the Lightpanda `browser` skill for recording — this skill always
  drives its own Chrome.
- 50 MB Telegram bot upload cap → 48 MB budget.
- Kokoro pauses follow punctuation; write narration like a voiceover script.

## Files

- `scripts/launch-mcp.sh` — start Playwright MCP HTTP server (caps=vision,devtools, persistent profile)
- `scripts/mcp-client.py` — single-call MCP client (fallback when tools unregistered); `--save-images DIR`
- `scripts/tts-narration.py` — per-scene Kokoro narration + JSON manifest
- `scripts/merge-scene.py` — webm+mp3(+caption) → normalized mp4
- `scripts/concat-final.py` — intro card + concat + 50 MB budget
- `scripts/render-card.py` — PIL title cards / caption bars
- `templates/scenario.yaml` — annotated example
- `references/mcp-tools.md` — Playwright MCP tool cheat sheet
- `references/ffmpeg-recipes.md` — exact filter graphs
- `references/gotchas.md` — everything that bites
