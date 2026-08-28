# Improving `theloop` → Pixel-Perfect SVG Generation (Deterministic, No Image-Gen Models)

**Author:** in-model loop analysis (Ornith-1.5-35B-A3B-MLX-4bit)
**Date:** 2026-08-22
**Constraint:** all tools free / open-source / install without login or payment; **no image-generation (diffusion) models**; uses the loop + static tools + smart reasoning + the running text-generation model.

---

## 0. TL;DR

The loop already *renders and scores* an SVG, but its judge (`verify_artifact.py`) can only do **three** things — count dark pixels in a region, measure bar heights, or substring-match text. Critically, `text_in_region` does **not read text**; it only checks "is there dark ink here." So it can never produce *pixel-perfect* output — it gives no coordinate-level feedback.

**The fix is not a new rendering engine — it is a much richer, deterministic judge.** Upgrade the judge with geometry/OCR/color/overlap assertions backed by four already-verified, free, login-free, payment-free libraries (`cairosvg`+`rsvg-convert` render, `tesseract` OCR, `svgpath2mpl`+`shapely` vector geometry, `Pillow` pixels, `xmllint` validation). Add a **text→outline-path** step (`svg-text-to-vector`, MIT) so text renders identically everywhere. Then the loop receives *precise, coordinate-level feedback* ("bar 2 right edge at x=158, expected 160 — off by 2px"; "text 'X1' OCR'd at (160,540) but expected (160,550)") and iterates to pixel-perfection.

---

## 1. Research Summary (Tiny Fish deep research, 78 queries / 3 rounds / 43 items)

The deep research was run against the Tiny Fish Search + Fetch APIs. The web corpus was heavily polluted by the word "open" (matched "Open Championship" golf, "OpenAI", "Open University", "Open Library"), but the genuinely relevant, tool-specific results are:

| Category | Tool (source) | What it does | License / cost |
|---|---|---|---|
| **Text → outlined paths** | **`svg-text-to-vector`** (npm, `npmx.dev`) | Converts `<text>` tags into outlined `<path>`s (font → vector) | **MIT**, 82 kB |
| **Text → SVG (font-to-path)** | `to-svg.com` / `texttosvg.app` / `svggenie` | Type text → download SVG with glyphs already outlined as paths | Free, some 100% local/offline |
| **Raster → SVG** | **`vtracer`** (visioncortex, 6.6k★) | Bitmap → vector paths | Open source |
| **Pixel-art → SVG** | `pix2svg` (crates.io / Rust) | Convert pixel art to optimized SVG | Open source (unreviewed) |
| **SVG ↔ PNG** | **`CairoSVG`** (Kozea) + `cairosvg`/`rsvg-convert` | Vector↔pixel rendering | Open source |
| **EXCLUDE (uses image-gen)** | **VectorFusion** (arXiv 2211.11319), **StarVector** (CVPR 2025) | Text/image → SVG *via pixel-based diffusion models* | Research — **violates the "no image-gen model" rule** |

**Conclusion:** the ecosystem already provides everything needed for *deterministic* text→SVG. The only thing missing is a judge strong enough to drive the loop to pixel-perfection. VectorFusion/StarVector/pix2svg-tracing are explicitly excluded because they require image-generation (diffusion) models.

---

## 2. Current `theloop` judge — what it can and cannot do

`scripts/verify_artifact.py` supports only:
- `bars_increasing` — ink-bar heights strictly increasing (coarse ordering only).
- `text_in_region` — **dark-pixel ratio in a region** — i.e. "is there dark stuff here?" (NOT text content).
- `text_present` — substring match on a `doc`/markdown artifact.

**Gaps that block pixel-perfection:**
1. **No text *content* verification** — `text_in_region` can't tell "X1" from "X2" from "foo". No OCR.
2. **No exact coordinates** — can't say "this rect's right edge is at x=160".
3. **No exact sizes / proportions / ratios** — only "increasing".
4. **No color checks** — can't assert fill #2563eb is present at the right place.
5. **No overlap / z-order / collision detection.**
6. **No grid/margin/alignment checks.**
7. **No reference pixel-diff (SSIM/MSE)** when a target image exists.
8. **Text font-availability variance** — `<text>` renders differently across cairosvg/rsvg/OS fonts → "not pixel perfect" even when coordinates are correct.

---

## 3. The Improvement Plan

### 3.1 New deterministic judge assertions (extend `verify_artifact.py`)

Add these criterion `type`s (all operate on real rendered pixels / parsed SVG geometry — no hand-waving):

| New `type` | Input from spec | What it checks | Feedback given |
|---|---|---|---|
| `exact_rect` | `{x,y,w,h}` in viewBox | rect's actual bbox matches spec within `tol` px | "rect #logo at (10,10,80,40) ✓ / off by 3px on w" |
| `exact_circle` | `{cx,cy,r}` | circle bbox matches | "circle r=25 → bbox 50×50 ✓" |
| `exact_path` | path string | `svgpath2mpl.parse_path` → shapely geometry area/bounds | "path area=2800, bounds=(10,10,90,80)" |
| `proportion_ratio` | expected ratio e.g. 16/9, 0.618 | width/height of element or canvas | "aspect 1.778 vs expected 1.778 ✓" |
| `exact_color` | fill/stroke hex + region | that color's dark-pixel mass in region ≥ threshold | "#2563eb present at 0.041 (≥0.02) ✓" |
| `text_ocr` | expected string(s) | **tesseract OCR** of rendered PNG; string present in region | "OCR: 'X1' at (160,540); expected (160,550) — 10px low" |
| `text_position` | expected (x,y) for a label | OCR bounding-box center vs expected | "label center off by (2,-4)px" |
| `overlap_free` | list of elements | shapely `.intersection().is_empty` between pairs | "rectA ∩ rectB = 4px² — overlap!" |
| `grid_alignment` | grid step e.g. 4 | every coordinate snaps to grid | "x=158 not on 4px grid (snap→160)" |
| `pixel_diff` | reference PNG path | SSIM + MSE vs reference | "SSIM=0.94, MSE=12.3" |

Exit code = overall ≥ threshold (unchanged). The JSON report gets a `detail` field per criterion carrying the measured numbers the model reads to iterate.

### 3.2 Toolchain (verified installed & working on this machine)

| Role | Tool | Status here | Install (free, no login, no payment) |
|---|---|---|---|
| Render SVG→PNG | `cairosvg` (Python) + `rsvg-convert` (librsvg 2.62) | ✅ both present | system deps already installed |
| Fallback render | `resvg` (`resvg-python`) / `node-canvas` / `sharp` | n/a | `uv pip install resvg` or `npm i sharp node-canvas` |
| **OCR (text content)** | **`tesseract` 5.5.3** | ✅ installed (brew) | `brew install tesseract` (+ `brew install tesseract-lang` for more langs) |
| **Vector geometry** | **`svgpath2mpl`** + **`shapely` 2.1.2** | ✅ installed (uv) | `uv pip install shapely svgpath2mpl` |
| **Text → outline paths** | **`svg-text-to-vector`** (npm) | n/a | `npm install svg-text-to-vector` (MIT) |
| Pixel analysis | `Pillow` 12.2.0 | ✅ | already present |
| SVG validation | `xmllint` (libxml2 2.9.13) | ✅ | already present (`sudo apt install libxml2-utils`) |

**One-liner setup for the skill's venv:**
```bash
uv venv .venv-svg && uv pip install --python .venv-svg/bin/python shapely svgpath2mpl cairosvg pillow resvg
sudo apt-get install -y libxml2-utils      # xmllint (if missing)
brew install tesseract tesseract-lang       # OCR (if missing)
npm i -g svg-text-to-vector               # text -> outlined paths
```

### 3.3 Spec format upgrade (`spec.json`)

```json
{
  "viewBox": "0 0 400 300",
  "grid": 4,                 // all coords must snap to 4px
  "margin": 16,              // canvas padding tolerance
  "tol_px": 3,               // per-geometry tolerance
  "reference": "target.png", // optional reference for pixel_diff
  "threshold": 0.85,
  "text_outline": true,      // run svg-text-to-vector before render (font-independent)
  "criteria": [
    {"name": "logo", "type": "exact_rect",   "ref": "#logo", "rect": {"x":10,"y":10,"w":80,"h":40}},
    {"name": "title text", "type": "text_ocr",   "expect": "Monthly Sales", "region":[0,0,400,40]},
    {"name": "x-labels",   "type": "text_ocr",   "expect": ["X1","X2","X3"]},
    {"name": "bar color",  "type": "exact_color","ref":"#bar", "color":"#2563eb"},
    {"name": "no overlap", "type": "overlap_free", "elements":["#bar","#axis"]},
    {"name": "aspect",     "type": "proportion_ratio", "ratio": 1.333}
  ]
}
```
New fields: `grid`, `margin`, `tol_px`, `text_outline`, `reference`, per-criterion `ref` (SVG id), `rect`/`cx/cy/r`, `color`, `expect` (string or list).

### 3.4 Loop change: from coarse to coordinate-level feedback

Before: iter-1 score "bars increasing = 0.5" → model guesses what's wrong.
After: the model reads exact numbers, e.g.:

```
[crit] exact_rect #logo: bbox=(10,10,80,40) — within tol ✓ 1.0
[crit] text_ocr "Monthly Sales": OCR found "Monthy Sales" (misspelled) — 0.0
[crit] text_ocr X-labels: OCR "X1","X2","X3" at (160,540)(260,540)(360,540);
       expected y=550 → all 10px too high → 0.6
[crit] exact_color #bar #2563eb: mass 0.041 ≥ 0.02 ✓ 1.0
[crit] overlap_free: #bar ∩ #title = 0 ✓
[crit] grid_alignment: x=158 not on 4px grid (snap→160) → 0.8
[overall] 0.88 ≥ 0.85 → PASS (stop)
```

The model now fixes *exactly one measured gap per iteration* (e.g. "shift labels down 10px, fix title spelling"), converging to pixel-perfect in few iterations — instead of guessing.

### 3.5 Text-perfection step (the big win)

Run `svg-text-to-vector` (or `to-svg.com`/`texttosvg.app` local mode) to convert every `<text>` into an outlined `<path>` **before** rendering. Benefits:
- Rendering no longer depends on OS font availability / cairo vs rsvg font metrics.
- Text becomes geometry → `shapely` can measure its exact bounds/area → `text_ocr` and `exact_path` assertions apply to text too.
- This removes the single largest source of "not pixel perfect" for text-heavy SVGs.

### 3.6 Guardrails (honoring the user's constraints)

- **No diffusion / image-generation models.** Exclude VectorFusion, StarVector, pix2svg-tracing. The pipeline is: *text → deterministic SVG (static tools) → render → deterministic judge → iterate*.
- All tools are free, open-source, install without login or payment.
- The executing model remains the only actor (plan → write → render → judge → iterate), exactly as `theloop` requires.

---

## 4. Implementation order (what I will build when you say "Proceed")

1. **`scripts/verify_artifact.py`** — add assertion types: `exact_rect`, `exact_circle`, `exact_path`, `proportion_ratio`, `exact_color`, `text_ocr`, `text_position`, `overlap_free`, `grid_alignment`, `pixel_diff`. (Reuse `load_image`/`rasterize`; add SVG-parse + shapely + tesseract paths.)
2. **`scripts/text_to_path.py`** — wrapper: parse SVG, run `svg-text-to-vector` (or `texttosvg.app` local) on every `<text>`, emit font-independent SVG. Called when `spec.text_outline: true`.
3. **New `spec.json` schema** (above) + validator (`spec.check()`).
4. **`references/pixel-perfect-plan.md`** in the skill documenting the loop change + feedback format.
5. **One end-to-end demo** (e.g. the bar-chart spec) proving the upgraded judge converges to ≥0.85 with coordinate-level feedback, and that `text_ocr` catches a misspelled title.

**Deliverable:** this plan (`reports/theloop-pixel-perfect-plan.md`) + the upgraded judge scripts once implemented.
