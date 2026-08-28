# Judge spec schema + the `_overlap_free` stale-global-binding fix

Session detail for `scripts/verify_artifact.py` (the deterministic judge).

## Working `spec.json` schema per new criterion
Coordinates are in the SVG `viewBox`; the judge scales them to pixels.

| Criterion | Required spec keys | Example |
|---|---|---|
| `exact_rect` | `rect:[x0,y0,x1,y1]` + `ref` (element id) | `{"type":"exact_rect","ref":"red","rect":[80,120,320,280],"tol":6}` |
| `exact_circle` | `circle:{cx,cy,r}` + `ref` | `{"type":"exact_circle","ref":"c","circle":{"cx":620,"cy":300,"r":100}}` |
| `exact_color` | `ref` + `tol_color` + `threshold` | `{"type":"exact_color","ref":"red","tol_color":64,"threshold":0.1}` |
| `text_ocr` | `expect` (+ optional `region:[x0,y0,x1,y1]`) | `{"type":"text_ocr","expect":"Hello","region":[0,430,400,600]}` |
| `proportion_ratio` | `ratio` | `{"type":"proportion_ratio","ratio":1.333}` |
| `overlap_free` | `elements:[ids]` | `{"type":"overlap_free","elements":["red","c"]}` |
| `grid_alignment` | `step` | `{"type":"grid_alignment","step":10}` |

Notes: `exact_rect` reads `rect` as an **array** `[x0,y0,x1,y1]` (not `x/y/width/height`). `exact_circle` reads a nested `circle:{cx,cy,r}`. `overlap_free` reads `elements` (a list of element ids). Exit code 0 when overall ≥ threshold, else 1; a JSON report prints to stdout.

## `_overlap_free` stale-global-binding bug (fixed by inlining)
**Symptom:** `_overlap_free` returned "need ≥2 elements with geometry" even though `_shapely_of(rect, ...)` returned area 38400 when called directly — identical arguments, different results.

**Diagnosis path:**
1. Monkeypatch the helper (`_shapely_of`) to trace calls. If it's **never invoked**, the wrapper short-circuits (e.g. `ctx.el()` returns None) — the bug is upstream, not in the helper.
2. Check `_overlap_free.__globals__['_shapely_of'] is module._shapely_of`. If the wrapper holds a **stale binding** (monkeypatching the module attribute did *not* change what the wrapper sees), the wrapper captured the old function object at definition time. Sibling subagent edits to the same file create new function objects, but the wrapper keeps the stale one.

**Fix:** **inline the helper's logic** (`_bbox_viewbox` + `Polygon` from `shapely.geometry`) directly into `_overlap_free`, bypassing the stale global binding. (Implemented in `scripts/verify_artifact.py`.)

**Lesson:** when a helper returns wrong results *only through a wrapper* but works *directly*, suspect a stale `__globals__` binding (common with sibling edits to one file). Re-fetch fresh from module globals, or inline.
