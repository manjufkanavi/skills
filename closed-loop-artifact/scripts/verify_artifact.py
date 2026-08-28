#!/usr/bin/env python3
"""Deterministic judge for the closed-loop-artifact loop (pixel-perfect upgrade).

The executing model runs a self-correcting loop (plan -> write artifact ->
render -> judge -> iterate). This script is the *judge step*: it scores an
artifact against a list of acceptance criteria using REAL rendered pixels
(for SVG/PNG) or substring matches (for text), so the model's own 0-1 scores
are anchored to ground truth instead of hand-waving.

Usage:
    python verify_artifact.py <artifact> --spec spec.json

spec.json (coordinates are in the SVG viewBox; the script scales them to
pixels). See references/pixel-perfect-plan.md for the full schema.

Criteria types (old kept for backward compatibility):
  - bars_increasing: ink bar heights strictly increasing left->right (0/0.5/1).
  - text_in_region: dark-pixel ratio in region [x0,y0,x1,y1] vs min_dark_ratio.
  - text_present: substring present in a doc (md/txt) artifact.

New deterministic assertions (all operate on real geometry + rendered pixels):
  - exact_rect:    element bbox matches spec {x,y,w,h} within tol px.
  - exact_circle:  circle (cx,cy,r) matches spec within tol px.
  - exact_path:    path area & bounds (shapely) match spec within tol.
  - proportion_ratio: element (or canvas) width/height matches expected ratio.
  - exact_color:   element fill color present (mass >= threshold) in its bbox.
  - text_ocr:      tesseract-OCR expected string(s) present (region optional).
  - text_position: OCR'd label center matches expected (x,y) within tol px.
  - overlap_free:  listed element geometries do not pairwise-intersect.
  - grid_alignment: every element coordinate snaps to the grid step.
  - pixel_diff:    SSIM vs a reference PNG (0..1, 1 == identical).

Exit code 0 when overall score >= threshold, else 1. A JSON report prints to
stdout. Requires cairosvg, Pillow, numpy, shapely, svgpath2mpl and the tesseract
binary (via pytesseract). Rasterizes SVG via cairosvg if available.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
INK_THRESHOLD = 160  # grayscale value below this counts as "ink"

# Small named-color map for exact_color fallbacks.
NAMED = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
    "green": (0, 128, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0),
    "orange": (255, 165, 0), "gray": (128, 128, 128), "grey": (128, 128, 128),
    "silver": (192, 192, 192), "maroon": (128, 0, 0), "navy": (0, 0, 128),
    "olive": (128, 128, 0), "purple": (128, 0, 128), "teal": (0, 128, 128),
    "aqua": (0, 255, 255), "cyan": (0, 255, 255), "lime": (0, 255, 0),
    "pink": (255, 192, 203), "brown": (165, 42, 41), "beige": (245, 245, 220),
    "tan": (210, 180, 140), "gold": (255, 215, 0), "coral": (255, 127, 80),
}


# --------------------------------------------------------------------------
# Geometry helpers (viewBox units -> pixels via rendered-image scale).
# --------------------------------------------------------------------------
def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _find_by_id(tree, element_id: str):
    if element_id is None:
        return None
    for el in tree.iter():
        if el.get("id") == element_id:
            return el
    return None


def _hex_to_rgb(c: str):
    c = c.strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    elif len(c) == 4:  # #RGB -> #RRGGBB (ignore alpha)
        c = "".join(ch * 2 for ch in c[:3])
    if len(c) == 6:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    if len(c) == 8:  # #RRGGBBAA
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return None


def resolve_fill(el):
    """Return the effective fill of an element (walk up for inheritance)."""
    cur = el
    while cur is not None:
        f = cur.get("fill")
        if f is not None and f.strip().lower() != "none":
            return f
        try:
            cur = cur.getparent()
        except Exception:
            break
    return "none"


def fill_rgb(fill):
    if fill is None:
        return None
    fill = fill.strip()
    if fill.lower() == "none":
        return None
    if fill.startswith("url("):
        return None  # gradient / pattern -> not a solid color
    if fill.startswith("#"):
        return _hex_to_rgb(fill)
    return NAMED.get(fill.lower())


def _path_geometry(d: str, viewbox):
    """Return (area, (minx,miny,maxx,maxy)) in viewBox units, or (0, None)."""
    if not d:
        return (0.0, None)
    try:
        from svgpath2mpl import parse_path
        p = parse_path(d)
        verts = [(float(vx), float(vy)) for vx, vy in p.vertices]
    except Exception:
        return (0.0, None)
    if len(verts) < 2:
        return (0.0, None)
    if len(verts) == 2:
        xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
        return (0.0, (min(xs), min(ys), max(xs), max(ys)))
    try:
        from shapely.geometry import Polygon
        poly = Polygon(verts)
        return (poly.area if poly.is_valid else 0.0, poly.bounds)
    except Exception:
        xs = [v[0] for v in verts]; ys = [v[1] for v in verts]
        return (0.0, (min(xs), min(ys), max(xs), max(ys)))


def _bbox_viewbox(el, viewbox):
    """Element bounding box in viewBox units, or None."""
    tag = _local(el.tag)
    if tag == "rect":
        x = float(el.get("x", 0.0)); y = float(el.get("y", 0.0))
        w = float(el.get("width", 0.0)); h = float(el.get("height", 0.0))
        return (x, y, x + w, y + h)
    if tag == "circle":
        cx = float(el.get("cx", 0.0)); cy = float(el.get("cy", 0.0))
        r = float(el.get("r", 0.0))
        return (cx - r, cy - r, cx + r, cy + r)
    if tag == "ellipse":
        cx = float(el.get("cx", 0.0)); cy = float(el.get("cy", 0.0))
        rx = float(el.get("rx", 0.0)); ry = float(el.get("ry", 0.0))
        return (cx - rx, cy - ry, cx + rx, cy + ry)
    if tag in ("polygon", "polyline"):
        pts = re.findall(r"[-+]?\d*\.?\d+", el.get("points", ""))
        nums = [float(z) for z in pts]
        if len(nums) >= 4:
            xs, ys = nums[0::2], nums[1::2]
            return (min(xs), min(ys), max(xs), max(ys))
    if tag == "path":
        return _path_geometry(el.get("d", ""), viewbox)[1]
    return None


def _el_bbox_pixels(el, viewbox, img):
    bb = _bbox_viewbox(el, viewbox)
    if bb is None:
        return None
    sx = img.width / viewbox[0] if viewbox and viewbox[0] else 1.0
    sy = img.height / viewbox[1] if viewbox and viewbox[1] else 1.0
    x0, y0, x1, y1 = bb
    return (x0 * sx, y0 * sy, x1 * sx, y1 * sy)


def _shapely_of(el, viewbox, img):
    """Return a shapely geometry (pixels) for an element, or None."""
    from shapely.geometry import Polygon, LineString
    tag = _local(el.tag)
    if tag == "path":
        d = el.get("d", "") or ""
        try:
            from svgpath2mpl import parse_path
            p = parse_path(d)
            sx = img.width / viewbox[0] if viewbox and viewbox[0] else 1.0
            sy = img.height / viewbox[1] if viewbox and viewbox[1] else 1.0
            verts = [(vx * sx, vy * sy) for vx, vy in p.vertices]
        except Exception:
            return None
        if len(verts) >= 3:
            return Polygon(verts)
        if len(verts) == 2:
            return LineString(verts).buffer(0.0)
        return None
    bb = _bbox_viewbox(el, viewbox)
    if bb is None:
        return None
    sx = img.width / viewbox[0] if viewbox and viewbox[0] else 1.0
    sy = img.height / viewbox[1] if viewbox and viewbox[1] else 1.0
    x0, y0, x1, y1 = bb[0] * sx, bb[1] * sy, bb[2] * sx, bb[3] * sy
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


# --------------------------------------------------------------------------
# Rendering / OCR.
# --------------------------------------------------------------------------
def rasterize(svg_path: Path, w: float, h: float) -> Path | None:
    try:
        from cairosvg import svg2png
    except Exception:
        return None
    out = svg_path.with_suffix(".png")
    try:
        svg2png(bytestring=svg_path.read_bytes(), write_to=str(out),
                output_width=int(w), output_height=int(h))
        return out
    except Exception:
        return None


def _ocr(im):
    """Return (full_text, [(word, x0, y0, x1, y1)]) using tesseract (top-left origin)."""
    import pytesseract
    try:
        if im.mode != "L":
            im = im.convert("L")
        data = pytesseract.image_to_data(im, output_type=pytesseract.Output.DICT)
        words = []
        n = len(data["text"])
        for i in range(n):
            t = (data["text"][i] or "").strip()
            x0 = int(data["left"][i]); y0 = int(data["top"][i])
            w = int(data["width"][i]); h = int(data["height"][i])
            if t:
                words.append((t, x0, y0, x0 + w, y0 + h))
        return pytesseract.image_to_string(im).strip(), words
    except Exception:
        return "", []


# --------------------------------------------------------------------------
# Color / similarity helpers.
# --------------------------------------------------------------------------
def _crop_rgb(im, region):
    from PIL import Image
    x0, y0, x1, y1 = region
    x0, y0, x1, y1 = int(x0), int(y0), int(max(x0 + 1, x1)), int(max(y0 + 1, y1))
    crop = im.crop((x0, y0, x1, y1)).convert("RGB")
    return crop.tobytes()


def color_mass(im, region, rgb, tol=64.0) -> float:
    if rgb is None:
        return 0.0
    data = _crop_rgb(im, region)
    if not data:
        return 0.0
    r0, g0, b0 = rgb
    hit = 0
    n = len(data) // 3
    for i in range(n):
        r = data[i * 3]; g = data[i * 3 + 1]; b = data[i * 3 + 2]
        if math.sqrt((r - r0) ** 2 + (g - g0) ** 2 + (b - b0) ** 2) <= tol:
            hit += 1
    return hit / n


def ssim_global(a: Path, b: Path) -> float:
    """Global SSIM approximation between two grayscale PNGs (downsampled)."""
    from PIL import Image
    import numpy as np
    def arr(p):
        im = Image.open(p).convert("L").resize((96, 96))
        return np.asarray(im, dtype=float)
    x = arr(a); y = arr(b)
    c1 = (0.01 * 255) ** 2; c2 = (0.03 * 255) ** 2
    mu_x = x.mean(); mu_y = y.mean()
    sx2 = x.var(); sy2 = y.var()
    cov = (x * y).mean() - mu_x * mu_y
    num = (2 * mu_x * mu_y + c1) * (2 * cov + c2)
    den = (mu_x ** 2 + mu_y ** 2 + c1) * (sx2 + sy2 + c2)
    if den == 0:
        return 0.0
    return float(min(1.0, max(0.0, num / den)))


# --------------------------------------------------------------------------
# New assertion handlers: each returns (score, detail).
# --------------------------------------------------------------------------
class _Ctx:
    def __init__(self, tree, img, viewbox):
        self.tree = tree
        self.img = img
        self.viewbox = viewbox

    def el(self, rid):
        return _find_by_id(self.tree, rid)

    def bbox(self, rid):
        return _el_bbox_pixels(self.el(rid), self.viewbox, self.img)

    def fill_rgb(self, rid):
        el = self.el(rid)
        return fill_rgb(resolve_fill(el)) if el else None


def _f(c, *names, default=None):
    for n in names:
        if n in c:
            return c[n]
    return default


def _exact_rect(c, ctx, tol):
    el = ctx.el(c.get("ref"))
    if el is None:
        return 0.0, f"element #{c.get('ref')} not found"
    rect = _f(c, "rect", "box") or c.get("rect")
    bbox = ctx.bbox(c.get("ref"))
    if rect is None or bbox is None:
        return 0.0, "missing rect spec or element geometry"
    sx = ctx.img.width / ctx.viewbox[0] if ctx.viewbox[0] else 1.0
    sy = ctx.img.height / ctx.viewbox[1] if ctx.viewbox[1] else 1.0
    x0, y0, x1, y1 = (float(rect[0]) * sx, float(rect[1]) * sy,
                      float(rect[2]) * sx, float(rect[3]) * sy)
    ew, eh = x1 - x0, y1 - y0
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    dx = abs(bbox[0] - x0); dy = abs(bbox[1] - y0)
    dw, dh = abs(bw - ew), abs(bh - eh)
    err = max(dx / tol, dy / tol, dw / tol, dh / tol) if tol > 0 else 0.0
    return (max(0.0, 1.0 - err),
            f"bbox=({bbox[0]:.0f},{bbox[1]:.0f},{bw:.0f}x{bh:.0f}) "
            f"spec=({rect[0]},{rect[1]},{rect[2]-rect[0]}x{rect[3]-rect[1]}) tol={tol}")


def _exact_circle(c, ctx, tol):
    el = ctx.el(c.get("ref"))
    if el is None:
        return 0.0, f"element #{c.get('ref')} not found"
    spec = _f(c, "circle", "params")
    if not spec:
        return 0.0, "missing circle spec {cx,cy,r}"
    cx, cy, r = spec["cx"], spec["cy"], spec["r"]
    bb = _bbox_viewbox(el, ctx.viewbox)
    if bb is None:
        return 0.0, "element is not a circle"
    sx = ctx.img.width / ctx.viewbox[0] if ctx.viewbox[0] else 1.0
    dcx = abs((cx - r) - bb[0]) / tol + abs((cx + r) - bb[2]) / tol
    dcy = abs((cy - r) - bb[1]) / tol + abs((cy + r) - bb[3]) / tol
    err = (dcx + dcy) / 4.0
    return (max(0.0, 1.0 - err), f"spec=({cx},{cy},{r}) measured=({bb[0]:.0f},{bb[1]:.0f},{bb[2]:.0f},{bb[3]:.0f})")


def _exact_path(c, ctx, tol):
    el = ctx.el(c.get("ref"))
    if el is None:
        return 0.0, f"element #{c.get('ref')} not found"
    area_exp = c.get("area"); bounds_exp = c.get("bounds")
    area, bounds = _path_geometry(el.get("d", ""), ctx.viewbox)
    if bounds is None:
        return 0.0, "path has no geometry"
    sx = ctx.img.width / ctx.viewbox[0] if ctx.viewbox[0] else 1.0
    sy = ctx.img.height / ctx.viewbox[1] if ctx.viewbox[1] else 1.0
    b0, b1, b2, b3 = bounds
    measured_bounds = (b0 * sx, b1 * sy, b2 * sx, b3 * sy)
    detail = f"area={area:.0f} bounds=({b0:.0f},{b1:.0f},{b2:.0f},{b3:.0f})"
    if area_exp is not None:
        err = abs(area - area_exp) / max(abs(area_exp), 1.0)
        return (max(0.0, 1.0 - err), f"{detail} area_spec={area_exp}")
    if bounds_exp is not None:
        x0, y0, x1, y1 = bounds_exp
        err = max(abs(measured_bounds[0] - x0), abs(measured_bounds[2] - x1),
                  abs(measured_bounds[1] - y0), abs(measured_bounds[3] - y1)) / tol
        return (max(0.0, 1.0 - err), f"{detail} bounds_spec=({x0},{y0},{x1},{y1})")
    return (max(0.0, 1.0 - abs(area - (area_exp or area)) / max(abs(area_exp or area), 1.0)), detail)


def _proportion_ratio(c, ctx, tol):
    ref = c.get("ref")
    if ref and ref != "canvas":
        bbox = ctx.bbox(ref)
        if bbox is None:
            return 0.0, f"element #{ref} has no bbox"
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    else:
        w, h = ctx.viewbox[0], ctx.viewbox[1]
    ratio = w / h if h else 0.0
    expected = c.get("ratio", c.get("target"))
    if expected is None:
        return 0.0, "missing ratio"
    err = abs(ratio - expected) / expected
    return (max(0.0, 1.0 - err), f"ratio={ratio:.3f} expected={expected}")


def _exact_color(c, ctx, tol):
    ref = c.get("ref")
    region = None
    if ref:
        region = ctx.bbox(ref)
    elif "region" in c:
        vb = ctx.viewbox
        sx = ctx.img.width / vb[0] if vb else 1.0
        sy = ctx.img.height / vb[1] if vb else 1.0
        x0, y0, x1, y1 = c["region"]
        region = (x0 * sx, y0 * sy, x1 * sx, y1 * sy)
    if region is None:
        return 0.0, "exact_color needs ref or region"
    rgb = fill_rgb(resolve_fill(ctx.el(ref))) if ref else _hex_to_rgb(c.get("color", "#000000"))
    thr = c.get("threshold", 0.02)
    mass = color_mass(ctx.img, region, rgb, tol=c.get("tol_color", 64.0))
    return (min(1.0, mass / thr) if thr > 0 else 0.0,
            f"color=#{rgb} mass={mass:.3f} thr={thr} region=({region[0]:.0f},{region[1]:.0f},{region[2]:.0f},{region[3]:.0f})")


def _text_ocr(c, ctx, tol):
    expect = c.get("expect")
    if isinstance(expect, str):
        expect = [expect]
    elif not isinstance(expect, list):
        return 0.0, "text_ocr needs 'expect' (string or list)"
    text, words = _ocr(ctx.img)
    region_spec = c.get("region")
    if region_spec:
        vb = ctx.viewbox
        sx = ctx.img.width / vb[0] if vb else 1.0
        sy = ctx.img.height / vb[1] if vb else 1.0
        x0, y0, x1, y1 = region_spec
        box = [(t, a, b, d, bb) for (t, a, b, d, bb) in words
               if x0 * sx <= a and d <= x1 * sx and y0 * sy <= b and bb <= y1 * sy]
    else:
        box = words
    found = 0
    for s in expect:
        if any(s.lower() in t.lower() for (t, *_a) in box) or any(s.lower() == t.lower() for (t, *_a) in box):
            found += 1
    score = found / len(expect)
    detail = f"found {found}/{len(expect)}: {[t for t, *_a in box][:8]}"
    return (score, detail)


def _text_position(c, ctx, tol):
    label = c.get("expect")
    expected = c.get("at") or c.get("point")
    if not (isinstance(expected, (list, tuple)) and len(expected) >= 2):
        return 0.0, "text_position needs 'at' [x,y] and 'expect' label"
    _, words = _ocr(ctx.img)
    vb = ctx.viewbox
    sx = ctx.img.width / vb[0] if vb else 1.0
    sy = ctx.img.height / vb[1] if vb else 1.0
    match = [w for w in words if label.lower() in w[0].lower()]
    if not match:
        return 0.0, f"OCR found no label '{label}'"
    x0, y0, x1, y1 = match[0][1:5]
    cx, cy = (x0 + x1) / 2.0 / sx, (y0 + y1) / 2.0 / sy
    ex, ey = expected[0], expected[1]
    err = math.sqrt((cx - ex) ** 2 + (cy - ey) ** 2) / tol
    return (max(0.0, 1.0 - err), f"OCR({cx:.0f},{cy:.0f}) spec=({ex},{ey}) err={err:.2f}tol")


def _overlap_free(c, ctx, tol):
    from shapely.geometry import Polygon
    ids = c.get("elements") or c.get("ref")
    if not isinstance(ids, list):
        return 0.0, "overlap_free needs 'elements': [ids]"
    geoms = []
    for rid in ids:
        e = ctx.el(rid)
        if e is None:
            continue
        bb = _bbox_viewbox(e, ctx.viewbox)
        if bb is None:
            continue
        sx = ctx.img.width / ctx.viewbox[0] if ctx.viewbox and ctx.viewbox[0] else 1.0
        sy = ctx.img.height / ctx.viewbox[1] if ctx.viewbox and ctx.viewbox[1] else 1.0
        x0, y0, x1, y1 = bb[0] * sx, bb[1] * sy, bb[2] * sx, bb[3] * sy
        g = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        if not g.is_empty:
            geoms.append((rid, g))
    if len(geoms) < 2:
        return 0.0, "need >=2 elements with geometry"
    tol_area = tol * tol
    total = overlap = 0
    for i in range(len(geoms)):
        for j in range(i + 1, len(geoms)):
            total += 1
            inter = geoms[i][1].intersection(geoms[j][1])
            if not inter.is_empty and inter.area > min(1.0, tol_area):
                overlap += 1
    return (1.0 - overlap / total if total else 0.0,
            f"{total} pairs, {overlap} overlapping")


def _grid_alignment(c, ctx, tol):
    step = c.get("step", c.get("grid"))
    if not step:
        return 0.0, "grid_alignment needs 'step'"
    step = float(step)
    ids = c.get("elements") or c.get("ref")
    coords = []
    if isinstance(ids, list):
        for rid in ids:
            el = ctx.el(rid)
            if el is None:
                continue
            bbox = _bbox_viewbox(el, ctx.viewbox)
            if bbox:
                coords.extend(bbox)
            area, bounds = _path_geometry(el.get("d", ""), ctx.viewbox)
            if bounds:
                coords.extend(bounds)
    else:
        for el in ctx.tree.iter():
            bbox = _bbox_viewbox(el, ctx.viewbox)
            if bbox:
                coords.extend(bbox)
    if not coords:
        return 0.0, "no coordinates to check"
    snapped = sum(1 for v in coords if abs(v % step) < tol or abs(v % step - step) < tol)
    return (snapped / len(coords), f"{snapped}/{len(coords)} coords on {step}px grid")


def _pixel_diff(c, ctx, tol):
    from PIL import Image as _Image
    ref = Path(c.get("reference", ""))
    if not ref or not ref.exists():
        return 0.0, f"reference {c.get('reference')} not found"
    tmp = ref.with_suffix(".current" + ref.suffix)
    ctx.img.save(str(tmp))
    s = ssim_global(tmp, ref)
    return (s, f"SSIM={s:.3f}")


_NEW_HANDLERS = {
    "exact_rect": _exact_rect, "exact_circle": _exact_circle, "exact_path": _exact_path,
    "proportion_ratio": _proportion_ratio, "exact_color": _exact_color,
    "text_ocr": _text_ocr, "text_position": _text_position, "overlap_free": _overlap_free,
    "grid_alignment": _grid_alignment, "pixel_diff": _pixel_diff,
}


# --------------------------------------------------------------------------
# Orchestration.
# --------------------------------------------------------------------------
def _parse_svg_tree(svg_path: Path):
    try:
        return ET.parse(str(svg_path))
    except Exception:
        return None


def run(artifact: Path, spec: dict) -> dict:
    threshold = float(spec.get("threshold", 0.8))
    tol = float(spec.get("tol", 4.0))
    viewbox = load_viewbox(spec)
    criteria = spec.get("criteria", [])
    svg_tree = _parse_svg_tree(artifact) if artifact.suffix.lower() == ".svg" else None

    # Render SVG -> PNG once for pixel/OCR-based criteria.
    from PIL import Image as _Image
    img = load_image(artifact, viewbox)
    if svg_tree is not None and not isinstance(img, _Image.Image) and viewbox:
        png = rasterize(artifact, viewbox[0], viewbox[1])
        if png:
            img = _Image.open(png).convert("L")

    ctx = _Ctx(svg_tree, img, viewbox) if (svg_tree is not None and img is not None) else None

    text = open_text(artifact) if artifact.suffix.lower() in (".md", ".txt") else None

    results = []
    for c in criteria:
        t = c["type"]
        if ctx is None:
            results.append({"name": c.get("name", t), "type": t, "score": 0.0,
                            "detail": "no rendered image (svg parse/rasterize failed)"})
            continue
        if t in _NEW_HANDLERS:
            s, detail = _NEW_HANDLERS[t](c, ctx, tol)
        elif t == "bars_increasing" and img is not None:
            s = bars_increasing(img, viewbox)
            detail = round(s, 3)
        elif t == "text_in_region" and img is not None:
            region = scale_region(c["region"], viewbox, img)
            s = score_text_in_region(img, region, c.get("min_dark_ratio", 0.02))
            detail = round(s, 3)
        elif t == "text_present" and text is not None:
            s = 1.0 if c.get("substring", "") in text else 0.0
            detail = round(s, 3)
        else:
            s, detail = 0.0, f"unknown type '{t}'"
        results.append({"name": c.get("name", t), "type": t,
                        "score": round(float(s), 3), "detail": detail})

    overall = round(sum(x["score"] for x in results) / len(results), 3) if results else 0.0
    return {
        "artifact": str(artifact),
        "threshold": threshold,
        "overall_score": overall,
        "passed": overall >= threshold,
        "criteria": results,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Deterministic judge for the closed-loop-artifact loop.")
    ap.add_argument("artifact", help="path to the artifact (svg, png, md, or txt)")
    ap.add_argument("--spec", required=True, help="path to a JSON spec file")
    args = ap.parse_args()

    artifact = Path(args.artifact)
    if not artifact.exists():
        print(f"error: {artifact} not found", file=sys.stderr)
        sys.exit(2)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    report = run(artifact, spec)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] else 1)


# (invocation moved to the END of the file so all helper functions, including
#  the backward-compat ones below, are defined before main() runs)


# --------------------------------------------------------------------------
# Backward-compat helpers (kept for the old criteria).
# --------------------------------------------------------------------------
def load_viewbox(spec: dict):
    vb = spec.get("viewBox")
    if not vb:
        return None
    m = re.match(r"[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)", vb)
    return (float(m.group(1)), float(m.group(2))) if m else None


def load_image(artifact: Path, viewbox):
    from PIL import Image
    ext = artifact.suffix.lower()
    if ext == ".svg" and viewbox:
        png = rasterize(artifact, viewbox[0], viewbox[1])
        if png:
            return Image.open(png).convert("RGB")
        return None
    if ext in (".png", ".jpg", ".jpeg", ".webp"):
        return Image.open(artifact).convert("RGB")
    return None


def open_text(artifact: Path) -> str:
    return artifact.read_text(encoding="utf-8", errors="replace")


def scale_region(region, viewbox, img):
    if not viewbox:
        return (int(region[0]), int(region[1]), int(region[2]), int(region[3]))
    sx = img.width / viewbox[0]
    sy = img.height / viewbox[1]
    return (int(region[0] * sx), int(region[1] * sy), int(region[2] * sx), int(region[3] * sy))


def region_dark_ratio(im, region):
    im = im.convert("L")
    x0, y0, x1, y1 = region
    crop = im.crop((int(x0), int(y0), int(x1), int(y1)))
    px = list(crop.getdata())
    if not px:
        return 0.0
    dark = sum(1 for v in px if v < INK_THRESHOLD)
    return dark / len(px)


def score_text_in_region(im, region, min_ratio):
    ratio = region_dark_ratio(im, region)
    if ratio <= 0:
        return 0.0
    return min(1.0, ratio / min_ratio)


def bars_increasing(im, viewbox):
    im = im.convert("L")
    w, h = viewbox or (400.0, 300.0)
    y_lo, y_hi = 0.20 * h, 0.85 * h
    heights = []
    for x in range(int(w)):
        ink_top = None
        for y in range(int(y_lo), int(y_hi)):
            if im.getpixel((x, y)) < INK_THRESHOLD:
                ink_top = float(y)
                break
        if ink_top is not None:
            heights.append(y_hi - ink_top)
    heights = [hh for hh in heights if hh > 0.05 * h]
    if len(heights) < 2:
        return 0.0
    return 1.0 if all(heights[i] < heights[i + 1] for i in range(len(heights) - 1)) else 0.5


if __name__ == "__main__":
    main()
