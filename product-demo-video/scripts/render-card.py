#!/usr/bin/env python3
"""Render title cards and caption bars as PNGs (PIL) for the video pipeline.

usage:
  render-card.py card    --text "TITLE" [--sub "subtitle"] --w 1280 --h 720 --out intro.png
  render-card.py caption --text "1. Landing" --w 1280 [--h 96] --out cap01.png

card    -> full-frame dark title card (RGB)
caption -> translucent bottom bar; the rest of the image is transparent
browserbar -> fake browser chrome (traffic lights + URL field) over a dark
              page area — the "entering the URL" moment before a scene
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def card(a):
    img = Image.new("RGB", (a.w, a.h), (15, 23, 42))
    d = ImageDraw.Draw(img)

    def center(text, font, y, fill):
        bbox = d.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        d.text(((a.w - w) / 2, y - bbox[1]), text, font=font, fill=fill)

    center(a.text, load_font(int(a.h * 0.09)), a.h * 0.38, (240, 244, 248))
    if a.sub:
        center(a.sub, load_font(int(a.h * 0.045)), a.h * 0.58, (148, 163, 184))
    img.save(a.out)
    print(a.out)


def caption(a):
    img = Image.new("RGBA", (a.w, a.h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, a.w, a.h], fill=(15, 23, 42, 215))
    f = load_font(int(a.h * 0.45))
    bbox = d.textbbox((0, 0), a.text, font=f)
    d.text((36, (a.h - (bbox[3] - bbox[1])) / 2 - bbox[1]), a.text, font=f, fill=(240, 244, 248, 255))
    img.save(a.out)
    print(a.out)


def browserbar(a):
    img = Image.new("RGB", (a.w, a.h), (15, 23, 42))
    d = ImageDraw.Draw(img)
    bar_h = max(48, int(a.h * 0.085))
    d.rectangle([0, 0, a.w, bar_h], fill=(30, 41, 59))
    for i, color in enumerate(((239, 68, 68), (234, 179, 8), (34, 197, 94))):
        c = 24 + i * 30
        d.ellipse([c, bar_h // 2 - 7, c + 14, bar_h // 2 + 7], fill=color)
    field_x, field_w = 120, int(a.w * 0.62)
    d.rounded_rectangle([field_x, bar_h // 2 - 16, field_x + field_w, bar_h // 2 + 16],
                        radius=16, fill=(11, 18, 32))
    f = load_font(28)
    text = "https://" + a.url if not a.url.startswith("http") else a.url
    bbox = d.textbbox((0, 0), text, font=f)
    d.text((field_x + 24, bar_h // 2 - (bbox[3] - bbox[1]) / 2 - bbox[1]),
           text, font=f, fill=(203, 213, 225))
    img.save(a.out)
    print(a.out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="kind", required=True)
    pc = sub.add_parser("card")
    pc.add_argument("--text", required=True)
    pc.add_argument("--sub", default="")
    pc.add_argument("--w", type=int, default=1280)
    pc.add_argument("--h", type=int, default=720)
    pc.add_argument("--out", required=True)
    pcp = sub.add_parser("caption")
    pcp.add_argument("--text", required=True)
    pcp.add_argument("--w", type=int, default=1280)
    pcp.add_argument("--h", type=int, default=96)
    pcp.add_argument("--out", required=True)
    pbb = sub.add_parser("browserbar")
    pbb.add_argument("--url", required=True)
    pbb.add_argument("--w", type=int, default=1280)
    pbb.add_argument("--h", type=int, default=720)
    pbb.add_argument("--out", required=True)
    a = p.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    {"card": card, "caption": caption, "browserbar": browserbar}[a.kind](a)


if __name__ == "__main__":
    main()
