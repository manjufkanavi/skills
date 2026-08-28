#!/usr/bin/env python3
"""
Infographic Video Generator — AI Image Edition
───────────────────────────────────────────────
Takes structured scene descriptions → generates images via Flux2-klein-9B
(mflux, MLX native) → composites text overlays → TTS narration via Kokoro
→ crossfade MP4 video.

All scenes are image-based (no SVG, no web downloads).
Every scene generates a matching AI image from its context description.

Supports:
  - Landscape (16:9) by default
  - Vertical (9:16) with `--vertical` flag for Instagram/Reels/Shorts

Usage:
  # Landscape 1920×1080
  python3 generate_video.py --scenes scenes.json --output video.mp4

  # Vertical 1080×1920 (Instagram/Reels)
  python3 generate_video.py --vertical --scenes scenes.json --output reel.mp4

  # Pipe JSON via stdin
  echo '{"title":"...","scenes":[...]}' | python3 generate_video.py -o video.mp4

Input format (stdin or file):
{
  "title": "Video Title",
  "theme": "ocean|sunset|forest|purple|monochrome",
  "duration_per_scene": 4.0,
  "transition_duration": 0.8,
  "narration_voice": "bf_isabella",
  "narration_speed": 1.0,
  "scenes": [
    {
      "type": "image",
      "title": "Scene Headline",
      "subtitle": "Optional subhead",
      "body": "Optional body paragraph",
      "narration": "TTS voiceover text.",
      "gen_prompt": "Optional override: image prompt for mflux generation"
    }
  ]
}

Scene type: "image" only. Every scene renders a Flux2-klein-9B generated
image with text compositing. If gen_prompt is missing, the prompt is
derived from scene title/subtitle/body.

Dependencies: ffmpeg, kokoro-onnx, soundfile, numpy, Pillow, mflux, python3
"""
import json, os, sys, subprocess, tempfile, shutil, argparse, time, datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RESOLUTION & SCALE HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REF_W, REF_H = 1920, 1080  # Reference design resolution (landscape)
W, H = REF_W, REF_H        # Active resolution — set dynamically


def sx(x):
    """Scale horizontal coordinate from REF_W-based to current W."""
    return int(x * W / REF_W)


def sy(y):
    """Scale vertical coordinate from REF_H-based to current H."""
    return int(y * H / REF_H)


def sr(r):
    """Scale radius/dimension proportionally."""
    return int(r * min(W, H) / min(REF_W, REF_H))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CINEMATIC PROMPT ENGINEER — LLM-powered prompt generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Local LLM (omlx) endpoint — serves Qwen3.6-35B-A3B-UD-MLX-4bit via
# OpenAI-compatible API on port 1234.
LLM_BASE = "http://127.0.0.1:1234"
LLM_TIMEOUT = 180  # seconds per batch


def _llm_complete(messages, temperature=0.7, max_tokens=4096):
    """Call the local omlx LLM with OpenAI-compatible chat completions."""
    import urllib.request, json
    body = json.dumps({
        "model": "current",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        f"{LLM_BASE}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  \u26a0 LLM call failed: {e}")
        return None


CINEMATOGRAPHER_SYSTEM_PROMPT = """\
You are an expert cinematographer and prompt engineer for text-to-image AI.\

For each scene, output a detailed visual prompt describing what is visible \
in the frame: subject, setting, lighting, mood, colours, composition. Use \
cinematic terminology (golden hour, shallow depth of field, dramatic shadows).\

RULES:\
- Return ONLY a valid JSON array of strings — no markdown, no commentary.\
- One prompt string per scene, in order.\
- Each prompt under 80 words.\
- Keep visual style consistent across scenes.\
\
EXAMPLE for 2 scenes:\
[\"Cinematic portrait of a 19th century Indian saint with white beard and \
robes, standing in a rustic temple doorway, golden hour sunlight, spiritual \
atmosphere, warm earth tones, shallow depth of field\", \"Peaceful rural \
Karnataka village at sunrise, mud houses with tiled roofs, banyan tree, \
soft morning mist, green fields, cinematic wide shot, warm light\"]\
\
Output exactly the same count as the number of scenes given.\
"""


def generate_cinematic_prompts(scenes, title):
    """Use the local LLM (acting as expert cinematographer/prompt engineer)
    to craft a detailed, context-aware image prompt for every scene.

    Each scene's gen_prompt field is overwritten with the LLM-crafted prompt.
    Falls back to _derive_prompt() if the LLM is unreachable or returns
    invalid output.
    """
    scene_count = len(scenes)
    if scene_count == 0:
        return

    # Build the user message — list each scene with its context
    lines = [f"VIDEO TOPIC: {title}", f"SCENE COUNT: {scene_count}",
             f"Return ONLY a valid JSON array of {scene_count} prompt strings.",
             ""]
    for i, sc in enumerate(scenes):
        lines.append(f"Scene {i+1}:")
        for k in ("title", "subtitle", "body", "narration"):
            v = sc.get(k, "") or ""
            if v:
                lines.append(f"  {k}: {v}")
        lines.append("")
    user_text = "\n".join(lines)

    messages = [
        {"role": "system", "content": CINEMATOGRAPHER_SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    print(f"  Calling cinematographer LLM for {scene_count} scene prompts...")
    raw = _llm_complete(messages, temperature=0.3, max_tokens=4096)
    if raw is None:
        print("  \u26a0 LLM unreachable — using fallback prompt derivation")
        return

    # Debug: log raw response length and sample
    print(f"  LLM response: {len(raw)} chars")
    if len(raw) < 100 or raw.count('"') < 4:
        print(f"  RAW (first 400): {raw[:400]}")

    # Parse JSON array from response
    prompts = _parse_prompt_response(raw, scene_count)
    if prompts is None or len(prompts) != scene_count:
        actual = len(prompts) if prompts else 0
        print(f"  \u26a0 LLM returned invalid prompts ({actual}/{scene_count}) — using fallback")
        print(f"  RAW (first 500): {raw[:500]}")
        return

    for i, sc in enumerate(scenes):
        sc["gen_prompt"] = prompts[i]
        print(f"    \u2713 [{i+1}/{scene_count}] prompt crafted ({len(prompts[i])} chars)")

    print(f"  All {scene_count} cinematic prompts ready.")


def _parse_prompt_response(raw, expected_count):
    """Extract a JSON list of prompt strings from the LLM response.
    Handles markdown fences, trailing commas, extra text, and verbose
    responses that mix analysis with the JSON output.

    Strategy search order:
      1. Look for a ```json ... ``` code block (prefer last block)
      2. Look for a ``` ... ``` code block (prefer last block)
      3. Find outermost [...] brackets
      4. Try to parse the entire response as JSON
    """
    import json, re
    text = raw.strip()

    # ── Search 1: ```json ... ``` block ──
    candidates = list(re.finditer(
        r"```(?:json|JSON)\s*\n?(.*?)```", text, re.DOTALL
    ))
    if candidates:
        for match in reversed(candidates):
            inner = match.group(1).strip()
            parsed = _try_parse_json_array(inner, expected_count)
            if parsed is not None:
                return parsed

    # ── Search 2: ``` ... ``` (unlabelled) ──
    candidates = list(re.finditer(r"```\s*\n?(.*?)```", text, re.DOTALL))
    if candidates:
        for match in reversed(candidates):
            inner = match.group(1).strip()
            parsed = _try_parse_json_array(inner, expected_count)
            if parsed is not None:
                return parsed

    # ── Search 3: outermost [...] brackets ──
    start_bracket = text.find("[")
    end_bracket = text.rfind("]")
    if start_bracket != -1 and end_bracket > start_bracket:
        json_str = text[start_bracket : end_bracket + 1]
        parsed = _try_parse_json_array(json_str, expected_count)
        if parsed is not None:
            return parsed

    # ── Search 4: entire response as JSON ──
    parsed = _try_parse_json_array(text, expected_count)
    if parsed is not None:
        return parsed

    return None


def _try_parse_json_array(text, expected_count):
    """Try to parse *text* as a JSON array of strings.  Handles trailing
    commas gracefully.  Returns the list on success, None on failure."""
    import json, re
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and all(isinstance(p, str) for p in parsed):
            return parsed[:expected_count]
    except json.JSONDecodeError:
        pass
    # Strip trailing commas before ] or }
    cleaned = re.sub(r",\s*([\]}])", r"\1", text)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and all(isinstance(p, str) for p in parsed):
            return parsed[:expected_count]
    except json.JSONDecodeError:
        pass
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MFLUX — delegate to comfyui skill's generate_image.py (per-scene)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COMFYUI_GENERATE_IMAGE = os.path.expanduser(
    "~/.nanobot/workspace/skills/comfyui/scripts/generate_image.py"
)


def _ensure_mflux_vram():
    """Free GPU memory for mflux by stopping omlx (MLX LLM) if running."""
    import subprocess
    try:
        result = subprocess.run(
            ["brew", "services", "list"],
            capture_output=True, text=True, timeout=10,
        )
        if "omlx" in result.stdout and "started" in result.stdout:
            print("  Stopping omlx to free GPU memory for mflux...")
            subprocess.run(
                ["brew", "services", "stop", "omlx"],
                capture_output=True, timeout=30,
            )
            time.sleep(2)
    except Exception:
        pass


def generate_mflux_images(scenes, tmp_dir, width, height):
    """Generate images by delegating to comfyui skill's generate_image.py.

    Calls generate_image.py as a subprocess per scene.
    Uses gen_prompt from scene JSON or derives visual prompt via _derive_prompt.
    Returns list of image paths.
    """
    if not os.path.isfile(COMFYUI_GENERATE_IMAGE):
        raise RuntimeError(
            f"generate_image.py not found at: {COMFYUI_GENERATE_IMAGE}"
        )

    paths = []
    for i, scene in enumerate(scenes):
        prompt = scene.get("gen_prompt") or _derive_prompt(scene)
        seed = int(time.time() + i) % (2**32)
        dest = tmp_dir / f"gen_img_{i:03d}.png"

        print(f"    [{i+1}/{len(scenes)}] Generating image: {prompt[:60]}...")

        out_dir = tmp_dir / f"_mflux_{i:03d}"
        out_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable or "python3",
            COMFYUI_GENERATE_IMAGE,
            "--prompt", prompt,
            "--seed", str(seed),
            "--steps", "4",
            "--width", str(width),
            "--height", str(height),
            "--guidance", "2.5",
            "--output-dir", str(out_dir),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(f"      ✗ mflux failed: {result.stderr.strip()[-200:]}")
            _generate_fallback_image(dest, width, height, i)
        else:
            pngs = sorted(Path(out_dir).rglob('*.png'))
            if pngs:
                shutil.copy2(str(pngs[0]), str(dest))
                print(f"      ✓ Generated ({os.path.getsize(dest) / 1024:.0f} KB)")
            else:
                print(f"      ✗ No PNG output from mflux, using fallback")
                _generate_fallback_image(dest, width, height, i)

        paths.append(dest)
    return paths


def _generate_fallback_image(dest, width, height, idx):
    """Generate a gradient fallback image when mflux fails."""
    colors = [
        (41, 128, 185), (231, 76, 60), (39, 174, 96),
        (124, 58, 237), (100, 71, 139), (230, 126, 34),
        (22, 160, 133), (192, 57, 43), (44, 62, 80),
    ]
    c = colors[idx % len(colors)]
    img = Image.new('RGB', (width, height), c)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        alpha = int(30 + (y / height) * 60)
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
    img.save(dest, quality=85)
    print(f"      ⚠ Fallback image generated ({os.path.getsize(dest) / 1024:.0f} KB)")


def _derive_prompt(scene):
    """Derive a visual image generation prompt from scene content.

    Uses the scene's title and body text directly to describe what the
    image should show — avoids fragile keyword matching that maps scenes
    to hardcoded visual templates. Flux2-klein-9B handles descriptive
    scene content naturally and generates context-appropriate visuals.
    """
    title = scene.get("title", "") or ""
    subtitle = scene.get("subtitle", "") or ""
    body = scene.get("body", "") or ""
    narration = scene.get("narration", "") or ""

    subject = title or subtitle or ""

    # Use the body as the primary visual description — it already describes
    # what the scene is about in natural language. Flux interprets this
    # directly instead of us guessing a visual category via keywords.
    visual_focus = body.strip() if body else narration.strip()

    # Style suffix for visual quality and consistency
    style_suffix = "cinematic photography, dramatic lighting, rich colours, high detail, 8k resolution"

    if visual_focus:
        prompt = f"{visual_focus}. {style_suffix}"
        if subject:
            prompt = f"{subject}: {prompt}"
    elif subject:
        prompt = f"{subject}. A cinematic scene evoking this theme. {style_suffix}"
    else:
        prompt = f"Abstract artistic composition with dramatic lighting, cinematic. {style_suffix}"

    if len(prompt) > 600:
        prompt = prompt[:597] + "..."
    return prompt


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# THEMES — simplified to colour values for text & accent overlays
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THEMES = {
    "ocean": {
        "name": "Ocean Depth",
        "accent": "#2980b9",
        "accent_light": "#5dade2",
        "text_primary": "#ffffff",
        "text_secondary": "#bdc3c7",
    },
    "sunset": {
        "name": "Sunset Glow",
        "accent": "#e74c3c",
        "accent_light": "#f1948a",
        "text_primary": "#ffffff",
        "text_secondary": "#d5b8ff",
    },
    "forest": {
        "name": "Forest Canopy",
        "accent": "#27ae60",
        "accent_light": "#82e0aa",
        "text_primary": "#ffffff",
        "text_secondary": "#a3c9b6",
    },
    "purple": {
        "name": "Cosmic Violet",
        "accent": "#7c3aed",
        "accent_light": "#a78bfa",
        "text_primary": "#ffffff",
        "text_secondary": "#c4b5fd",
    },
    "monochrome": {
        "name": "Slate",
        "accent": "#64748b",
        "accent_light": "#94a3b8",
        "text_primary": "#f1f5f9",
        "text_secondary": "#94a3b8",
    },
}

SAMPLE_RATE = 24000  # Kokoro native sample rate


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KOKORO TTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_kokoro_instance = None
_available_voices = None


def init_kokoro():
    """Lazy-init Kokoro TTS model (singleton)."""
    global _kokoro_instance, _available_voices
    if _kokoro_instance is None:
        from kokoro_onnx import Kokoro
        model_path = os.path.expanduser(
            '~/.hermes/skills/voice-bridge/assets/kokoro/model.onnx'
        )
        voices_path = os.path.expanduser(
            '~/.hermes/skills/voice-bridge/assets/voices-v1.0.bin'
        )
        k = Kokoro(model_path, voices_path)
        _kokoro_instance = k
        _available_voices = list(k.voices.keys())
        print(f"  Kokoro TTS loaded: {len(_available_voices)} voices")
    return _kokoro_instance


MAX_PHONEME_LENGTH = 510


def _split_phonemes(phonemes: str) -> list[str]:
    """Split phonemes into batches of MAX_PHONEME_LENGTH."""
    import re
    words = re.split(r"([.,!?;])", phonemes)
    batches = []
    current = ""
    for part in words:
        part = part.strip()
        if part:
            if len(current) + len(part) + 1 >= MAX_PHONEME_LENGTH:
                batches.append(current.strip())
                current = part
            else:
                if part in ".,!?;":
                    current += part
                else:
                    if current:
                        current += " "
                    current += part
    if current:
        batches.append(current.strip())
    return batches


def trim_audio(audio, threshold=0.01, min_silence=24000):
    """Trim leading/trailing silence."""
    import numpy as np
    mask = np.abs(audio) > threshold
    if not np.any(mask):
        return audio
    nonzero = np.where(mask)[0]
    start = max(0, nonzero[0] - min(4000, nonzero[0]))
    end = min(len(audio), nonzero[-1] + 4000)
    return audio[start:end]


def generate_speech(text, voice="af_bella", speed=1.0):
    """
    Generate speech audio from text using Kokoro's low-level ONNX session.
    Returns (audio_array [float32], duration_seconds).
    """
    import numpy as np
    k = init_kokoro()

    if not text or not text.strip():
        return np.array([], dtype=np.float32), 0.0

    phonemes_str = k.tokenizer.phonemize(text.strip(), "en-us")
    batches = _split_phonemes(phonemes_str)

    voice_emb = k.voices.get(voice)
    if voice_emb is None:
        voice_emb = k.voices.get("af_bella")

    audio_parts = []
    for batch in batches:
        tokens = np.array(k.tokenizer.tokenize(batch), dtype=np.int64)
        style = voice_emb[len(tokens), 0, :].reshape(1, -1).astype(np.float32)
        padded = np.array([[0, *tokens.tolist(), 0]], dtype=np.int64)

        inputs = {
            "input_ids": padded,
            "style": style,
            "speed": np.array([speed], dtype=np.float32),
        }
        audio = k.sess.run(None, inputs)[0].flatten().astype(np.float32)
        audio = trim_audio(audio)
        audio_parts.append(audio)

    if not audio_parts:
        return np.array([], dtype=np.float32), 0.0
    result = np.concatenate(audio_parts)
    return result, len(result) / SAMPLE_RATE


def save_audio(audio, path):
    """Save float32 numpy array as WAV."""
    import soundfile as sf
    sf.write(path, audio, SAMPLE_RATE)
    return path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IMAGE COMPOSITING (no download — pre-generated AI images)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_font(size):
    """Load Helvetica from system, fall back to default bitmap font."""
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except (IOError, OSError):
        return ImageFont.load_default()


def _word_wrap(text, max_chars=50):
    """Simple word wrapper (no hyphenation)."""
    words = text.split()
    lines, current = [], ""
    for w in words:
        test = current + " " + w if current else w
        if len(test) <= max_chars:
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def render_image_scene(scene, theme_name, idx, total, tmp_dir, gen_img_path):
    """Render an image scene: composite text overlay on a pre-generated AI image.

    Fields expected:
        type       - "image" (required, enforced by caller)
        title      - scene headline (top-center pill badge)
        subtitle   - optional sub-headline below title
        body       - optional body text (bottom panel)
        narration  - TTS text (handled separately by pipeline)
        gen_prompt - optional image generation prompt override

    Returns a Path to the rendered PNG.
    """
    t = THEMES.get(theme_name, THEMES["ocean"])
    out_path = tmp_dir / f"scene_{idx:03d}.png"

    try:
        img = Image.open(gen_img_path).convert("RGB")
        # Already the right dimensions (generated at W×H), no crop needed

        # Semi-transparent gradient overlay (darker toward bottom)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        for y in range(H):
            alpha = int(50 + (y / H) * 120)
            odraw.line([(0, y), (W, y)], fill=(0, 0, 0, min(alpha, 150)))
        img.paste(overlay, (0, 0), overlay)

        draw = ImageDraw.Draw(img)

        title = scene.get("title", "")
        subtitle = scene.get("subtitle", "")
        body = scene.get("body", "")

        font_title = _load_font(sy(50))
        font_subtitle = _load_font(sy(28))
        font_body = _load_font(sy(22))
        font_page = _load_font(sy(16))

        cur_y = sy(85)

        # ── Title with pill background ──
        if title:
            bbox = draw.textbbox((0, 0), title, font=font_title)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pill_w = tw + sx(60)
            draw.rounded_rectangle(
                [(W // 2 - pill_w // 2, cur_y - sy(12)),
                 (W // 2 + pill_w // 2, cur_y + th + sy(14))],
                radius=sr(10), fill=(0, 0, 0, 170)
            )
            draw.text((W // 2, cur_y + th // 2 + sy(2)), title,
                      fill="#FFFFFF", font=font_title, anchor="mt")
            cur_y += th + sy(28)

            # Accent underline
            draw.rounded_rectangle(
                [(W // 2 - sx(40), cur_y), (W // 2 + sx(40), cur_y + sy(3))],
                radius=sr(2), fill=t["accent"]
            )
            cur_y += sy(18)

        # ── Subtitle ──
        if subtitle:
            bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
            sh = bbox[3] - bbox[1]
            draw.text((W // 2, cur_y + sh // 2), subtitle,
                      fill=t["text_secondary"], font=font_subtitle, anchor="mt")
            cur_y += sh + sy(15)

        # ── Body text (bottom panel) ──
        if body:
            bx, by = sx(100), H - sy(140)
            draw.rounded_rectangle(
                [(bx - sx(10), by - sy(8)), (bx + sx(1820), by + sy(80))],
                radius=sr(6), fill=(0, 0, 0, 140)
            )
            lines = _word_wrap(body, 60)
            for j, line in enumerate(lines):
                draw.text((W // 2, by + sy(20) + j * sy(30)), line,
                          fill="#DDDDDD", font=font_body, anchor="mt")

        # ── Page number ──
        draw.text((W - sx(60), H - sy(35)), f"{idx:02d} / {total:02d}",
                  fill=(180, 180, 180), font=font_page)

        img.save(out_path, quality=95)
        print(f"    [{idx}/{total}] composited: {title[:50]}")
        return out_path

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Scene {idx}: failed to composite image scene: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUDIO PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_narration_scenes(scenes, voice, speed, min_duration, trans):
    """Generate narration WAVs for scenes with `narration` field."""
    audio_dir = Path(tempfile.mkdtemp(prefix="infographic_audio_"))
    scene_durations = []
    audio_paths = []

    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "").strip()
        if narration:
            print(f"    [{i+1}/{len(scenes)}] Generating narration ({len(narration)} chars)...")
            audio, audio_dur = generate_speech(narration, voice, speed)
            wav_path = audio_dir / f"narration_{i:03d}.wav"
            save_audio(audio, wav_path)
            scene_dur = audio_dur + trans + 0.3
            scene_durations.append(scene_dur)
            audio_paths.append(wav_path)
        else:
            scene_dur = scene.get("duration", min_duration)
            scene_durations.append(scene_dur)
            silent = audio_dir / f"silence_{i:03d}.wav"
            import soundfile as sf
            import numpy as np
            sf.write(silent, np.zeros(int(min_duration * SAMPLE_RATE), dtype=np.float32), SAMPLE_RATE)
            audio_paths.append(silent)

    return scene_durations, audio_paths, audio_dir


def build_combined_audio(audio_paths, scene_durations, output_path):
    """Concatenate per-scene audio WAVs into one, padded to match scene durations."""
    import numpy as np, soundfile as sf

    clips = []
    for apath, sdur in zip(audio_paths, scene_durations):
        data, sr = sf.read(apath)
        target_samples = int(sdur * sr)
        if len(data) < target_samples:
            padding = np.zeros(target_samples - len(data), dtype=np.float32)
            padded = np.concatenate([data.astype(np.float32), padding])
        else:
            padded = data[:target_samples].astype(np.float32)
        clips.append(padded)

    combined = np.concatenate(clips) if clips else np.array([], dtype=np.float32)
    sf.write(output_path, combined, SAMPLE_RATE)
    dur_sec = len(combined) / SAMPLE_RATE
    return output_path, dur_sec


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VIDEO GENERATION PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_video(data, output_path, work_dir=None, vertical=False):
    """
    Main pipeline:
    1. Validate all scenes are type "image"
    2. Generate AI images for each scene via mflux Flux2-klein-9B
    3. Generate narration audio per scene via Kokoro TTS
    4. Composite text overlays onto AI images
    5. Build combined audio track padded to video length
    6. Compile video with FFmpeg xfade transitions + synchronized audio
    """
    global W, H
    if vertical:
        W, H = 1080, 1920  # Vertical 9:16
        print(f"  Mode: VERTICAL ({W}x{H})")
    else:
        W, H = REF_W, REF_H  # Landscape 16:9
        print(f"  Mode: LANDSCAPE ({W}x{H})")

    title = data.get("title", "Infographic")
    theme = data.get("theme", "ocean")
    scenes = data.get("scenes", [])
    trans = data.get("transition_duration", 0.8)
    default_dur = data.get("duration_per_scene", 4.0)
    nar_voice = data.get("narration_voice", "bf_isabella")
    nar_speed = data.get("narration_speed", 1.0)

    if not scenes:
        print("ERROR: No scenes provided.")
        return False

    # ── Validate: ALL scenes must be type "image" ──
    for i, scene in enumerate(scenes):
        stype = scene.get("type", "")
        if stype != "image":
            print(f"ERROR: Scene {i+1} has type '{stype}'. "
                  f"This skill ONLY accepts 'image' scenes (AI-generated photos with text compositing). "
                  f"Use the infographic-video-svg skill for SVG infographic cards.")
            return False

    tmp_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="infographic_"))
    need_cleanup = False
    if not work_dir:
        need_cleanup = True
    else:
        tmp_dir.mkdir(parents=True, exist_ok=True)

    audio_dir = None
    total = len(scenes)
    print(f"\n  === Generating {total}-scene AI-image video: {title} ===")

    # ── Step 1: Craft cinematic prompts via LLM ──
    print("  [1/7] Crafting cinematic prompts via expert LLM...")
    generate_cinematic_prompts(scenes, title)

    # Free GPU memory: stop omlx if running (MLX LLM conflicts with mflux)
    _ensure_mflux_vram()

    # ── Step 2: Generate AI images for each scene ──
    print("  [2/7] Generating AI images via mflux Flux2-klein-9B...")
    gen_image_paths = generate_mflux_images(scenes, tmp_dir, W, H)

    # ── Step 2: Generate narration audio ──
    print("  [3/7] Generating narration audio...")
    scene_durations, audio_paths, audio_dir = generate_narration_scenes(
        scenes, nar_voice, nar_speed, default_dur, trans
    )

    # ── Step 3: Composite text onto generated images ──
    print("  [4/7] Compositing text overlays onto AI images...")
    png_paths = []
    for i, scene in enumerate(scenes):
        print(f"    [{i+1}/{total}] Compositing scene...")
        png_path = render_image_scene(scene, theme, i + 1, total, tmp_dir, gen_image_paths[i])
        png_paths.append(png_path)

    # ── Step 4: (skip — already rendered as PNGs) ──
    print("  [5/7] All scenes rendered as PNG (no SVG conversion needed).")

    # ── Step 5: Build combined audio track ──
    print("  [6/7] Building combined audio track...")
    combined_audio_path = tmp_dir / "combined_narration.wav"
    combined_audio_path, audio_dur = build_combined_audio(
        audio_paths, scene_durations, combined_audio_path
    )
    print(f"    Combined audio duration: {audio_dur:.1f}s")

    # ── Step 6: Compile video with FFmpeg ──
    print("  [7/7] Assembling video with FFmpeg...")

    n = len(png_paths)

    if n == 1:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(scene_durations[0]), "-i", str(png_paths[0]),
            "-i", str(combined_audio_path),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                   f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
            "-r", "30",
            str(output_path)
        ]
    else:
        input_args = []
        for i, png in enumerate(png_paths):
            input_args.extend(["-loop", "1", "-t", str(scene_durations[i]), "-i", str(png)])

        durations = scene_durations
        offset = durations[0] - trans
        filter_parts = []
        for i in range(1, n):
            if i == 1:
                filter_parts.append(
                    f"[0][1]xfade=transition=fade:duration={trans}:offset={offset}[v1]"
                )
            else:
                filter_parts.append(
                    f"[v{i-1}][{i}]xfade=transition=fade:duration={trans}:offset={offset}[v{i}]"
                )
            offset += durations[i] - trans

        filter_complex = "; ".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            *input_args,
            "-i", str(combined_audio_path),
            "-filter_complex", filter_complex,
            "-map", f"[v{n-1}]",
            "-map", f"{n}:a",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            str(output_path)
        ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        print(f"  ✓ Video saved: {output_path}")
        size_kb = Path(output_path).stat().st_size / 1024
        print(f"  Size: {size_kb:.0f} KB")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: FFmpeg failed:")
        print(f"  stderr: {e.stderr.decode()[:1000]}")
        return False
    finally:
        if need_cleanup:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        if audio_dir:
            shutil.rmtree(audio_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Generate image-only infographic video from scene descriptions")
    parser.add_argument("--scenes", "-s", type=str, help="Path to JSON scenes file")
    parser.add_argument("--output", "-o", type=str, default="infographic.mp4", help="Output video path")
    parser.add_argument("--work-dir", "-w", type=str, help="Working directory (kept for debugging)")
    parser.add_argument("--vertical", "-v", action="store_true",
                        help="Render vertical 9:16 (1080×1920) for Instagram/Reels")
    args = parser.parse_args()

    if args.scenes:
        with open(args.scenes) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    success = generate_video(data, args.output, args.work_dir, vertical=args.vertical)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
