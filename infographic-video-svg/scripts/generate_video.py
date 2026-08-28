#!/usr/bin/env python3
"""
Infographic Video Generator — Pure SVG Edition
───────────────────────────────────────────────
Takes structured scene descriptions with narration text → generates SVGs →
TTS narration via Kokoro → crossfade MP4 video with synchronized audio.

All scenes are SVG infographic cards (no image downloads, no photo compositing).
Ideal for programming, data, abstract concepts, charts, stats, and timelines.

Usage:
  # From scene JSON file
  python3 generate_video.py --scenes scenes.json --output video.mp4

  # From JSON on stdin
  echo '{"title":"...","scenes":[...]}' | python3 generate_video.py --output video.mp4

Input format (stdin or file):
{
  "title": "Video Title",
  "theme": "ocean|sunset|forest|purple|monochrome",
  "duration_per_scene": 4.0,
  "transition_duration": 0.8,
  "scenes": [
    {"type": "title", "subtitle": "..."},
    {"type": "stat", "stat": "85%", "stat_label": "of users..."},
    {"type": "list", "items": [...], "highlight_index": 0},
    {"type": "chart_bar", "bars": [{"label":"A","value":80},...]},
    {"type": "comparison", "left_title":"Old","right_title":"New",
     "left_items":[...], "right_items":[...]},
    {"type": "timeline", "steps": [...]},
    {"type": "quote", "quote": "...", "attribution": "..."},
    {"type": "closing"},
    {"type": "content", "subtitle": "...", "body": "..."}
  ]
}

Supported scene types: title, stat, list, chart_bar, comparison, timeline,
quote, closing, content.

The "image" type is NOT supported and is explicitly rejected — use the
infographic-video-image skill for real-photo compositing.

Dependencies: cairosvg, ffmpeg, kokoro-onnx, soundfile, numpy, python3
"""
import json, os, sys, subprocess, tempfile, shutil, math, textwrap, argparse
from xml.sax.saxutils import escape as xml_escape
from pathlib import Path

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# THEMES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THEMES = {
    "ocean": {
        "name": "Ocean Depth",
        "bg_start": "#0c2340", "bg_end": "#1a5276",
        "accent": "#2980b9", "accent_light": "#5dade2",
        "accent_glow": "#1a527640",
        "text_primary": "#ffffff", "text_secondary": "#bdc3c7",
        "card_bg": "#ffffff12", "card_border": "#ffffff20",
        "deco1": "#1abc9c", "deco2": "#3498db",
        "highlight_bg": "#2980b930",
    },
    "sunset": {
        "name": "Sunset Glow",
        "bg_start": "#2d1b4e", "bg_end": "#6b2fa0",
        "accent": "#e74c3c", "accent_light": "#f1948a",
        "accent_glow": "#6b2fa040",
        "text_primary": "#ffffff", "text_secondary": "#d5b8ff",
        "card_bg": "#ffffff12", "card_border": "#ffffff20",
        "deco1": "#f39c12", "deco2": "#e74c3c",
        "highlight_bg": "#e74c3c30",
    },
    "forest": {
        "name": "Forest Canopy",
        "bg_start": "#1a2e1a", "bg_end": "#22553d",
        "accent": "#27ae60", "accent_light": "#82e0aa",
        "accent_glow": "#22553d40",
        "text_primary": "#ffffff", "text_secondary": "#a3c9b6",
        "card_bg": "#ffffff12", "card_border": "#ffffff20",
        "deco1": "#2ecc71", "deco2": "#f1c40f",
        "highlight_bg": "#27ae6030",
    },
    "purple": {
        "name": "Cosmic Violet",
        "bg_start": "#1a0a2e", "bg_end": "#3d1e6d",
        "accent": "#7c3aed", "accent_light": "#a78bfa",
        "accent_glow": "#3d1e6d40",
        "text_primary": "#ffffff", "text_secondary": "#c4b5fd",
        "card_bg": "#ffffff12", "card_border": "#ffffff20",
        "deco1": "#8b5cf6", "deco2": "#ec4899",
        "highlight_bg": "#7c3aed30",
    },
    "monochrome": {
        "name": "Slate",
        "bg_start": "#0f141e", "bg_end": "#1e293b",
        "accent": "#64748b", "accent_light": "#94a3b8",
        "accent_glow": "#1e293b40",
        "text_primary": "#f1f5f9", "text_secondary": "#94a3b8",
        "card_bg": "#ffffff08", "card_border": "#ffffff15",
        "deco1": "#475569", "deco2": "#334155",
        "highlight_bg": "#64748b30",
    },
}

SAMPLE_RATE = 24000  # Kokoro native sample rate

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KOKORO TTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_kokoro_instance = None
_available_voices = None

def init_kokoro():
    """Lazy-init Kokoro TTS model (singleton)."""
    global _kokoro_instance, _available_voices
    if _kokoro_instance is None:
        from kokoro_onnx import Kokoro, Tokenizer
        import numpy as np
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


MAX_PHONEME_LENGTH = 510  # Kokoro model limit


def _split_phonemes(phonemes: str) -> list[str]:
    """Split phonemes into batches of MAX_PHONEME_LENGTH, preferring punctuation breaks."""
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
    """Trim leading and trailing silence from audio, matching Kokoro's trim behavior."""
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

    Mirrors Kokoro.create() pipeline exactly:
      1. phonemize(text)  → IPA phoneme string
      2. split into batches (max MAX_PHONEME_LENGTH)
      3. per batch: tokenize, index voice by unpadded token count, pad, infer
      4. trim silence between batches
      5. concatenate

    Direct ONNX bypasses a dtype bug in kokoro-onnx 0.4.7
    (speed passed as int32 but model expects float32).
    """
    import numpy as np
    k = init_kokoro()

    if not text or not text.strip():
        return np.array([], dtype=np.float32), 0.0

    # Step 1: phonemize raw text → IPA phoneme string (CRITICAL: tokenize()
    #          expects phonemes, NOT raw English text)
    phonemes_str = k.tokenizer.phonemize(text.strip(), "en-us")

    # Step 2: split long phoneme strings into batches
    batches = _split_phonemes(phonemes_str)

    # Step 3: get voice embedding tensor
    voice_emb = k.voices.get(voice)
    if voice_emb is None:
        voice_emb = k.voices.get("af_bella")

    # Step 4: process each batch
    audio_parts = []
    for batch in batches:
        tokens = np.array(k.tokenizer.tokenize(batch), dtype=np.int64)

        # Index voice by unpadded token count (matches Kokoro internals)
        style = voice_emb[len(tokens), 0, :].reshape(1, -1).astype(np.float32)
        padded = np.array([[0, *tokens.tolist(), 0]], dtype=np.int64)

        inputs = {
            "input_ids": padded,
            "style": style,
            "speed": np.array([speed], dtype=np.float32),
        }
        audio = k.sess.run(None, inputs)[0].flatten().astype(np.float32)
        # Trim silence between batches (matches Kokoro create())
        audio = trim_audio(audio)
        audio_parts.append(audio)

    # Step 5: concatenate
    if len(audio_parts) == 0:
        return np.array([], dtype=np.float32), 0.0
    result = np.concatenate(audio_parts)
    return result, len(result) / SAMPLE_RATE


def save_audio(audio, path):
    """Save float32 numpy array as WAV."""
    import soundfile as sf
    sf.write(path, audio, SAMPLE_RATE)
    return path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SVG HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

W, H = 1920, 1080  # 16:9

def esc(t):
    return xml_escape(str(t))

def svg_tag(content, defs=""):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
{defs}
<style><![CDATA[
  text {{ font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; }}
  .num {{ font-family: 'SF Mono', Menlo, Monaco, monospace; }}
]]></style>
{content}
</svg>'''

def grad_def(id_name, x1, y1, x2, y2, stops):
    """Generate a linearGradient definition string."""
    stops_xml = '\n'.join(
        f'    <stop offset="{p}" style="stop-color:{c};stop-opacity:{o}" />'
        for p, c, o in stops
    )
    return f'''<linearGradient id="{id_name}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">
{stops_xml}
  </linearGradient>'''

def rect(x, y, w, h, fill="none", stroke="none", sw=1, rx=0, opacity=1, cls=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}" opacity="{opacity}" class="{cls}" />'

def circle(cx, cy, r, fill="none", stroke="none", sw=1, opacity=1):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}" />'

def text_svg(text, x, y, size=24, color="#fff", weight="400", align="left", opacity=1, cls=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{align}" opacity="{opacity}" class="{cls}">{esc(text)}</text>'

def wrap_text(text, max_chars=50):
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DECORATIVE ELEMENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def deco_circles(t):
    """Decorative floating circles in background."""
    c = t["accent_glow"]
    return (
        circle(150, 120, 300, fill=c) +
        circle(W - 100, H - 80, 200, fill=c) +
        circle(W // 2, H // 2, 400, fill=c, opacity=0.3) +
        circle(50, H - 50, 60, fill=t["deco1"], opacity=0.15) +
        circle(W - 200, 200, 40, fill=t["deco2"], opacity=0.12)
    )

def accent_line(t):
    """Thin accent bar near top."""
    return rect(80, 40, 80, 4, fill=t["accent"], rx=2)

def page_number(idx, total, t):
    """Bottom-right page indicator."""
    return text_svg(f"{idx:02d} / {total:02d}", W - 60, H - 35, 14, t["text_secondary"], "400", "end")

def card(x, y, w, h, t):
    """Translucent content card."""
    return rect(x, y, w, h, fill=t["card_bg"], stroke=t["card_border"], sw=1, rx=12)

def section_title(text, x, y, t):
    """Section title with left accent bar."""
    bar = rect(x, y - 24, 5, 32, fill=t["accent"], rx=2)
    lbl = text_svg(text, x + 18, y + 2, 22, t["text_primary"], "700", "start")
    return bar + lbl

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCENE RENDERERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_title(scene, t, idx, total):
    """Title / opening slide."""
    title = scene.get("title", "")
    subtitle = scene.get("subtitle", "")
    icon = scene.get("decorative_icon", "")
    
    bg = f'<rect width="{W}" height="{H}" fill="url(#bg)" />'
    elements = bg + deco_circles(t) + accent_line(t)
    
    # Large centered title
    elements += text_svg(title, W // 2, 460, 64, t["text_primary"], "800", "center")
    
    # Accent underline
    elements += rect(W // 2 - 60, 500, 120, 4, fill=t["accent"], rx=2)
    
    if subtitle:
        elements += text_svg(subtitle, W // 2, 580, 28, t["text_secondary"], "300", "center")
    
    if icon:
        elements += text_svg(icon, W // 2, 660, 40, t["accent"], "400", "center")
    
    elements += page_number(idx, total, t)
    
    defs = grad_def("bg", 0, 0, 1, 1, [
        ("0%", t["bg_start"], 1),
        ("100%", t["bg_end"], 1),
    ])
    return svg_tag(elements, defs)


def render_stat(scene, t, idx, total):
    """Big stat with label and description."""
    title = scene.get("title", "")
    stat_val = scene.get("stat", "")
    stat_label = scene.get("stat_label", "")
    description = scene.get("description", "")
    
    bg = f'<rect width="{W}" height="{H}" fill="url(#bg)" />'
    elements = bg + deco_circles(t) + accent_line(t) + page_number(idx, total, t)
    
    # Title
    elements += section_title(title, 80, 110, t)
    
    # Card in center
    cx, cy, cw, ch = 200, 280, 1520, 680
    elements += card(cx, cy, cw, ch, t)
    
    # Big stat number
    elements += text_svg(stat_val, W // 2, 520, 96, t["accent"], "800", "center", cls="num")
    
    # Stat label
    lines = wrap_text(stat_label, 60)
    y = 600
    for line in lines:
        elements += text_svg(line, W // 2, y, 30, t["text_primary"], "600", "center")
        y += 44
    
    # Description
    desc_lines = wrap_text(description, 80)
    y = 720
    for line in desc_lines:
        elements += text_svg(line, W // 2, y, 22, t["text_secondary"], "400", "center")
        y += 34
    
    defs = grad_def("bg", 0, 0, 1, 1, [
        ("0%", t["bg_start"], 1),
        ("100%", t["bg_end"], 1),
    ])
    return svg_tag(elements, defs)


def render_list(scene, t, idx, total):
    """List of items with optional highlights."""
    title = scene.get("title", "")
    items = scene.get("items", [])
    highlight_idx = scene.get("highlight_index", -1)
    
    bg = f'<rect width="{W}" height="{H}" fill="url(#bg)" />'
    elements = bg + deco_circles(t) + accent_line(t) + page_number(idx, total, t)
    
    # Title
    elements += section_title(title, 80, 110, t)
    
    # Card
    elements += card(80, 160, 1760, 820, t)
    
    y_start = 240
    for i, item in enumerate(items):
        y = y_start + i * 110
        is_hl = (i == highlight_idx)
        
        # Number badge
        badge_color = t["accent"] if is_hl else t["card_border"]
        elements += circle(150, y - 10, 20, fill=badge_color)
        elements += text_svg(str(i + 1), 150, y - 5, 16, t["text_primary"], "700", "middle")
        
        # Item text
        text_lines = wrap_text(item, 70)
        for j, line in enumerate(text_lines):
            color = t["text_primary"] if is_hl else t["text_secondary"]
            weight = "700" if is_hl and j == 0 else "400"
            size = 24 if j == 0 else 20
            elements += text_svg(line, 200, y + j * 30, size, color, weight, "start")
    
    defs = grad_def("bg", 0, 0, 1, 1, [
        ("0%", t["bg_start"], 1),
        ("100%", t["bg_end"], 1),
    ])
    return svg_tag(elements, defs)


def render_chart_bar(scene, t, idx, total):
    """Horizontal bar chart."""
    title = scene.get("title", "")
    bars = scene.get("bars", [])
    max_val = max((b.get("value", 0) for b in bars), default=100)
    
    bg = f'<rect width="{W}" height="{H}" fill="url(#bg)" />'
    elements = bg + deco_circles(t) + accent_line(t) + page_number(idx, total, t)
    
    # Title
    elements += section_title(title, 80, 110, t)
    
    # Card
    elements += card(80, 160, 1760, 820, t)
    
    chart_x = 200
    label_w = 350
    bar_max_w = 1200
    bar_h = 36
    bar_gap = 20
    start_y = 250
    
    for i, bar in enumerate(bars):
        y = start_y + i * (bar_h + bar_gap)
        val = bar.get("value", 0)
        label = bar.get("label", "")
        color = bar.get("color", t["accent"])
        
        # Label
        elements += text_svg(label, chart_x, y + bar_h, 22, t["text_primary"], "600", "start")
        
        # Bar background
        elements += rect(chart_x + label_w, y, bar_max_w, bar_h, fill=t["card_bg"], rx=bar_h // 2)
        
        # Bar fill
        bar_w = int(bar_max_w * (val / max_val))
        elements += rect(chart_x + label_w, y, bar_w, bar_h, fill=color, rx=bar_h // 2, opacity=0.85)
        
        # Value label
        elements += text_svg(str(val), chart_x + label_w + bar_w + 15, y + bar_h - 2, 20, t["accent_light"], "700", "start", cls="num")
    
    defs = grad_def("bg", 0, 0, 1, 1, [
        ("0%", t["bg_start"], 1),
        ("100%", t["bg_end"], 1),
    ])
    return svg_tag(elements, defs)


def render_comparison(scene, t, idx, total):
    """Side-by-side comparison."""
    title = scene.get("title", "")
    left_title = scene.get("left_title", "")
    right_title = scene.get("right_title", "")
    left_items = scene.get("left_items", [])
    right_items = scene.get("right_items", [])
    
    bg = f'<rect width="{W}" height="{H}" fill="url(#bg)" />'
    elements = bg + deco_circles(t) + accent_line(t) + page_number(idx, total, t)
    
    # Title
    elements += section_title(title, 80, 110, t)
    
    col_w = 780
    col_y = 220
    
    # Left column
    elements += card(80, col_y, col_w, 760, t)
    elements += text_svg(left_title, 80 + col_w // 2, col_y + 40, 28, t["accent"], "700", "center")
    # VS divider
    elements += circle(W // 2, col_y + 380, 36, fill=t["accent"])
    elements += text_svg("VS", W // 2, col_y + 388, 18, "#fff", "800", "middle")
    
    # Right column
    elements += card(W - 80 - col_w, col_y, col_w, 760, t)
    elements += text_svg(right_title, W - 80 - col_w // 2, col_y + 40, 28, t["accent"], "700", "center")
    
    def render_column(x_base, items):
        nonlocal elements
        for i, item in enumerate(items):
            y = col_y + 100 + i * 70
            elements += text_svg(f"✦ {item}", x_base + 30, y, 22, t["text_primary"], "400", "start")
    
    render_column(80, left_items)
    render_column(W - 80 - col_w, right_items)
    
    defs = grad_def("bg", 0, 0, 1, 1, [
        ("0%", t["bg_start"], 1),
        ("100%", t["bg_end"], 1),
    ])
    return svg_tag(elements, defs)


def render_timeline(scene, t, idx, total):
    """Vertical timeline with steps."""
    title = scene.get("title", "")
    steps = scene.get("steps", [])
    
    bg = f'<rect width="{W}" height="{H}" fill="url(#bg)" />'
    elements = bg + deco_circles(t) + accent_line(t) + page_number(idx, total, t)
    
    # Title
    elements += section_title(title, 80, 110, t)
    
    # Card
    elements += card(80, 160, 1760, 820, t)
    
    # Vertical line
    line_x = 200
    elements += rect(line_x, 220, 3, 680, fill=t["accent"], opacity=0.3, rx=1.5)
    
    step_y = 250
    step_gap = 130
    
    for i, step in enumerate(steps):
        y = step_y + i * step_gap
        
        # Circle on timeline
        elements += circle(line_x + 1, y, 14, fill=t["accent"], stroke="#fff", sw=3)
        
        # Number
        elements += text_svg(str(i + 1), line_x - 35, y + 6, 20, t["accent_light"], "700", "end", cls="num")
        
        # Title
        step_title = step.get("title", "")
        elements += text_svg(step_title, line_x + 40, y - 5, 24, t["text_primary"], "700", "start")
        
        # Description
        desc = step.get("description", "")
        desc_lines = wrap_text(desc, 50)
        for j, line in enumerate(desc_lines):
            elements += text_svg(line, line_x + 40, y + 30 + j * 26, 18, t["text_secondary"], "400", "start")
    
    defs = grad_def("bg", 0, 0, 1, 1, [
        ("0%", t["bg_start"], 1),
        ("100%", t["bg_end"], 1),
    ])
    return svg_tag(elements, defs)


def render_quote(scene, t, idx, total):
    """Large quote card."""
    title = scene.get("title", "")
    quote = scene.get("quote", "")
    attribution = scene.get("attribution", "")
    
    bg = f'<rect width="{W}" height="{H}" fill="url(#bg)" />'
    elements = bg + deco_circles(t) + accent_line(t) + page_number(idx, total, t)
    
    # Card
    cx, cy, cw, ch = 200, 240, 1520, 600
    elements += card(cx, cy, cw, ch, t)
    
    # Big quote mark
    elements += text_svg("\u201C", 250, 380, 120, t["accent"], "800", "start", 0.3)
    
    # Quote text
    quote_lines = wrap_text(quote, 40)
    y = 420
    for line in quote_lines:
        elements += text_svg(line, 360, y, 36, t["text_primary"], "700", "start")
        y += 50
    
    # Attribution
    if attribution:
        elements += rect(360, y + 20, 40, 2, fill=t["accent"], rx=1)
        elements += text_svg(f"\u2014 {attribution}", 420, y + 32, 22, t["text_secondary"], "400", "start")
    
    defs = grad_def("bg", 0, 0, 1, 1, [
        ("0%", t["bg_start"], 1),
        ("100%", t["bg_end"], 1),
    ])
    return svg_tag(elements, defs)


def render_closing(scene, t, idx, total):
    """Closing / thank you slide."""
    title = scene.get("title", "")
    subtitle = scene.get("subtitle", "")
    
    bg = f'<rect width="{W}" height="{H}" fill="url(#bg)" />'
    elements = bg + deco_circles(t) + accent_line(t)
    
    elements += text_svg(title or "Thank You", W // 2, 460, 56, t["text_primary"], "800", "center")
    elements += rect(W // 2 - 50, 500, 100, 4, fill=t["accent"], rx=2)
    
    if subtitle:
        elements += text_svg(subtitle, W // 2, 560, 24, t["text_secondary"], "300", "center")
    
    elements += page_number(idx, total, t)
    
    defs = grad_def("bg", 0, 0, 1, 1, [
        ("0%", t["bg_start"], 1),
        ("100%", t["bg_end"], 1),
    ])
    return svg_tag(elements, defs)


def render_content(scene, t, idx, total):
    """Generic content slide with title + body text."""
    title = scene.get("title", "")
    subtitle = scene.get("subtitle", "")
    body = scene.get("body", "")
    
    bg = f'<rect width="{W}" height="{H}" fill="url(#bg)" />'
    elements = bg + deco_circles(t) + accent_line(t) + page_number(idx, total, t)
    
    # Title
    elements += section_title(title, 80, 110, t)
    
    if subtitle:
        elements += text_svg(subtitle, 80, 160, 24, t["text_secondary"], "300", "start")
    
    # Card
    elements += card(80, 220, 1760, 760, t)
    
    # Body text
    body_lines = wrap_text(body, 90)
    y = 280
    for line in body_lines:
        elements += text_svg(line, 130, y, 26, t["text_primary"], "400", "start")
        y += 38
    
    defs = grad_def("bg", 0, 0, 1, 1, [
        ("0%", t["bg_start"], 1),
        ("100%", t["bg_end"], 1),
    ])
    return svg_tag(elements, defs)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DISPATCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCENE_RENDERERS = {
    "title": render_title,
    "stat": render_stat,
    "list": render_list,
    "chart_bar": render_chart_bar,
    "comparison": render_comparison,
    "timeline": render_timeline,
    "quote": render_quote,
    "closing": render_closing,
    "content": render_content,
}

def render_scene(scene, theme_name, idx, total):
    t = THEMES.get(theme_name, THEMES["ocean"])
    stype = scene.get("type", "content")
    renderer = SCENE_RENDERERS.get(stype, render_content)
    return renderer(scene, t, idx, total)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUDIO PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_narration_scenes(scenes, voice, speed, min_duration, trans):
    """Generate narration WAVs for scenes with `narration` field.
    Returns (scene_durations, audio_paths, audio_dir) where:
      scene_durations: list of per-scene display durations (seconds)
      audio_paths: list of per-scene WAV file paths (silence if no narration)
    """
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
            # Scene duration = narration + buffer for transition end overlap
            scene_dur = audio_dur + trans + 0.3
            scene_durations.append(scene_dur)
            audio_paths.append(wav_path)
        else:
            # No narration — use default duration, create silence
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
    total_dur = 0.0
    for apath, sdur in zip(audio_paths, scene_durations):
        data, sr = sf.read(apath)
        target_samples = int(sdur * sr)
        if len(data) < target_samples:
            padding = np.zeros(target_samples - len(data), dtype=np.float32)
            padded = np.concatenate([data.astype(np.float32), padding])
        else:
            padded = data[:target_samples].astype(np.float32)
        clips.append(padded)
        total_dur += target_samples / sr

    combined = np.concatenate(clips) if clips else np.array([], dtype=np.float32)
    sf.write(output_path, combined, SAMPLE_RATE)
    dur_sec = len(combined) / SAMPLE_RATE
    return output_path, dur_sec


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VIDEO GENERATION PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━




def generate_video(data, output_path, work_dir=None):
    """
    Main pipeline:
    1. Generate narration audio per scene via Kokoro TTS
    2. Render scene visuals → SVG via scene renderers
    3. Convert SVGs → PNGs via cairosvg
    4. Build combined audio track padded to video length
    5. Compile video with FFmpeg xfade transitions + synchronized audio
    """
    title = data.get("title", "Infographic")
    theme = data.get("theme", "ocean")
    scenes = data.get("scenes", [])
    trans = data.get("transition_duration", 0.8)
    default_dur = data.get("duration_per_scene", 4.0)
    nar_voice = data.get("narration_voice", "af_bella")
    nar_speed = data.get("narration_speed", 1.0)

    if not scenes:
        print("ERROR: No scenes provided.")
        return False

    # ── Validate: reject image-type scenes ──
    for i, scene in enumerate(scenes):
        stype = scene.get("type", "")
        if stype == "image":
            print(f"ERROR: Scene {i+1} has type 'image'. "
                  f"This skill ONLY accepts SVG scene types (title, stat, list, chart_bar, "
                  f"comparison, timeline, quote, closing, content). "
                  f"Use the infographic-video-image skill for real-photo compositing.")
            return False

    tmp_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="infographic_"))
    need_cleanup = False
    if not work_dir:
        need_cleanup = True
    else:
        tmp_dir.mkdir(parents=True, exist_ok=True)

    total = len(scenes)
    print(f"\n  === Generating {total} scene infographic: {title} ===")

    # ── Step 1: Generate narration audio ──
    print("  [1/5] Generating narration audio...")
    scene_durations, audio_paths, audio_dir = generate_narration_scenes(
        scenes, nar_voice, nar_speed, default_dur, trans
    )

    # ── Step 2: Render scene visuals ──
    print("  [2/5] Rendering scene visuals...")
    scene_paths = []
    for i, scene in enumerate(scenes):
        stype = scene.get("type", "content")
        svg = render_scene(scene, theme, i + 1, total)
        svg_path = tmp_dir / f"scene_{i+1:03d}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        scene_paths.append(svg_path)
        print(f"    [{i+1}/{total}] {stype}: {scene.get('title','')[:50]}")

    # ── Step 3: Convert SVGs → PNGs ──
    print("  [3/5] Rendering scene frames...")
    png_paths = []
    for spath in scene_paths:
        png_path = spath.with_suffix(".png")
        try:
            subprocess.run(
                ["cairosvg", str(spath), "-o", str(png_path)],
                check=True, capture_output=True, timeout=120
            )
            png_paths.append(png_path)
        except subprocess.CalledProcessError as e:
            print(f"  ERROR converting {spath.name}: {e.stderr.decode()}")
            return False

    # ── Step 4: Build combined audio track ──
    print("  [4/5] Building combined audio track...")
    combined_audio_path = tmp_dir / "combined_narration.wav"
    combined_audio_path, audio_dur = build_combined_audio(
        audio_paths, scene_durations, combined_audio_path
    )
    print(f"    Combined audio duration: {audio_dur:.1f}s")

    # ── Step 5: Compile video with FFmpeg ──
    print("  [5/5] Assembling video with FFmpeg...")

    n = len(png_paths)
    total_video_dur = sum(scene_durations)

    # Each scene PNG needs to loop for its scene_duration
    # FFmpeg input loops (provide infinite streams) + trim to exact duration
    input_args = []
    filter_parts = []
    stream_idx = 0

    if n == 1:
        # Single scene: no transitions
        sdur = scene_durations[0]
        input_args = ["-loop", "1", "-t", str(sdur), "-i", str(png_paths[0])]
        filter_complex = (
            f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setpts=PTS-STARTPTS[v0]"
        )
        last_label = "[v0]"
    else:
        # Multi-scene: each scene is a separate input, trimmed to duration
        # We use -​loop 1 -t scene_dur for each PNG, then xfade between them
        for i, png in enumerate(png_paths):
            input_args.extend(["-loop", "1", "-t", str(scene_durations[i]), "-i", str(png)])

        # Build xfade filter chain
        # Scene i starts at offset = sum(durations[:i]) for xfade placement
        durations = scene_durations
        offset = durations[0] - trans
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
        last_label = f"[v{n-1}]"

    cmd = ["ffmpeg", "-y"]
    cmd.extend(input_args)
    cmd.extend(["-i", str(combined_audio_path)])
    cmd.extend(["-filter_complex", filter_complex]) if filter_complex else None
    if last_label:
        cmd.extend(["-map", last_label])
    cmd.extend([
        "-map", f"{n}:a" if n > 0 else "1:a",  # Audio from the last input (the WAV)
        "-c:v", "libx264",
        "-c:a", "aac",
        # "-shortest",  # removed to prevent audio truncation; final frame holds for narration tail
        "-pix_fmt", "yuv420p",
        "-r", "30",
        str(output_path)
    ])

    # Fix audio mapping and correct command for single vs multi-scene
    if n == 1:
        # Single scene: video from [0], audio from [1] (the WAV)
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(scene_durations[0]), "-i", str(png_paths[0]),
            "-i", str(combined_audio_path),
            "-c:v", "libx264",
            "-c:a", "aac",
            # "-shortest",  # removed to prevent audio truncation; final frame holds for narration tail
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                     "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-r", "30",
            str(output_path)
        ]
    else:
        # Multi-scene: build proper command
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
            "-filter_complex", f"{filter_complex}",
            "-map", f"[v{n-1}]",
            "-map", f"{n}:a",  # Audio is the last input (index n)
            "-c:v", "libx264",
            "-c:a", "aac",
            # "-shortest",  # removed to prevent audio truncation; final frame holds for narration tail
            "-pix_fmt", "yuv420p",
            "-r", "30",
            str(output_path)
        ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        print(f"  \u2713 Video saved: {output_path}")
        size_kb = Path(output_path).stat().st_size / 1024
        print(f"  Size: {size_kb:.0f} KB")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: FFmpeg failed:")
        print(f"  stderr: {e.stderr.decode()[:1000]}")
        return False
    finally:
        # Clean up temp dirs
        if need_cleanup:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        shutil.rmtree(audio_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Generate infographic video from scene descriptions")
    parser.add_argument("--scenes", "-s", type=str, help="Path to JSON scenes file")
    parser.add_argument("--output", "-o", type=str, default="infographic.mp4", help="Output video path")
    parser.add_argument("--work-dir", "-w", type=str, help="Working directory (kept for debugging)")
    args = parser.parse_args()
    
    # Read scenes JSON
    if args.scenes:
        with open(args.scenes) as f:
            data = json.load(f)
    else:
        # Read from stdin
        data = json.load(sys.stdin)
    
    success = generate_video(data, args.output, args.work_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
