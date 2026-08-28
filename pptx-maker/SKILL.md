---
name: pptx-maker
description: Generate a beautiful, animated, EDITABLE PowerPoint (.pptx) from a declarative JSON spec. Offline — no image model, no API keys. Uses python-pptx + lxml.
tags: [presentation, pptx, powerpoint, design, animation]
---

# pptx-maker

Turn a **JSON spec** into a polished, animated, fully-editable `.pptx` deck.

- **Offline**: no image model, no API keys, no network.
- **Editable**: real text, shapes, native charts, tables — not flattened images.
- **Animated**: hand-crafted OOXML `<p:seq>` animations that work even on python-pptx builds lacking a high-level animation API.

## When to use

Building a slide deck from project data (benchmarks, architecture, metrics, comparisons)
where you want a consistent visual theme, charts/tables, and reveal animations — without
designer tools or image generation.

## Files

- `scripts/deck_builder.py` — the engine (single dependency: `python-pptx`, plus `lxml`).
- `scripts/verify_deck.py` — validate a generated deck (integrity, slide/animation/chart counts).
- `templates/deck_spec.template.json` — minimal starter spec to copy and modify.
- `references/python-pptx-102-quirks.md` — enum-name differences + API workarounds for old python-pptx builds.
- `reports/final/solvarch_deck_spec.json` — example spec (10-slide Solvarch deck).
- `reports/final/solvarch_deck.pptx` — generated output.

**Validate before shipping:** `python scripts/verify_deck.py reports/final/solvarch_deck.pptx`.

## Quick start

```bash
python scripts/deck_builder.py --spec <spec.json> --out <deck.pptx>
python scripts/deck_builder.py --spec <spec.json> --out <deck.pptx> --inspect   # preview plan, no write
python scripts/deck_builder.py --spec <spec.json> --out <deck.pptx> --resize 10,7.5  # custom size
```

The spec is a JSON object: `{ "theme": {...}, "slides": [ ... ] }`.

## Spec schema

### `theme`

```json
"theme": {
  "bg": "#0B1420", "panel": "#12212E", "accent": "#12B5C1",
  "accent2": "#F5B642", "text": "#F1F5F9", "muted": "#94A3B8",
  "title_font": "Calibri", "body_font": "Calibri"
}
```

### `slides`

Each slide is an object with `type` + type-specific fields. Supported types:

| type | purpose | key fields |
|------|---------|------------|
| `title` | cover | `num, kicker, title, subtitle, footers` |
| `section` | chapter break | `num, kicker, title, lead` |
| `bullets` | lists | `num, kicker, title, items[]` |
| `two_col` | side-by-side | `num, kicker, title, left[], right[]` |
| `metrics` | KPI cards | `num, kicker, title, cards[]` |
| `chart` | native charts | `num, kicker, title, categories, values` **or** `grouped, series, colors` |
| `table` | data grid | `num, kicker, title, rows[]` |
| `quote` | highlight | `num, kicker, title, text, attribution` |
| `closing` | Q&A | `title, points[]` |

**Animations** are attached per-slide via an `anim` dict (see below).

## Animation model

Animations are declared in a slide-level `anim` object. The engine emits `<p:seq>`
elements (validated OOXML) so they work on any python-pptx build.

```json
"anim": {
  "watermark": { "effect": "fly",  "trigger": "after", "order": 1 },
  "title":     { "effect": "fade", "trigger": "after", "order": 3 },
  "items":     { "effect": "fly",  "trigger": "after", "order_base": 3 }
}
```

- **effect**: `fly, fade, push, split, zoom, appear, fall` (entry) or `pulse, glow, compress, expand, resize, skew` (emphasis).
- **trigger**: `after` (after previous), `with` (with previous), `click` (on request).
- **order**: 1-based play order for a single element.
- **order_base**: used by multi-item renderers (`bullets`, `two_col` columns, `metrics` cards) — each item gets `order_base + index`.

Default animation args are applied automatically; only override when you want a specific effect/order.

## Slide-type details

- **chart** (bar): `{ "categories": [...], "values": [...], "value_color": "#…" }`.
- **chart** (grouped): `{ "grouped": true, "categories": [...], "series": [[name, v1, v2,...], ...], "colors": [hex...] }`.
- **metrics** cards: `{ "value", "label", "sub", "value_color" }`.
- **table** rows: first row is the header; cells support `"bold|normal"` split for inline emphasis.
- **two_col** / **bullets** items: `str`, `(level, text)` tuple, or `{ "text", "level", "bold", "color" }` dict.

## Conventions & pitfalls

- Keep animations **ordered** (`order` / `order_base`) — un-ordered animations play together.
- Font sizes are `Pt(...)`; never pass `0` (minimum is `Pt(1)`). The engine clamps metric-card sizes.
- Chart enums differ per python-pptx build (`BAR_CLUSTERED`, `COLUMN_CLUSTERED`) — the engine pins them.
- The engine resolves the owning slide from both `Shape` and `text_frame` objects, so either can be animated.
- Rerun `--inspect` to preview the slide plan before writing.

## Extending

Add a slide type by defining `_slide_<type>(deck, slide, spec)` and dispatching it in `render_slide`
(`globals().get("_slide_" + t)`). To animate a new element, call `deck.animate(shape, effect=..., order=...)`.
