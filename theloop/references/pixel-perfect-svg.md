# Pixel-perfect SVG generation (deterministic, no diffusion)

How to make the `theloop`/`closed-loop-artifact` loop produce **pixel-perfect SVG from text** using only free, open-source, login-free tools — **no AI diffusion / no image-gen models**.

## The gap
The loop already *authors* SVG and *judges* it deterministically (`scripts/verify_artifact.py`). The missing piece is a **structured-generation layer** so geometry is exact, plus deterministic tracing/cleanup.

## Structured intent → exact SVG
Emit a **shape list** (JSON) and convert to *exact* SVG — no hand-crafting, no coordinate drift:

```json
{"shapes":[
  {"type":"rect","x":80,"y":120,"width":240,"height":160,"fill":"#e63946"},
  {"type":"circle","cx":620,"cy":300,"r":100,"fill":"#ffd166"},
  {"type":"text","x":80,"y":520,"size":64,"text":"Hello","fill":"white"}
]}
```

Convertors (pick one per runtime):
- **Python:** `svgwrite` (author drawings), `drawsvg` (generate images)
- **Rust:** `resvg` (render), `usvg` (simplify)
- **JS/TS:** `SVG.js`, `D3.js`, `Paper.js`, `Snap.svg`
- **Render to PNG for judging:** `cairosvg` (already in the loop)

## Phase 0 — implemented (theloop/scripts/)
Two files close the structured-generation gap:

- **`svgwrite_adapter.py`** — `svgwrite_adapter.py <intent.json> --out <svg>`.
  Reads a structured intent (`{viewBox, gradients[], shapes[]}`) and emits exact SVG.
  Supports `rect`/`circle`/`path`/`polygon`/`ellipse`/`text`, plus a top-level
  `gradients[]` (linear/radial with `{offset,color,opacity}` stops) referenced via
  `fill:"url(#id)"`.
- **`spec_to_svg.py`** — `spec_to_svg.py <judge_spec.json> --out <svg>`.
  Translates a `verify_artifact.py` spec (criteria list) into a structured intent
  (synthesizes rects/circles/paths from `rect`/`circle`/`d`/`points`) and writes SVG
  (`--emit-intent <json>` also dumps the structured intent).

### Gotchas (learned the hard way)
1. **viewBox**: this `svgwrite` version *stores* `viewBox` but does not emit it, and
   its validator rejects the `viewBox` kwarg. `_build_group` injects `viewBox` into the
   root `<svg>` tag post-build (`_inject_viewbox`) so the renderer/judge see real dims.
2. **libcairo on Apple Silicon (macOS)**: `cairosvg`/`cairocffi` cannot find Homebrew's
   `libcairo.2.dylib`. **Export `DYLD_LIBRARY_PATH=/opt/homebrew/lib` before running the
   loop** — otherwise rasterization fails silently ("no rendered image").
3. **venv**: deps live in `~/.venvs/theloop` (Python 3.11, no pip). Install with
   `uv pip install --python ~/.venvs/theloop/bin/python3 cairosvg …`.

### Example scene (cat on a beach at sunset, 800×600)
`theloop/scripts/scene_cat_beach_sunset.{json,svg,png}` — sky→coral/gold horizon gradient,
glowing radial sun with water reflection, teal ocean, tan sand, dark cat silhouette with
golden eyes. Judge on a scene spec → **overall_score 0.909, passed** (threshold 0.8).

## Phase 1 — Dual-Judge (visual_authoritative) — implemented (theloop/scripts/)

Upgrades the loop with a **visual judge** that reads the rendered PNG directly and is
**authoritative**: `final_score = visual_score`. ASCII runs only when vision is unavailable.
The judge emits a structured `critique.json` with exact SVG fix directives consumed by the
next iteration's writer.

### Scripts

- **`visual_judge.py`** — two-step visual judging:
  - `--emit-prompt`: prints structured inspection prompt (what to look for per criterion)
  - `--ingest`: ingests `visual_score` + `visual_observations` + `svg_fixes` per criterion,
    validates exact SVG fix format, enforces per-criterion `visual_threshold` (strict block),
    writes `critiqueNN.json`
  - `--ascii-fallback`: ASCII-mode ingest when vision unavailable

- **`judge_spec_template.json`** — spec template defining:
  - `visual_judge.merge_strategy: "visual_authoritative"` — visual is the source of truth
  - `visual_judge.svg_fix_format: "exact"` — vague fixes dropped with a warning
  - Per-criterion `visual_threshold`, `blocking`, `weight`

### `critique.json` — inter-iteration contract

| Field | Purpose |
|-------|---------|
| `priority_fixes[]` | Ranked: `"[criterion_id] <exact SVG edit>"` |
| `next_iter_directive` | What to fix AND what NOT to change (names passing criteria) |
| `delivery_blocked_by[]` | Criteria blocking delivery |
| `should_deliver` | `true` → stop and deliver |

### Merge strategy: visual_authoritative
```
vision available  →  final_score = visual_score   judge_mode = "visual"
vision absent     →  final_score = ascii_score    judge_mode = "ascii-fallback"
```
`ascii_score` stored in `critique.json` for audit only — never overrides visual.

### The Phase 1 loop
```
plan(structured intent)
  → generate(svgwrite_adapter.py)
  → render(cairosvg)
  → visual_judge.py --emit-prompt  [model views PNG]
  → visual_judge.py --ingest       → critiqueNN.json
  → check: should_deliver?
       yes → deliver best artifact
       no  → read priority_fixes + next_iter_directive → targeted SVG fix → next iteration
```
Stop when `overall_score ≥ score_threshold` **AND** all blocking criteria meet `visual_threshold`.

---

## Raster → SVG (deterministic tracing, no diffusion)
If the user supplies a raster reference, trace it (not diffusion) then clean:

`user raster → Potrace / AutoTrace → SVGO → cairosvg → visual_judge.py → iterate`

- **Potrace** / **AutoTrace** — open-source bitmap→vector engines (the core Inkscape & SVGcode uses).
- **SVGcode** — browser PWA using Potrace (free).

## Clean + validate
After each generation, run **SVGO** / **svgcleaner** (strip cruft) and **xmllint** (XML well-formedness) so the judge measures *intent*, not noise.

## The full loop (Phase 0 + Phase 1)
```
plan(structured intent)
  → generate(svgwrite_adapter.py)
  → render(cairosvg)
  → visual_judge.py --emit-prompt  [model views PNG directly]
  → visual_judge.py --ingest       → critiqueNN.json
  → writer reads priority_fixes + next_iter_directive
  → apply exact svg_fixes for failing criteria only
  → repeat until should_deliver = true
```

## Exactness anchors (measure against)
`W3C SVG2` spec + `verify_artifact.py` criteria: `exact_rect`, `exact_circle`, `exact_color`, `text_ocr`, `proportion_ratio`, `overlap_free`, `grid_alignment`, `exact_path`, `exact_text`, `exact_palette`.
