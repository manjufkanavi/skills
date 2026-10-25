# Reverse-Engineering a PDF's Design (pymupdf + pixels)

Run `scripts/reverse-engineer.py <pdf>` for the full dump (spans, drawings, font/size/color census). Then resolve what it can't:

1. **Spans** (`page.get_text("dict")`): x/y/w/h + size + font + color per span → the layout blueprint and type scale.
2. **Line pitch, not bbox height**: consecutive span y0 deltas are the true leading. A 9.3pt face at 13.8pt pitch means `line-height ≈ 1.5` — never derive line-height from glyph bbox height (it under-reads).
3. **Drawings** (`page.get_drawings()`): rect + fill/stroke hex + width. Rules, borders, panels, cards, corner tabs show up here.
4. **Stacked same-rect fills** (e.g. 3× pale + 1× accent on one rect) = a clip-ring mechanism: the generator draws border segments inside a rounded-rect clip, each segment a different color. Don't guess — read the raw stream (`doc.xref_stream(xref)` over `page.get_contents()`) for `W n` / `W* n` clip ops, or pixel-sample the render at each edge (left/right/top/bottom ±1px) to see which edge carries which color. The visible result is usually a thick accent bar on one edge + hairline on the rest; in CSS that is `border: 1pt solid <hairline>; border-left: 4pt solid <accent>; border-radius: R`.
5. **Pixel sampling** (PIL on the 2x render) resolves anti-aliasing ambiguity: sample panel centers, edge ±1px, rule lines, corner accents. A ~50%-blend pixel (accent over white) means the true color is the unblended hex.
6. **Stream coordinates**: content-stream units ≠ pt. Scale = `page.rect.width / max_stream_x`. Corner radius = first curve-control offset of the rounded-rect path, divided by that scale.
7. Encode everything as CSS custom properties in pt (the measured unit) — one `:root` token block, no magic numbers in the rules.
