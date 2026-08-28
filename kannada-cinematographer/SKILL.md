---
name: kannada-cinematographer
description: Agy-powered cinematographic scene creator — takes Kannada text and visualizes it as a short film scene-by-scene, generating detailed image generation prompts.
tags: [kannada, cinematography, scene-generation, image-prompts, agy, visualisation]
---

# Kannada Cinematographer — Scene Visualiser & Prompt Generator

## Overview

Takes any Kannada text (poem, story, narrative, vachana, tatvapada) and treats it like a film script. A **cinematography expert** (agy agent) breaks the text into visual scenes — complete with camera angles, lighting, mood, composition, and color palette — then produces ready-to-use **image generation prompts** for each scene.

### Pipeline

1. **Input** → Kannada text or a reference to one (e.g., "ಶಿಶುನಾಳ ಶರೀಫರ ತಂಬೂರಿ ತತ್ವಪದ")
2. **Role Assignment** → agy becomes "ಪ್ರಖ್ಯಾತ ಸಿನಿಮಾಟೋಗ್ರಾಫರ್" (Renowned Cinematographer)
3. **Scene Analysis** → agy reads the text, identifies scene boundaries, emotional arcs, visual motifs
4. **Cinematographic Breakdown** → Each scene gets camera angle, lens, lighting, color palette, composition, mood
5. **Prompt Generation** → Each scene is converted into a detailed English prompt suitable for Flux, Midjourney, SDXL, DALL-E 3, etc.
6. **Saved** → All scenes written to `prompts/<topic_slug>/prompts.md`

## Quick Start

```bash
# Kannada text as argument
python3 skills/kannada-cinematographer/main.py --text "ಎಲ್ಲಿರುವೆ ಮನುಜ, ನಿನ್ನ ಗುರಿಯೇನು? ಹುಟ್ಟು ಸಾವಿನ ನಡುವೆ ನೀನೇನು ಮಾಡುವೆ?"

# From a file
python3 skills/kannada-cinematographer/main.py --file path/to/poem.txt

# Named source (agy searches/retrieves context)
python3 skills/kannada-cinematographer/main.py --source "ಶಿಶುನಾಳ ಶರೀಫರ ತಂಬೂರಿ ತತ್ವಪದ"
```

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--text` | Direct Kannada text input | — |
| `--file` | Path to a .txt/.md file with Kannada text | — |
| `--source` | Named source (agy finds content if possible) | — |
| `--style` | Visual style: cinematic, theatrical, watercolor, anime, realistic, painterly | cinematic |
| `--aspect` | Aspect ratio for prompts: "16:9", "9:16", "1:1", "4:3" | "16:9" |
| `--model` | agy model to use | "gemini-3.1-pro-high" |
| `--effort` | agy reasoning effort (low, medium, high) | high |
| `--output` | Output directory | `prompts/` |
| `--force` | Re-generate if prompts.md exists | False |

## Output Structure

```
prompts/<topic_slug>/
  prompts.md          — All scenes with cinematographic breakdown + image prompts
  source.txt          — Original Kannada text that was analysed (for reference)
```

### prompts.md Format

Each scene contains:

```
## Scene 1: <Scene Title>

### Kannada Source
> The original Kannada verse/segment this scene is based on

### Visual Description
What the scene shows — narrative context

### Cinematography
- **Camera**: Wide shot / Close-up / Dutch angle / etc.
- **Lens**: 35mm / 50mm / 85mm / Wide-angle / Telephoto
- **Lighting**: Golden hour / Low-key / Soft diffused / etc.
- **Color Palette**: Dominant colors with hex codes
- **Composition**: Rule of thirds / Symmetrical / Leading lines / etc.
- **Mood**: Emotional tone of the scene

### Image Prompt
> Ready-to-use English prompt for image generation models.
> Structured: subject, setting, lighting, colors, composition, style, camera details.
```

## Default Role

> ನಿಮ್ಮ ಪಾತ್ರ: ಪ್ರಖ್ಯಾತ ಚಲನಚಿತ್ರ ಸಿನಿಮಾಟೋಗ್ರಾಫರ್ ಮತ್ತು ದೃಶ್ಯ ನಿರ್ದೇಶಕ. ನೀವು ಕನ್ನಡ ಸಾಹಿತ್ಯ ಮತ್ತು ಸಂಸ್ಕೃತಿಯನ್ನು ಆಳವಾಗಿ ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೀರಿ. ಕನ್ನಡ ಪದ್ಯ/ಕಥೆ/ವಚನಗಳನ್ನು ಓದಿ, ಅವುಗಳ ಭಾವ ಮತ್ತು ಸಂದೇಶವನ್ನು ದೃಶ್ಯಗಳಾಗಿ ಪರಿವರ್ತಿಸುವಲ್ಲಿ ನಿಪುಣರು. ಪ್ರತಿ ದೃಶ್ಯಕ್ಕೂ ಸೂಕ್ತ ಕ್ಯಾಮೆರಾ ಕೋನ, ಬೆಳಕು, ಬಣ್ಣ ಸಂಯೋಜನೆ ಮತ್ತು ಸಂಯೋಜನೆ ನಿರ್ಧರಿಸುತ್ತೀರಿ.

(You are a renowned film cinematographer and visual director with deep understanding of Kannada literature and culture. You excel at reading Kannada poetry/stories/vachanas and converting their emotions and messages into visual scenes. For each scene, you determine the right camera angle, lighting, color palette, and composition.)

## agy Usage Rules

See `kannada-poet-agy/SKILL.md` for agy CLI conventions.

1. Never use `-p` with shell inline single quotes for long prompts — use stdin piping via Python subprocess.
2. agy output is used directly — the prompt extraction logic handles JSON from agy output.
3. Timeouts — agy can take 60-240 seconds for detailed scene breakdowns. Default timeout is 300s.

## Prerequisites

- `agy` CLI installed and authenticated (`agy agents`)
- Workspace path: `~/.nanobot/workspace`

## File Location

**Working copy:** `~/.nanobot/workspace/skills/kannada-cinematographer/main.py`
