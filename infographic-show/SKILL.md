---
name: infographic-show
description: Generate a narrated MP4 infographic video from SVG scene cards using an in-model closed loop (theloop) — plan, write SVG, render to PNG, judge, refine — then narrate with Kokoro TTS, stitch with ffmpeg xfade, and send to Telegram.
category: video/design
---

# infographic-show

Build a **narrated infographic video** (MP4) entirely from **in-model SVG scene cards**. No external image model: each scene is generated and refined by an in-model closed loop (theloop), rasterized to a PNG, narrated with Kokoro TTS, and stitched with ffmpeg xfade transitions.

## Pipeline

1. **Pick a topic + audience.** Plan 3–10 scenes (each: `title`, `subtitle`, spoken `narration`, and a self-contained SVG visual).
2. **Run the in-model closed loop per scene** (theloop / closed-loop-artifact pattern):
   - *plan* the visual → *write* a self-contained `<svg>` at **1920×1080** → *render* to PNG (cairosvg) → *judge* (ascii_view or visually against the spec) → *refine* (≤3 iterations). This is the "theloop-based image generation" that replaces any external image model.
3. **Collect the final SVGs** into `scenes.json` (see schema below).
4. **Generate the video**: run `generate_video.py` (renders each SVG → 1920×1080 PNG, narrates with Kokoro, stitches with ffmpeg xfade → MP4).
5. **Send the MP4** to Telegram.

## Requirements

- Skill venv `~/.venvs/infographic-show` (has `cairosvg`, `kokoro_onnx`, `soundfile`, `numpy`). The venv is **pip-less** (uv-managed, PEP 668) - install packages with `uv pip install --python ~/.venvs/infographic-show/bin/python <pkg>` (the `--venv` flag is invalid).
- `ffmpeg` (xfade filter).
- Kokoro model + voices at `~/.hermes/skills/voice-bridge/assets/` (`kokoro/model.onnx`, `voices-v1.0.bin`).
- macOS: `libcairo` is located automatically via `DYLD_LIBRARY_PATH=/opt/homebrew/lib` (baked into the script).

## Support files

- `references/macos-libcairo.md` - fixing the "no library called cairo-2" crash (set `DYLD_LIBRARY_PATH=/opt/homebrew/lib`).
- `references/kokoto-tts.md` - the `k.voices.get()` numpy-array `is None` fix and the TTS asset layout.
- `references/environment-setup.md` - installing packages into the pip-less venv (`uv pip install --python ...`), rendering via the cairosvg CLI (not `svg2png()`), and the absolute-path requirement for background-process invocations.
- `templates/scenes_plan.json` - starter hand-crafted narration plan for the `--script` mode (copy, fill in, run).

## Usage

```bash
~/.venvs/infographic-show/bin/python scripts/generate_video.py --scenes scenes.json --output show.mp4
```

Then send the result to Telegram (current chat or a target):

```
send_message(target="telegram:<chat_id>", media=["show.mp4"])
```

## Research-first workflow (new)

To make the skill work **for any topic**, `scripts/research_to_video.py` chains the
`deep-research` skill in front of `generate_video.py`:

```bash
# Automated: research the topic, then build + render the video.
~/.venvs/infographic-show/bin/python scripts/research_to_video.py "how to become a better person" --output show.mp4

# Crafted narration for higher quality (research still drives the scenes):
~/.venvs/infographic-show/bin/python scripts/research_to_video.py "how to become a better person" \
    --script templates/scenes_plan.json --output show.mp4
```

What it does, end to end:

1. **Research** — runs the deep-research skill's `deep_research.py` (query → scrape → structured `themes`/`all_items`), writing `research_data.json` into the work dir.
2. **Build scenes** — one scene per research theme, where each scene's **spoken narration is derived from the research** (the research summary *is* the script). In crafted mode, `--script scenes_plan.json` supplies the narration; the visual cards are still generated here.
3. **Render** — calls `generate_video.py` (SVG → PNG → Kokoro narration → ffmpeg xfade → MP4).

Files:

- `scripts/research_to_video.py` — orchestrator (run deep-research → build scenes.json → call generate_video.py).
- `templates/scenes_plan.json` — starter hand-crafted narration plan (copy, fill in, then pass via `--script`).

### Crafted mode (recommended for quality)

The automated research-to-narration pipeline produces mediocre narration (it grabs the first two sentences from research items). For **high-quality narration**, use crafted mode:

1. Copy `templates/scenes_plan.json` to a working file.
2. Write compelling narration for each scene — write as if speaking to someone, 40-80 words per scene.
3. Plan 3-10 scenes covering the topic's key themes.
4. Run: `research_to_video.py "topic" --script /path/to/your_plan.json --output show.mp4`

The `build_card` function in `research_to_video.py` generates SVG scene cards from the plan's title, subtitle, bullets, and accent — no hand-written SVG needed.

## scene.json schema

```json
{
  "title": "demo title",
  "theme": "purple",
  "duration_per_scene": 4.5,
  "transition_duration": 0.9,
  "narration_voice": "af_bella",
  "narration_speed": 1.0,
  "scenes": [
    {
      "type": "svg",
      "title": "scene title",
      "svg": "<svg xmlns=... viewBox=\"0 0 1920 1080\" ...>...</svg>",
      "narration": "spoken text (Kokoro TTS)"
    }
  ]
}
```

- Each scene **must** be `type: "svg"` with a self-contained `<svg>` markup (viewBox 1920×1080, or the script scales/pads to 1920×1080).
- `narration` is optional: if omitted, the scene holds for `duration_per_scene` (silent).
- `duration` per scene overrides `duration_per_scene`.

## Notes

- If Kokoro is unavailable, narration is skipped and the video is silent (scenes still hold for their duration).
- The SVGs are meant to be *generated by the in-model loop*, not hand-written — use the loop to iterate on the visual until it passes the judge step.

## Kokoro TTS Calibration

Kokoro's `speed` parameter works but produces unnatural speech rates:
- `speed=1.0` → ~2.3× normal speech (too slow)
- `speed=0.5` → ~1.15× normal speech (still slow)
- `speed=0.4` → ~0.92× normal speech (near-natural)

The `generate_video.py` script automatically calibrates to `speed=min(user_speed, 0.4)` and then time-stretches/trimms narration to match scene target duration. This ensures consistent pacing regardless of Kokoro's speed calibration.

**Known bug fix**: The `_time_stretch` function uses `pyrubberband` for pitch-preserving time-stretching. The rate parameter is inverted (`rate=1.5` means 1.5× longer, not 1.5× faster) because pyrubberband uses playback rate semantics.
