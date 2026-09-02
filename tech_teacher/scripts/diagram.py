#!/usr/bin/env python3
"""Generate per-scene SVG diagrams and render them to PNG for tech_teacher videos.

This module closes the gap in orchestrate.py: it used to rely on an external
"loop skill" (which does not exist) to produce per-scene images, so every
scene fell back to a black background. This module derives the diagram content
directly from each scene's title + body and renders a clean, professional slide.

Pipeline:
    script.md -> split scenes -> build SVG per scene -> cairosvg -> PNG

Usage:
    python3 diagram.py --workdir <workdir> [--width 1280] [--height 720]
    python3 diagram.py <script.md> --out-dir <dir>

The SVG uses Helvetica (macOS) with manual word-wrapping: cairosvg has no text
measurement API, so we estimate characters-per-line from an average glyph width
and verify the result visually (see skill's references/debugging.md). Tune the
CHAR_WIDTH_FACTOR below if any line is clipped or has excessive trailing space.
"""

from __future__ import annotations

import argparse
import os
import re


# Average glyph width for Helvetica at a given font size (fraction of fontSize).
# 0.52 is conservative: fewer chars per line means no right-edge clipping, at the
# cost of a few blank lines. Verify with vision_analyze and tune if needed.
CHAR_WIDTH_FACTOR = 0.52

# Theme palette (dark, high-contrast teaching slides).
BG = "#141b2e"          # deep navy background
BANNER = "#243b6a"      # header band
WHITE = "#ffffff"       # title text
CYAN = "#8fe0ef"        # subtitle/caption accent
BODY = "#e2e1ed"        # body text
BULLET = "#5aa9e6"      # bullet accent


def split_into_scenes(script_text: str) -> list[dict]:
    """Split a teaching script into scenes on '## Scene N' markers."""
    lines = script_text.splitlines()
    scenes: list[dict] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        body = "\n".join(l.strip() for l in current_lines if l.strip()).strip()
        body = re.sub(r"\s+", " ", body)
        if current_lines and not any(l.strip().startswith("#") for l in current_lines):
            scenes.append({"title": current_title or f"Scene {len(scenes)+1}", "text": body})
        current_lines = []

    for line in lines:
        m = re.match(r"##\s+(?:Scene\s+\d+[:\-]?\s*)?(.+)", line.strip())
        if m:
            flush()
            current_title = m.group(1).strip()
        elif line.strip().startswith("#"):
            continue  # top-level heading ignored
        elif line.strip():
            current_lines.append(line)
    flush()

    if not scenes:  # fallback: paragraph splitting
        for block in re.split(r"\n\s*\n", script_text.strip()):
            text = re.sub(r"\s+", " ", block.strip())
            if text:
                scenes.append({"title": f"Section {len(scenes)+1}", "text": text})
    return scenes


def split_sentences(text: str, max_count: int = 4) -> list[str]:
    """Split body text into up to max_count sentence-clusters for bullets."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p][:max_count]


def wrap(text: str, font_size: int, max_px: float) -> list[str]:
    """Wrap text into lines no wider than max_px, estimated from glyph width."""
    char_w = font_size * CHAR_WIDTH_FACTOR
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        if (len(" ".join(cur + [w])) * char_w) <= max_px or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_svg(title: str, subtitle: str, bullets: list[str], w: int, h: int) -> str:
    """Build an SVG string for one scene's slide."""
    title = _esc(title)
    subtitle = _esc(subtitle)

    usable_w = w - 180  # margins of 90px each side
    title_lines = wrap(title, 46, usable_w) or [""]
    subtitle_line = (wrap(subtitle, 28, usable_w) + [""])[0]

    # Body bullets at a size that fits ~2 lines each.
    body_svg: list[str] = []
    y_cursor = 0

    if len(title_lines) == 1:
        t_y = 92
    else:
        t_y = 78

    title_svg = ""
    for ln in title_lines:
        y = t_y + (0 if len(title_lines) == 1 else 60 * title_lines.index(ln))
        title_svg += f'<text x="{w//2}" y="{y}" text-anchor="middle" ' \
                     f'font-family="Helvetica, \'Helvetica Neue\'" font-size="46" ' \
                     f'font-weight="bold" fill="{WHITE}">{ln}</text>'

    sub_y = 78 + len(title_lines) * 60 + 42
    subtitle_svg = (f'<text x="{w//2}" y="{sub_y}" text-anchor="middle" '
                    f'font-family="Helvetica, \'Helvetica Neue\'" font-size="28" '
                    f'fill="{CYAN}">{subtitle_line}</text>') if subtitle_line else ""

    y_cursor = sub_y + 90
    for b in bullets[:4]:
        if not b.strip():
            y_cursor += 26
            continue
        for ln in wrap(b, 30, usable_w):
            body_svg.append(
                f'<text x="90" y="{y_cursor}" font-family="Helvetica, \'Helvetica Neue\'" '
                f'font-size="30" fill="{BODY}"><tspan fill="{BULLET}" '
                f'font-weight="bold">&#8226;</tspan> {ln}</text>'
            )
            y_cursor += 52

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="{BG}"/>'
        f'<rect x="0" y="0" width="{w}" height="150" fill="{BANNER}"/>'
        f'{title_svg}{subtitle_svg}'
        f'<g>{"".join(body_svg)}</g>'
        f'</svg>'
    )


def render_svg_to_png(svg_src_path: str, png_dst_path: str) -> bool:
    """Render one SVG file to PNG via cairosvg. Returns success flag."""
    try:
        import cairosvg  # noqa: F401
    except Exception:
        return False
    try:
        cairosvg.svg2png(url=svg_src_path, write_to=png_dst_path)
        return True
    except Exception:
        print(f"  [warn] cairosvg failed for {os.path.basename(svg_src_path)}: "
              f"{__import__('traceback').format_exc().strip()}", flush=True)
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate per-scene SVG->PNG diagrams.")
    ap.add_argument("script", nargs="?", default=None, help="Path to script.md")
    ap.add_argument("--workdir", default=None, help="Work dir (holds script.md + images/)")
    ap.add_argument("--out-dir", default=None, help="Directory to write PNGs into")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    if args.script:
        src_path = os.path.abspath(args.script)
    elif args.workdir:
        src_path = os.path.join(os.path.abspath(args.workdir), "script.md")
    else:
        src_path = os.path.join(os.getcwd(), "script.md")

    if args.out_dir:
        dst_path = os.path.abspath(args.out_dir)
    elif args.workdir:
        dst_path = os.path.join(os.path.abspath(args.workdir), "images")
    else:
        dst_path = os.path.join(os.getcwd(), "images")

    w, h = args.width, args.height
    os.makedirs(dst_path, exist_ok=True)

    with open(src_path) as f:
        script_text = f.read()

    scenes = split_into_scenes(script_text)
    print(f"[diagram] {len(scenes)} scene(s) -> {dst_path}")
    for i, s in enumerate(scenes, start=1):
        bullets = split_sentences(s["text"], max_count=4)
        subtitle = f"Scene {i} of {len(scenes)}"
        svg = build_svg(s["title"], subtitle, bullets, w, h)
        safe_title = re.sub(r"[^a-z0-9]+", "-", s["title"].lower())[:24]
        svg_path = os.path.join(dst_path, f"scene{i:02d}.{safe_title}.svg")
        with open(svg_path, "w") as f:
            f.write(svg)
        png = os.path.join(dst_path, f"scene{i:02d}.png")
        ok = render_svg_to_png(svg_path, png)
        print(f"  [{i}/{len(scenes)}] {s['title'][:42]:42s} -> "
              f"{'PNG' if ok else 'SVG-only'} ({len(bullets)} bullets)")
    print("[diagram] done")


if __name__ == "__main__":
    main()
