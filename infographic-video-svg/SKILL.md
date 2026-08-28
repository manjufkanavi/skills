# Infographic Video Generator — Pure SVG Edition

Generates infographic-style videos entirely from **SVG infographic cards** — no image downloads, no photo compositing. All visuals are programmatically rendered with gradients, charts, and text.

Scenes are narrated via Kokoro TTS and assembled into an MP4 with crossfade transitions.

Ideal for: data, code, abstract concepts, technical explanations, charts, stats, timelines, listicles, comparisons.

---

## Workflow

1. **User provides a topic/prompt**
2. **Agent builds scene JSON** with only SVG scene types
3. **Agent calls the script** to generate the video
4. **Video delivered** via `message` with `media` attachment

**There is no image scene type.** `type: "image"` scenes are **explicitly rejected** by the script with an error message. All scenes must be pure SVG (title, stat, list, chart_bar, comparison, timeline, quote, closing, content). If the topic requires real photography, use the `infographic-video-image` skill instead.

---

## Usage

```bash
python3 skills/infographic-video-svg/scripts/generate_video.py \
  --scenes scenes.json \
  --output video.mp4

# Or pipe JSON via stdin
echo '{...}' | python3 skills/infographic-video-svg/scripts/generate_video.py \
  --output video.mp4
```

Options:
| Flag | Default | Description |
|------|---------|-------------|
| `--scenes` / `-s` | stdin | Path to scene JSON file |
| `--output` / `-o` | `infographic.mp4` | Output video path |
| `--work-dir` / `-w` | auto-cleanup | Keep temp files for debugging |

---

## Scene JSON Format

```json
{
  "title": "Video Title",
  "theme": "ocean",
  "duration_per_scene": 4.0,
  "transition_duration": 0.8,
  "scenes": [ ... ]
}
```

### Top-level Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title` | string | — | Video title |
| `theme` | string | `ocean` | One of 5 color themes |
| `duration_per_scene` | float | 4.0 | Fallback seconds per slide when no narration |
| `transition_duration` | float | 0.8 | Crossfade transition seconds |
| `narration_voice` | string | `af_bella` | Kokoro TTS voice ID |
| `narration_speed` | float | 1.0 | Speech rate multiplier (0.8–1.5) |
| `scenes` | array | — | Array of scene objects |

---

## Color Themes

| Theme | Colors | Mood |
|-------|--------|------|
| `ocean` | Deep blue → teal | Professional, calm, data-focused |
| `sunset` | Purple → crimson → gold | Energetic, passionate, urgent |
| `forest` | Dark green → emerald | Environmental, growth, natural |
| `purple` | Deep violet → magenta | Creative, modern, premium |
| `monochrome` | Slate grays | Minimalist, corporate, clean |

---

## Scene Types

All scenes support an optional `narration` field. When set, Kokoro TTS generates voiceover and scene duration is auto-calculated from audio length. Omit `narration` to use `duration_per_scene`.

### `title` — Opening/title slide

```json
{"type": "title", "title": "Main Headline", "subtitle": "Supporting text", "decorative_icon": "⬡", "narration": "Welcome to this presentation."}
```

### `stat` — Big number statistic

```json
{"type": "stat", "title": "Section Title", "stat": "85%", "stat_label": "of users prefer X", "description": "Context and additional explanation"}
```

Large centered number (monospace), bold label below, smaller description.

### `list` — Numbered list with highlights

```json
{"type": "list", "title": "Key Items", "items": ["First item", "Second item", "Third item"], "highlight_index": 0}
```

Items numbered automatically. `highlight_index` (0-based) picks accent highlight.

### `chart_bar` — Horizontal bar chart

```json
{"type": "chart_bar", "title": "Emissions by Sector", "bars": [
  {"label": "Energy", "value": 73},
  {"label": "Agriculture", "value": 12, "color": "#e74c3c"}
]}
```

Bars scale to max value. Optional `color` per bar overrides theme accent.

### `comparison` — Side-by-side columns

```json
{"type": "comparison", "title": "Then vs Now", "left_title": "2010", "right_title": "2025",
 "left_items": ["Point A", "Point B"], "right_items": ["Point X", "Point Y"]}
```

### `timeline` — Vertical process steps

```json
{"type": "timeline", "title": "Project Phases", "steps": [
  {"title": "Phase 1", "description": "Research and planning"},
  {"title": "Phase 2", "description": "Development and testing"}
]}
```

### `quote` — Pull quote / testimonial

```json
{"type": "quote", "title": "On Innovation", "quote": "The only way to do great work is to love what you do.", "attribution": "Steve Jobs"}
```

### `closing` — End slide

```json
{"type": "closing", "title": "Thank You", "subtitle": "Contact us for more information"}
```

### `content` — Generic text slide (fallback)

```json
{"type": "content", "title": "Section", "subtitle": "Optional", "body": "Full paragraph of text that wraps nicely."}
```

---

## Tips for the Agent

- **Keep scenes to 4–10** for a watchable video (under 40s)
- **Vary scene types** — mix charts, lists, timelines for visual variety
- **Write compelling stat values** — bold numbers that grab attention
- **Bar chart values** should be 0–100 scale (they auto-scale to max value)
- **Comparison items** should be short (under 60 chars) — they don't wrap
- Choose `sunset` or `purple` for urgency, `ocean` for data/reports, `forest` for environment
- This is **pure SVG** — no image URLs needed. Every scene is programmatically rendered.

---

## Dependencies

- `cairosvg` (SVG → PNG)
- `ffmpeg` (video encoding)
- `kokoro-onnx` (TTS narration via Kokoro)
- `soundfile` (WAV audio output)
- `numpy` (audio buffer math)
- Python 3 stdlib

### Narration Tips

- Keep narration under 100 chars per scene for short punchy videos
- For stats-heavy scenes, narrate key number + context
- **Voice naming**: `xy_name` where `x` = language (a=US, b=UK) and `y` = gender (f=female, m=male)
- **Recommended voices**: `af_bella` (clearest US, default), `af_sarah` (natural), `af_sky` (calm), `am_michael` (deep male), `am_adam` (warm male)
- British voices: `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`, `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`
- Set `narration_speed: 1.2` for faster pacing, `0.9` for dramatic slow delivery
- Scenes without `narration` fall back to `duration_per_scene` with silent audio

---

## Delivery

After generating, send the video to the user:

```python
message(content="Here's the infographic video",
        channel="telegram",
        chat_id="...",
        media=["path/to/video.mp4"])
```
