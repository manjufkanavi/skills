# Pixel-Perfect Text→SVG: Open-Source, Deterministic Toolchain (No Diffusion)

**Research date:** 2026-08-22 · **Source:** `awesome-vector-tools` GitHub list + deep-research corpus (53 items, 7 themes).

## Scope
Free / open-source / easy-to-install tools that generate **pixel-perfect SVG from text** using the in-model loop **plus** deterministic static tools — **no AI diffusion / no image-gen models, no login, no payment.**

## What the research showed
The public corpus for "text-to-SVG" is dominated by **AI diffusion SVG models** — which this task **excludes**:

| Model | Approach | Status |
|---|---|---|
| StarVector (8B) | image→SVG foundation model | Excluded (diffusion) |
| VectorFusion | abstracts pixel diffusion → SVG | Excluded (diffusion) |
| OmniSVG | unified SVG generation model | Excluded (diffusion) |
| SVGFusion | vector-space diffusion | Excluded (diffusion) |
| SVG-VAE / Magenta | typography VAE | Excluded (diffusion) |

The **deterministic, open-source** alternatives (the actual answer) cluster into five roles.

## The deterministic toolchain (what we use)

### 1. Programmatic SVG generation (text → exact geometry)
| Tool | Lang | Role |
|---|---|---|
| **svgwrite** | Python | Author SVG drawings from structured shapes (rect/circle/path/text) with exact coords |
| **drawsvg** | Python | Programmatically generate SVG images |
| **resvg** / **usvg** | Rust | High-quality SVG render / SVG simplification |
| **SVG.js**, **D3.js**, **Paper.js** | JS/TS | Manipulate/render SVG in-browser |
| **CairoSVG** | Python | Render SVG → PNG (used by the loop for judging) |

### 2. Bitmap → vector tracing (reference-based, NO diffusion)
| Tool | Role |
|---|---|
| **Potrace** | Open-source bitmap-tracing engine — the core that powers Inkscape, SVGcode, SVGOMG |
| **AutoTrace** | Open-source bitmap→vector, multiple output formats |
| **SVGcode** | Browser PWA using the Potrace algorithm (free, open-source) |

### 3. SVG optimization / cleanup (post-generation)
| Tool | Role |
|---|---|
| **SVGO** | Node.js SVG optimizer — the industry standard |
| **svgcleaner** | CLI that strips unnecessary data |
| **SVGOMG** | Web UI for SVGO |

### 4. Validation / exactness anchors
| Tool | Role |
|---|---|
| **xmllint** (already installed) | XML well-formedness check |
| **W3C SVG2 spec** | The exactness standard the judge measures against |

### 5. Open-source editors / design (human-in-the-loop)
| Tool | Role |
|---|---|
| **Inkscape** | Free vector editor with Potrace "Trace Bitmap" |
| **Penpot** | Open-source design platform, SVG-native format |

## Conclusion
Pixel-perfect SVG from text does **not** require diffusion. The loop already *authors* SVG and *judges* it deterministically (`verify_artifact.py`). The missing piece is a **structured-generation layer** (svgwrite/resvg) + **deterministic tracing** (Potrace) + **cleanup** (SVGO/svgcleaner) + **validation** (xmllint) — all free, open-source, no login, no payment, no image-gen model.
