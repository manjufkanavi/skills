#!/usr/bin/env python3
"""Design ground-truth dump for a PDF (resume rebuild workflow).

Usage: reverse-engineer.py <input.pdf> [page_index ...]

Prints per page: page rect, every text span (x,y,w,h | size | B/R | hex | text),
every vector drawing fill/stroke, then font / font-size / weighted-color census.
This is the ground truth to build design tokens from — pair with a 2x PNG render
+ PIL pixel sampling to resolve ambiguous fills (clip rings, hairlines).
"""
import sys
import collections

try:
    import fitz
except ImportError:
    sys.exit("pymupdf is required: uv pip install pymupdf")


def hx(c):
    if c is None:
        return None
    return "#%02x%02x%02x" % tuple(int(round(x * 255)) for x in c)


def main():
    src = sys.argv[1]
    doc = fitz.open(src)
    pages = [int(a) for a in sys.argv[2:]] or list(range(doc.page_count))
    fonts, sizes, colors = collections.Counter(), collections.Counter(), collections.Counter()
    for i in pages:
        page = doc[i]
        print(f"\n{'=' * 70}\nPAGE {i}  rect={page.rect}\n{'=' * 70}")
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        print(f"rendered 2x: {pix.width}x{pix.height}")
        for f in page.get_fonts(full=True):
            fonts[(f[2], f[3], f[4])] += 1
        for dr in page.get_drawings():
            r = dr["rect"]
            fill, stroke = hx(dr.get("fill")), hx(dr.get("stroke"))
            if fill or stroke:
                print(f"  draw fill={fill} stroke={stroke} w={dr.get('width')} "
                      f"rect=({r.x0:.1f},{r.y0:.1f},{r.x1:.1f},{r.y1:.1f}) {r.width:.1f}x{r.height:.1f}")
                if fill:
                    colors[fill] += 1
                if stroke:
                    colors[stroke + "(stroke)"] += 1
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    if not s["text"].strip():
                        continue
                    c = s.get("color", 0)
                    hexc = "#%02x%02x%02x" % ((c >> 16) & 255, (c >> 8) & 255, c & 255)
                    bold = "B" if "Bold" in s.get("font", "") else "R"
                    colors[hexc] += len(s["text"])
                    sizes[round(s.get("size", 0), 1)] += 1
                    x0, y0, x1, y1 = s["bbox"]
                    print(f"  span ({x0:6.1f},{y0:6.1f}) {x1 - x0:6.1f}x{y1 - y0:5.1f} "
                          f"sz={s.get('size', 0):5.1f} {bold} {hexc}  {s['text'][:80]}")
    print("\n================ FONTS ================")
    for k, v in fonts.most_common():
        print(f"  {v:3d}  {k}")
    print("\n================ SIZES ================")
    for k, v in sorted(sizes.items()):
        print(f"  {k}: {v}")
    print("\n================ COLORS (weighted) ================")
    for k, v in colors.most_common(25):
        print(f"  {v:6d}  {k}")


if __name__ == "__main__":
    main()
