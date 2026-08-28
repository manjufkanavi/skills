#!/usr/bin/env python3
"""svgwrite_adapter.py -- Phase 0 structured-generation adapter.

Converts a *structured intent* (a JSON shape list) into an exact <svg> element
using svgwrite. No hand-crafted SVG -> no coordinate drift.

This is the "generate" step of the improved loop:

    plan(structured intent) -> generate(svgwrite) -> render(cairosvg)
        -> judge(verify_artifact.py) -> critique(model) -> regenerate

Usage:
    python3 svgwrite_adapter.py intent.json --out out.svg
    cat intent.json | python3 svgwrite_adapter.py - --out out.svg

Intent schema (see references/pixel-perfect-svg.md, Phase 0):
{
  "viewBox": "0 0 800 600",
  "shapes": [
    {"type":"rect","id":"sky","x":0,"y":0,"width":800,"height":360,"fill":"#2b2d42"},
    {"type":"circle","id":"sun","cx":620,"cy":150,"r":72,"fill":"#ffb703"},
    {"type":"ellipse","id":"cloud","cx":200,"cy":120,"rx":70,"ry":30,"fill":"white"},
    {"type":"line","id":"horizon","x1":0,"y1":360,"x2":800,"y2":360,"stroke":"#000","stroke-width":1},
    {"type":"polygon","id":"sail","points":"100,300 160,300 160,220"},
    {"type":"path","id":"cat","d":"M50,300 ... Z","fill":"#1d3557"},
    {"type":"text","id":"title","x":400,"y":40,"size":28,"text":"Beach","text-anchor":"middle",
     "fill":"#ffffff","dominant-baseline":"middle"}
  ]
}

Only the attributes the loop cares about are required; everything else is passed
through untouched. Unknown "type" values raise a clear error instead of emitting
broken SVG.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import svgwrite
except Exception as e:  # noqa: BLE001
    print("svgwrite not available:", e, file=sys.stderr)
    sys.exit(2)


def _num(v, default=0.0):
    """Coerce a value to float, tolerating strings / None."""
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _attrs(shape: dict) -> dict:
    """Pull common presentation attributes out of a shape dict."""
    out = {}
    for k in ("id", "fill", "stroke", "stroke-width", "stroke-width",
               "opacity", "opacity", "display", "visibility", "transform"):
        if k in shape and shape[k] is not None:
            out[k] = shape[k]
    return out


def _add_text(dw, group, shape):
    dw_text = dw.text(
        shape.get("text", shape.get("label", "")),
        ( _num(shape.get("x")), _num(shape.get("y"))),
        font_size=_num(shape.get("size", shape.get("font-size", 16))),
    )
    for k in ("fill", "text-anchor", "dominant-baseline", "font-weight",
              "font-style", "opacity"):
        if k in shape and shape[k] is not None:
            dw_text[k] = shape[k]
    group.add(dw_text)


def _build_group(intent: dict) -> str:
    """Build shapes into a Drawing and return the final SVG *string* with the
    viewBox injected into the root tag (this svgwrite version does not emit it)."""
    viewBox = intent.get("viewBox", "0 0 800 600")
    dw = svgwrite.Drawing()
    if "width" in intent or "height" in intent:
        if "width" in intent:
            dw.set("width", str(_num(intent.get("width"), 800)))
        if "height" in intent:
            dw.set("height", str(_num(intent.get("height"), 600)))
    group = dw
    for shape in intent.get("shapes", []):
        t = (shape.get("type") or "").lower()
        sid = shape.get("id")
        a = _attrs(shape)
        if t == "rect":
            group.add(dw.rect(
                insert=(_num(shape.get("x")), _num(shape.get("y"))),
                size=(_num(shape.get("width"), 0), _num(shape.get("height"), 0)),
                **a))
        elif t == "circle":
            group.add(dw.circle(
                center=(_num(shape.get("cx")), _num(shape.get("cy"))),
                r=_num(shape.get("r", 0)), **a))
        elif t == "ellipse":
            group.add(dw.ellipse(
                center=(_num(shape.get("cx")), _num(shape.get("cy"))),
                rx=_num(shape.get("rx", 0)), ry=_num(shape.get("ry", 0)), **a))
        elif t == "line":
            group.add(dw.line(
                start=(_num(shape.get("x1")), _num(shape.get("y1"))),
                end=(_num(shape.get("x2")), _num(shape.get("y2"))), **a))
        elif t == "polygon":
            group.add(dw.polygon(_num_points(shape.get("points")), **a))
        elif t == "polyline":
            group.add(dw.polyline(_num_points(shape.get("points")), **a))
        elif t == "path":
            group.add(dw.path(d=shape.get("d", ""), **a))
        elif t == "text":
            _add_text(dw, group, shape)
        else:
            raise ValueError(f"unknown shape type {t!r} in shape {sid!r}")
    svg = dw.tostring()
    defs = _build_gradients(intent)
    if defs:
        if "<defs />" in svg:
            svg = svg.replace("<defs />", defs, 1)
        else:
            svg = re.sub(r"</svg>", f"{defs}</svg>", svg, count=1)
    return _inject_viewbox(svg, viewBox)


def _num_points(points):
    """Parse a points string / list into [(x,y), ...]."""
    if isinstance(points, (list, tuple)):
        return [(float(points[i]), float(points[i + 1]))
                for i in range(0, len(points) - 1, 2)]
    nums = [float(z) for z in re.findall(r"[-+]?[0-9]*\.?[0-9]+", points or "")]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


def _build_gradients(intent: dict) -> str:
    """Build <linearGradient>/<radialGradient> definitions from a top-level
    ``gradients`` key. Each gradient: {id, type: linear|radial, stops:[{offset,color,opacity}]}.
    Offsets 0..1 are normalised to percentages. Shapes reference a gradient via
    ``fill: "url(#id)"``."""
    grads = intent.get("gradients") or []
    if not grads:
        return ""
    parts = []
    for g in grads:
        gid = g.get("id")
        if not gid:
            continue
        gt = (g.get("type") or "linear").lower()
        if gt == "radial":
            cx, cy, r = _num(g.get("cx", 0.5)), _num(g.get("cy", 0.5)), _num(g.get("r", 0.5))
            fx = _num(g.get("fx", cx)); fy = _num(g.get("fy", cy))
            tag = f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}" fx="{fx}" fy="{fy}">'
        else:
            tag = f'<linearGradient id="{gid}" x1="{_num(g.get("x1", 0))}" ' \
                  f'y1="{_num(g.get("y1", 0))}" x2="{_num(g.get("x2", 0))}" ' \
                  f'y2="{_num(g.get("y2", 1))}">'
        stops = g.get("stops", [])
        for s in stops:
            off = _num(s.get("offset", 0.0))
            offp = f"{off * 100:.0f}%" if 0.0 <= off <= 1.0 else f"{off:.0f}%"
            stop = f'<stop offset="{offp}" stop-color="{s.get("color", "#000000")}">'
            if s.get("opacity") is not None:
                stop += f' stop-opacity="{_num(s.get("opacity"), 1.0)}"'
            stop += "</stop>"
            tag += stop
        parts.append(f"{tag}</{gt}Gradient>")
    return "<defs>" + "".join(parts) + "</defs>"


def _inject_viewbox(svg: str, viewBox: str) -> str:
    """This svgwrite version stores viewBox but does not emit it; inject it
    into the root <svg> tag so the renderer/judge see the real dimensions."""
    if not viewBox:
        return svg

    def _repl(m):
        inner = m.group(2)
        if "viewBox=" in inner:
            return m.group(0)
        return '%s viewBox="%s"%s>' % (m.group(1), viewBox, inner)

    return re.sub(r"(<svg\b)(\s[^>]*?)>", _repl, svg, count=1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Structured intent (JSON) -> SVG via svgwrite.")
    ap.add_argument("intent", help="path to intent.json, or '-' for stdin")
    ap.add_argument("--out", "-o", default="-", help="output .svg path, or '-' for stdout")
    args = ap.parse_args()

    src = sys.stdin.read() if args.intent == "-" else Path(args.intent).read_text(encoding="utf-8")
    intent = json.loads(src)
    if "shapes" not in intent:
        print("error: intent needs a top-level 'shapes' array", file=sys.stderr)
        sys.exit(2)

    dw = _build_group(intent)
    svg = dw if isinstance(dw, str) else dw.tostring()

    if args.out == "-":
        sys.stdout.write(svg)
    else:
        Path(args.out).write_text(svg, encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
