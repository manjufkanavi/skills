# Infographic Video Generator — AI Image Edition

Generates infographic-style videos entirely from **AI-generated images** (Flux2-klein-9B via mflux, MLX native) composited with text overlays — no SVG, no web downloads. Every scene generates a unique AI image matching the context explanation.

Supports **landscape 16:9** (default) and **vertical 9:16** (`--vertical`) for Instagram Reels / YouTube Shorts / TikTok.

---

## Agent Workflow

### 1. Plan scenes
Plan 5–12 scenes. Every scene is an AI-generated image with text on top. There are NO SVG types and no web downloads.

### 2. Derive image prompts (via Cinematic Prompt Engineer)
Before image generation, the script calls the **local LLM** (Qwen3.6-35B-A3B through omlx) acting as an **expert cinematographer and prompt engineer**. It analyses every scene's narrative context and crafts a detailed, cinematic prompt with lighting, mood, composition, colour palette, and atmosphere — ensuring visual consistency across scenes.

These LLM-crafted prompts are automatically written to each scene's `gen_prompt` field. You can still override with an explicit `gen_prompt` in the JSON.

### 3. Build scene JSON
Each scene is `type: "image"`:

```json
{
  "type": "image",
  "title": "Scene Headline",
  "subtitle": "Optional sub-headline",
  "body": "Optional body paragraph (shows in bottom panel)",
  "narration": "TTS voiceover text for this scene.",
  "gen_prompt": "Optional: override the auto-derived Flux prompt"
}
```

### 4. Call the script
Pass the scene JSON to generate_video.py, then deliver the MP4.

---

## Usage

```bash
# Landscape (16:9) — default
python3 skills/infographic-video-image/scripts/generate_video.py \
  --scenes scenes.json --output video.mp4

# Vertical (9:16) — Instagram/Reels
python3 skills/infographic-video-image/scripts/generate_video.py \
  --vertical --scenes scenes.json --output reel.mp4

# Pipe JSON via stdin
echo '{...}' | python3 skills/infographic-video-image/scripts/generate_video.py \
  --vertical --output reel.mp4
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--scenes` / `-s` | stdin | Path to scene JSON file |
| `--output` / `-o` | `infographic.mp4` | Output video path |
| `--work-dir` / `-w` | auto-cleanup | Keep temp files for debugging |
| `--vertical` / `-v` | off | Render vertical 9:16 (1080×1920) |

---

## Scene JSON Format

```json
{
  "title": "Video Title",
  "theme": "ocean",
  "duration_per_scene": 4.0,
  "transition_duration": 0.8,
  "narration_voice": "bf_isabella",
  "narration_speed": 1.0,
  "scenes": [
    {
      "type": "image",
      "title": "Headline",
      "subtitle": "Supporting text",
      "body": "Optional body paragraph at bottom",
      "narration": "Voiceover text for TTS.",
      "gen_prompt": "Optional: custom flux prompt for this scene"
    }
  ]
}
```

### Top-level Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title` | string | — | Video title |
| `theme` | string | `ocean` | One of 5 color themes for accent overlays |
| `duration_per_scene` | float | 4.0 | Fallback when no narration |
| `transition_duration` | float | 0.8 | Crossfade transition seconds |
| `narration_voice` | string | `bf_isabella` | Kokoro TTS voice ID |
| `narration_speed` | float | 1.0 | Speech rate multiplier (0.8–1.5) |
| `scenes` | array | — | Array of `type: "image"` scene objects |

### Scene Type: `image`

This is the **only** scene type. Each scene generates a unique AI image via Flux2-klein-9B and composites text on top.

| Field | Required | Description |
|-------|----------|-------------|
| `type` | ✅ | Must be `"image"` |
| `title` | ❌ | Scene headline — composited as centered pill badge near top |
| `subtitle` | ❌ | Sub-headline below title |
| `body` | ❌ | Body text — composited in a bottom overlay panel |
| `narration` | ❌ | TTS voiceover text; auto-calculates scene duration |
| `gen_prompt` | ❌ | Override the auto-derived Flux2 image generation prompt |

**Auto-prompt derivation**: If `gen_prompt` is omitted, the script sends all scene contexts to the local LLM (acting as expert cinematographer/prompt engineer) which returns detailed cinematic prompts for every scene. Falls back to concatenating title → subtitle → body → narration if the LLM is unreachable.

**Resolution**: Images are generated at the full active resolution (1920×1080 or 1080×1920 vertical). No crop needed. A semi-transparent gradient overlay ensures text readability.

---

## Color Themes

| Theme | Accent | Mood |
|-------|--------|------|
| `ocean` | Blue #2980b9 | Professional, calm |
| `sunset` | Crimson #e74c3c | Energetic, passionate |
| `forest` | Green #27ae60 | Environmental, growth |
| `purple` | Violet #7c3aed | Creative, premium |
| `monochrome` | Slate #64748b | Minimalist, corporate |

Themes control the accent line color and text color palette in the composited overlay. The AI-generated image provides the visual background.

---

## Tips for the Agent

### Writing Narration
- Keep narration under 100 chars per scene for punchy pacing
- **Recommended voice**: `bf_isabella` (British RP, preferred), `af_bella` (clear US)
- Set `narration_speed: 1.2` for faster pacing, `0.9` for dramatic delivery

### Scene Planning
- Keep 5–12 scenes for a watchable video (30–60s)
- Vary the context — each scene gets its own unique generated image
- First scene sets the tone (grand establishing image), last scene is a closing image
- If narration is long, scene auto-extends to fit the voiceover

### Image Prompts & Cinematic Prompt Engineer
- Before image generation, the script calls **omlx** (Qwen3.6-35B-A3B on port 1234) with a **cinematographer/prompt engineer** system prompt
- The LLM receives **all scenes at once** with their full narrative context and returns a batch of detailed, visually-consistent cinematic prompts
- Each prompt includes: subject, setting, composition, lighting, mood, colour palette, cinematic terminology
- Prompts are auto-injected into each scene's `gen_prompt` field
- **Fallback**: if omlx isn't running, uses simple concatenation of title → subtitle → body → narration
- For specific visual control, explicitly set `gen_prompt` in the scene JSON — it takes priority over the LLM output
- Flux2-klein-9B works best with descriptive natural language prompts
- The model generates at full resolution (no cropping needed)

---

## Dependencies

- `ffmpeg` (video encoding)
- `kokoro-onnx` (TTS narration)
- `soundfile` (WAV audio output)
- `numpy` (audio buffer math)
- `Pillow` / `PIL` (image compositing)
- `mflux` with `flux2-klein-9b-4bit` model (AI image generation)
- **omlx** with `Qwen3.6-35B-A3B-UD-MLX-4bit` (LLM for cinematic prompt engineering)
- Python 3 stdlib

---

## Delivery

After generating, send the video to the user:

```python
message(content="Here's the video",
        channel="telegram",
        chat_id="...",
        media=["path/to/video.mp4"])
```
