"""Design + content extraction from a source resume PDF (programmatic, no vision).

Usage: python extract_design.py <resume.pdf> [--out <dir>]

Prints: page geometry, font/size/color usage, vector shape inventory,
writes 2x rendered PNGs, and pixel-scans the mid-page line for exact
panel/bar colors. Feed the printed values into design-tokens.css.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = Path(args.out or (Path(args.pdf).parent / "extract"))
    out.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(args.pdf)
    print(f"pages={doc.page_count}")
    for i, page in enumerate(doc):
        r = page.rect
        print(f"page{i} rect=({r.width:.1f}x{r.height:.1f})")

        fonts, sizes, colors = Counter(), Counter(), Counter()
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    fonts[s["font"]] += 1
                    sizes[round(s["size"], 1)] += 1
                    c = s["color"]
                    colors[f"#{(c >> 16) & 255:02x}{(c >> 8) & 255:02x}{c & 255:02x}"] += 1
        print(f"page{i} fonts: {dict(fonts.most_common(4))}")
        print(f"page{i} sizes: {dict(sorted(sizes.items(), key=lambda kv: -kv[1])[:8])}")
        print(f"page{i} colors: {dict(colors.most_common(10))}")

        fills, strokes = Counter(), Counter()
        for d in page.get_drawings():
            if d.get("fill"):
                f = d["fill"]
                fills[f"#{int(f[0]*255):02x}{int(f[1]*255):02x}{int(f[2]*255):02x}"] += 1
            if d.get("color"):
                c = d["color"]
                strokes[f"#{int(c[0]*255):02x}{int(c[1]*255):02x}{int(c[2]*255):02x}"] += 1
        print(f"page{i} fills: {dict(fills.most_common(8))}")
        print(f"page{i} strokes: {dict(strokes.most_common(8))}")

        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x render
        png = out / f"page_{i}.png"
        pix.save(png)
        print(f"page{i} render: {png} ({pix.width}x{pix.height})")

    if HAS_PIL:
        # Color runs across the mid-page line: finds panel fills / accent bars.
        for i in range(doc.page_count):
            im = Image.open(out / f"page_{i}.png").convert("RGB")
            w, h = im.size
            y = h // 2
            prev, runs = None, []
            for x in range(w):
                px = im.getpixel((x, y))
                if px != prev:
                    runs.append((x, "#%02x%02x%02x" % px))
                    prev = px
            print(f"page{i} y-mid runs (x>=200, first 12): {[(x, c) for x, c in runs if x >= 200][:12]}")
    else:
        print("(PIL not available - pixel sampling skipped; install pillow)")

    doc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
