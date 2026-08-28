# Infographic Video Generator

Generates infographic-style videos from structured scene descriptions. Supports two visual modes:

1. **SVG infographic cards** — programmatically rendered with gradients, charts, and text (ideal for data, code, abstract topics)
2. **Real-image scenes** — downloads web photos, composites text overlays (ideal for nuanced general topics)

Scenes are narrated via Kokoro TTS and assembled into an MP4 with crossfade transitions.

---

## Workflow

1. **User provides a topic/prompt**
2. **Agent analyses topic** and decides visual mode per scene
3. **For image scenes**: agent web-searches relevant images and collects their URLs
4. **Agent builds scene JSON** with mixed SVG and image scene types
5. **Agent calls the script** to generate the video
6. **Video delivered** via `message` with `media` attachment

### Visual mode decision logic

- **SVG mode** (default) — for programming, data, abstract concepts, technical explanations, charts, stats, timelines
- **Image mode** (`type: "image"`) — for nuanced general-interest topics like history, culture, travel, nature, biographies, science concepts
- **Mix freely** — SVG and image scenes can coexist in the same video

---

## Usage

```bash
python3 skills/infographic-video/scripts/generate_video.py \
  --scenes scenes.json \
  --output video.mp4

# Or pipe JSON via stdin
echo '{...}' | python3 skills/infographic-video/scripts/generate_video.py \
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

## SVG Scene Types

All SVG scenes support an optional `narration` field. When set, Kokoro TTS generates voiceover and scene duration is auto-calculated from audio length. Omit `narration` to use `duration_per_scene`.

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

## Image Scene Type

Use for nuanced general topics. Downloads a real photo from the web, composites text onto it as a full-frame scene.

```json
{
  "type": "image",
  "title": "The Great Pyramid",
  "subtitle": "Built circa 2560 BCE",
  "body": "The Great Pyramid of Giza stood as the tallest human-made structure for over 3,800 years.",
  "images": [
    {"url": "https://upload.wikimedia.org/wikipedia/commons/6/6c/Great_Pyramid_of_Giza.jpg", "caption": "Pyramid of Khufu"}
  ],
  "narration": "The Great Pyramid of Giza, built around 2560 BCE, remained the tallest man-made structure for nearly four millennia."
}
```

### Image scene fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Must be `"image"` |
| `title` | string | Headline composited at top (pill background) |
| `subtitle` | string | Optional sub-headline below title |
| `body` | string | Optional body text at bottom of frame |
| `images` | array | `[{"url": "...", "caption": "..."}]` — first image is the background |
| `image_urls` | array | Flat list of URL strings (alternative to `images`) |
| `narration` | string | TTS voiceover (same as other scene types) |

**Fallback:** If download fails or no URLs given, renders as SVG content card automatically.

### Combining SVG and image scenes

SVG and image scenes can be freely mixed in any order:

```json
{
  "title": "The Hubble Telescope",
  "theme": "ocean",
  "scenes": [
    {"type": "title", "title": "Hubble Space Telescope", "subtitle": "30 Years of Discovery"},
    {"type": "image", "title": "The Pillars of Creation", "images": [{"url": "https://upload.wikimedia.org/wikipedia/commons/6/68/Pillars_of_creation_2014_HST_WFC3-UVIS_full-res_denoised.jpg"}], "narration": "The Pillars of Creation show towering columns of gas and dust where new stars are born."},
    {"type": "stat", "title": "By the Numbers", "stat": "13.4B", "stat_label": "light-years — Hubble's farthest reach"},
    {"type": "image", "title": "The Deep Field", "images": [{"url": "https://upload.wikimedia.org/wikipedia/commons/5/5f/Hubble_Ultra_Deep_Field_2014.jpg"}], "narration": "The Ultra Deep Field revealed thousands of galaxies in what seemed like empty sky."},
    {"type": "closing", "title": "Thank you, Hubble!"}
  ]
}
```

---

## Delivery

After generating, send the video to the user:

```python
message(content="Here's the infographic video", 
        channel="telegram", 
        chat_id="...",
        media=["path/to/video.mp4"])
```

---

## Image Sourcing Best Practices (for the agent)

1. **Web-search** for high-resolution relevant images before building the JSON
2. Use direct image URLs from Wikimedia Commons, Unsplash, NASA, or similar sources
3. Prefer JPEG at least 1920×1080 resolution
4. Provide fallback URLs in `image_urls` if unsure about availability
5. The script auto-falls back to SVG if downloads fail — no crash

---

## Tips for the Agent

- **Keep scenes to 4–10** for a watchable video (under 40s)
- **Vary scene types** — mix SVG charts, lists, and image scenes for visual variety
- **Write compelling stat values** — bold numbers that grab attention
- **Bar chart values** should be 0–100 scale (they auto-scale to max value)
- **Comparison items** should be short (under 60 chars) — they don't wrap
- Choose `sunset` or `purple` for urgency, `ocean` for data/reports, `forest` for environment
- For image scenes, keep title short (3–6 words) so it fits the pill overlay cleanly

---

## Dependencies

- `cairosvg` (SVG → PNG)
- `ffmpeg` (video encoding)
- `kokoro-onnx` (TTS narration via Kokoro)
- `soundfile` (WAV audio output)
- `numpy` (audio buffer math)
- `Pillow` (image compositing)
- `requests` (image downloads)
- Python 3 stdlib

### Narration Tips

- Keep narration under 100 chars per scene for short punchy videos
- For stats-heavy scenes, narrate key number + context
- **Voice naming**: `xy_name` where `x` = language (a=US, b=UK) and `y` = gender (f=female, m=male)
- **Recommended voices**: `af_bella` (clearest US, default), `af_sarah` (natural), `af_sky` (calm), `am_michael` (deep male), `am_adam` (warm male)
- British voices: `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`, `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`
- Set `narration_speed: 1.2` for faster pacing, `0.9` for dramatic slow delivery
- Scenes without `narration` fall back to `duration_per_scene` with silent audio
