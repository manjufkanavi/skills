#!/usr/bin/env python3
"""spec_to_svg.py -- Phase 0 spec->SVG converter.

Reads a judge spec.json (the exact format consumed by
`verify_artifact.py`) and emits:
  1. a *structured intent* JSON (--emit-intent writes intent.json), and
  2. an <svg> file, via the svgwrite adapter.

Geometry is synthesised from each criterion's own parameters
(rect/circle/ellipse/path/bounds/text) so the judge's criteria *define* the
shapes; an explicit top-level "shapes" list in the spec overrides synthesis.

Usage:
    python3 spec_to_svg.py spec.json --out out.svg
    python3 spec_to_svg.py spec.json --emit-intent intent.json --out out.svg

The emitted intent can be re-run through svgwrite_adapter.py, and the SVG can
be judged by verify_artifact.py -- closing the plan->generate->render->judge loop.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent

try:
    import svgwrite  # noqa: F401  (import to confirm availability)
except Exception as e:  # noqa: BLE001
    print("svgwrite not available:", e, file=sys.stderr)
    sys.exit(2)


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _num_points(points):
    if isinstance(points, (list, tuple)):
        return [(float(points[i]), float(points[i + 1]))
                for i in range(0, len(points) - 1, 2)]
    nums = [float(z) for z in re.findall(r"[-+]?[0-9]*\.?[0-9]+", points or "")]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


def _points_str(pts):
    return " ".join(f"{x},{y}" for x, y in pts)


def spec_to_intent(spec: dict) -> dict:
    """Turn a judge spec.json into a structured-intent dict.

    If the spec carries an explicit top-level "shapes" list, it is used as-is.
    Otherwise shapes are synthesised from each criterion's geometry.
    """
    if "shapes" in spec and spec["shapes"]:
        return {"viewBox": spec.get("viewBox", "0 0 800 600"), "shapes": spec["shapes"]}

    shapes = []
    seen = set()

    def _fill_of(c):
        return c.get("fill") or c.get("color")

    for c in spec.get("criteria", []):
        t = c.get("type")
        ref = c.get("ref")
        fill = _fill_of(c)
        if t == "exact_rect":
            r = c.get("rect", c.get("box")) or c.get("rect")
            if r:
                shapes.append({"type": "rect", "id": ref, "x": r[0], "y": r[1],
                               "width": r[2] - r[0], "height": r[3] - r[1], "fill": fill})
                seen.add(ref)
        elif t == "exact_circle":
            p = c.get("circle", c.get("params")) or {}
            if p:
                shapes.append({"type": "circle", "id": ref, "cx": p["cx"], "cy": p["cy"],
                               "r": p["r"], "fill": fill})
                seen.add(ref)
        elif t == "exact_ellipse":
            p = c.get("ellipse", c.get("params")) or {}
            if p:
                shapes.append({"type": "ellipse", "id": ref, "cx": p["cx"], "cy": p["cy"],
                               "rx": p["rx"], "ry": p["ry"], "fill": fill})
                seen.add(ref)
        elif t == "exact_path":
            d = c.get("d")
            if d:
                shapes.append({"type": "path", "id": ref, "d": d, "fill": fill})
            else:
                b = c.get("bounds")
                if b:
                    x0, y0, x1, y1 = b
                    pts = _points_str([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
                    shapes.append({"type": "polygon", "id": ref, "points": pts, "fill": fill})
            seen.add(ref)
        elif t == "text_ocr":
            expect = c.get("expect")
            if isinstance(expect, list):
                expect = expect[0] if expect else ""
            at = c.get("at") or c.get("point")
            x = at[0] if isinstance(at, (list, tuple)) and at else 0
            y = (at[1] if isinstance(at, (list, tuple)) and len(at) > 1 else 20)
            shapes.append({"type": "text", "id": ref, "x": x, "y": y,
                           "size": c.get("size", 24), "text": expect, "fill": fill})
            seen.add(ref)
        elif t == "exact_color":
            # color-only constraint: attach fill to an already-declared shape.
            for s in shapes:
                if s.get("id") == ref and fill:
                    s["fill"] = fill
        # proportion_ratio / grid_alignment / overlap_free / pixel_diff:
        #   judge-only -> no shape emitted.
    return {"viewBox": spec.get("viewBox", "0 0 800 600"), "shapes": shapes}


def write_svg(intent: dict, out: str) -> None:
    """Build the SVG in-process via the adapter's _build_group."""
    import svgwrite_adapter
    svg = svgwrite_adapter._build_group(intent)
    if not isinstance(svg, str):  # pragma: no cover - defensive
        svg = svg.tostring()
    Path(out).write_text(svg, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="spec.json (judge format) -> structured intent + SVG.")
    ap.add_argument("spec", help="path to spec.json")
    ap.add_argument("--out", "-o", default="out.svg")
    ap.add_argument("--emit-intent", default="", help="write the structured intent here")
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    intent = spec_to_intent(spec)

    if args.emit_intent:
        Path(args.emit_intent).write_text(json.dumps(intent, indent=2), encoding="utf-8")
        print(f"wrote intent -> {args.emit_intent}")

    write_svg(intent, args.out)
    print(f"wrote {args.out}  ({len(intent['shapes'])} shapes)")


if __name__ == "__main__":
    main()
