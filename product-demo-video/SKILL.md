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
scenario.yaml ──► narrate (Kokoro, per-scene mp3) ──► audio durations
                 └─► record (Playwright MCP, FULL interaction,
                     sized to the narration: URL load, every hover/scroll/click)
                     └─► merge (ffmpeg: real motion + ≤3s pad, captions)
                         └─► concat (title + URL-bar card + scenes, ≤48 MB)
                             └─► MEDIA: final.mp4
```

The narration is generated **before** recording and **drives the recording
length**: the interaction is written/paced to roughly fill the audio, so the
finished video is real motion end-to-end — not a slideshow of frozen frames.

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

Registering for future sessions (one-time):

```bash
echo Y | hermes mcp add playwright --command npx --args -y @playwright/mcp --browser=chrome --headless --caps=vision,devtools --shared-browser-context --output-dir=$HOME/.hermes/product-demo-video/recordings --user-data-dir=$HOME/.hermes/product-demo-video/browser-profile --viewport-size=1280x720
```

`echo Y |` answers the "Enable all N tools?" prompt — without a TTY the prompt
is Cancelled and **nothing is saved** (the add looks like it ran; it didn't).
Tools appear as `mcp_playwright_browser_navigate`, etc.; run `/reload-mcp` in
an open session to load them without a gateway restart.
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

## Step 2 — narrate first (the narration drives recording length)

```bash
python3 <skill>/scripts/tts-narration.py <run>/scenario.yaml --run-dir "$RUN" \
  [--voice im_nicola] [--speed 0.9] [--production]
# prints a JSON manifest: [{scene, id, file, duration}, ...]
```

Note each scene's `duration` — it is the **target recording length** for
step 3.

## Step 3 — record the COMPLETE interaction, sized to the narration

The video must contain the **full real interaction** — the URL load, every
hover, scroll, and click the user would actually make. Record it long enough
to roughly fill the scene's narration (aim: recorded ≈ 1.0–1.3× audio).
A real interaction slightly longer than the audio is fine (silence tail);
**a scene padded with >3 s of frozen video is a defect — re-record it.**

For scene N (webm name `<run>/record/scene_NN_<id>.webm`, **absolute path**):

1. Scene 1 starts on a **fresh tab**: `browser_start_video` while blank,
   then `browser_navigate` — the blank→load transition is part of the footage
   (the "URL entry" moment itself is the intro URL-bar card, added by
   `concat-final.py --url`).
   Later scenes: navigate to the scene URL (or continue on the current page
   if the previous scene's click already landed there — avoid reload flashes).
2. Run the scene's actions with **human pacing**: hover every interactive
   element (nav items, cards, CTAs) with 1.2–2.5 s waits, scroll through
   all the content, click through. Use `browser_mouse_wheel` / refs /
   `browser_evaluate` per references/mcp-tools.md.
3. Verify each step (evaluate returns, snapshot after navigations). If the
   page drifted from the plan, re-ground with `browser_snapshot` and adapt —
   the interaction must stay coherent, not scripted-robotic.
4. `browser_stop_video` → confirm the webm exists. If the interaction came in
   shorter than the narration, extend it (more hovers/scrolls/settle time)
   and re-record that scene rather than accepting a long freeze.
5. After all scenes: `browser_close`.

## Step 4 — merge per scene

For each scene (use the manifest file path; webm = the recorded file from step 3):

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
  --url "<the site URL>" --max-mb 48
# prints JSON: {"path", "size_mb", "duration_s"}
```

## Step 6 — verify, then deliver

QA the finished file before claiming success (details: gotchas.md "QA without
vision"): extract one frame per scene + the title card (`ffmpeg -ss T -i
final.mp4 -frames:v 1 f.png`) and check with vision_analyze, or with the PIL
frame-statistics fallback when vision is unavailable; confirm audio is present
(`ffmpeg -i final.mp4 -af volumedetect -f null -` — narration reads ≈ -20 to
-25 dB mean volume; near -91 dB = silent track).

Then reply with `MEDIA:<absolute path to final.mp4>` (inline Telegram video)
plus a short summary: scene list, total duration, size. If >50 MB survives the
re-encode ladder, split or shorten instead of uploading.

## Pitfalls (full list in references/gotchas.md)

- **No slide shows.** The narration drives the recording length (TTS first);
  every scene must be real interaction sized to its audio. A merge that pads
  >3 s of frozen frame means the recording was too short — re-record, don't
  ship. (This is the #1 quality complaint — the "it looks like screenshots"
  failure mode.)
- `--caps=vision,devtools` is required for video tools to exist.
- Scene 1 records from a blank tab through the URL load; the URL-bar card
  (`concat-final --url`) is the literal "entering the URL" moment.
- Video is per-page; multi-tab scenes yield suffixed webms.
- Don't use the Lightpanda `browser` skill for recording — this skill always
  drives its own Chrome.
- 50 MB Telegram bot upload cap → 48 MB budget.
- Kokoro pauses follow punctuation; write narration like a voiceover script.

## Files

- `scripts/launch-mcp.sh` — start Playwright MCP HTTP server (caps=vision,devtools, persistent profile)
- `scripts/mcp-client.py` — single-call / `--script` session MCP client (fallback when tools unregistered); `--save-images DIR`
- `scripts/tts-narration.py` — per-scene Kokoro narration + JSON manifest (run BEFORE recording; durations drive recording length)
- `scripts/merge-scene.py` — webm+mp3(+caption) → normalized mp4 (freeze/silence pad ≤ a few seconds)
- `scripts/concat-final.py` — title card + URL-bar card + concat + 50 MB budget
- `scripts/render-card.py` — PIL title cards / caption bars / browser-URL bar
- `templates/scenario.yaml` — annotated example
- `references/mcp-tools.md` — Playwright MCP tool cheat sheet
- `references/ffmpeg-recipes.md` — exact filter graphs
- `references/gotchas.md` — everything that bites
