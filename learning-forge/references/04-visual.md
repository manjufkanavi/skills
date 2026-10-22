# Stage 4 — Visual direction (Manim CE 0.22)

## Stack rules
- **Text-only scenes. No LaTeX, no MathTex.** Most code/CS concepts need no
  math; if a topic genuinely needs equations, install texlive and use MathTex
  with RAW strings — but default is `Text(font=MONO)`.
- One Python file `script.py`, one class per scene, class name == scene id in
  script.json. Every scene sets its own background in `setup()`.
- Import the shared kit:
  ```python
  import sys; sys.path.insert(0, str(Path(__file__).parent / "scripts" / ".." / "scripts"))  # or absolute
  from learning_forge_helpers import *   # see below
  ```
  Concretely: `sys.path.insert(0, "<skill>/scripts/helpers")` then
  `from components import *` — gives the palette + auto_card / chip_badge /
  slot_box with guaranteed text containment.

## Palette (shared constants in components.py)
| role | color | use |
|---|---|---|
| BG | #1C1C1C | every scene |
| CYAN | #58C4DD | primary / structure |
| GREEN | #83C167 | correct / working state |
| YELLOW | #FFFF00 | the hero / aha element |
| RED | #FF6B6B | errors, breaks, traps |
| LIGHT | #EEEEEE | code text |
| MIDGRAY | #BBBBBB | captions, secondary labels |
| DIM | #555555 | structural (grids, axes) at low opacity |

**One accent per idea.** When a beat introduces a new concept, it gets the
accent color; previous concepts drop to MIDGRAY/DIM. This is how the eye knows
what just changed.

## Typography
- Monospace ONLY (Menlo). Proportional fonts render with broken kerning.
- Title 48 BOLD · Heading 36 · Body 30 · Label 24 · Caption 20. Floor: 18.
- Code lines 24–26; never let a line exceed ~60 chars — split it.

## Opacity layering (directs attention)
- primary elements 1.0 · contextual 0.4 · structure (grids/axes) 0.15
- never show everything at full brightness; the brightest thing on screen is
  always the thing being spoken about.

## Containment (never clip)
- Any text in a box: derive the box from the text
  (`SurroundingRectangle(content, buff=0.25)`) or use `auto_card`.
- Long lines: `content.scale_to_fit_width(max_w)`.
- Edge text: `buff >= 0.5` from screen edge.

## Manim 0.22 gotchas (these WILL bite you)
- `Write()` is vectorized-only → **FadeIn for all Text/Code** (Write for shapes).
- `CENTER` constant removed → align with `align_to(m, LEFT/RIGHT/UP/DOWN)`
  (LEFT = vertical axis, i.e. "center vertically, align left edge").
- `get_center_x()`/`.center_x` removed → use `get_center()[0]`.
- `.animate` on a Group requires the members added first: add, then animate.
- `Triangle` needs explicit `color`/`fill` kwargs to render as expected.
- `dash_ratio` is gone → use `DashedLine` / `set_stroke`.
- `Arrow` needs `Create(arrow)` in 0.21; in 0.22 `self.play(arrow.animate...)`
  or `GrowArrow` are safest.
- Background color: set in `def setup(self): self.camera.background_color = BG`,
  not in construct.

## Per-scene variation (boring = same layout twice)
Vary across scenes: dominant color, layout (left/right/center/triadic),
entry animation (Write / FadeIn / GrowFromCenter / Create / TransformFromFamily),
density. Two consecutive scenes with the same layout AND same dominant color
is a FAIL.

## Staging the aha moment
- The hero element enters at 1.0 opacity in the ACCENT color with a 2.0–2.5 s
  run_time, then `self.wait(2.0)` — the viewer needs 2 s of stillness after a
  reveal. Never cut the aha.
- Use `ReplacementTransform` to morph between related states (code card A →
  code card B; wrapper box closed → open). Morphs sell "this IS that".
- Errors: RED burst = quick `Flash`/`Indicate` + the error text in a red
  `auto_card`. Recovery: the same card flips to GREEN. Color state is semantic.

## Transitions
Keep them fast (0.5 s) and consistent: FadeOut-all at scene end. No fancy
wipes — the CONTENT change is the transition.

## Subtitles in-video
Every narration line gets `self.add_subcaption(line_text, duration=est)` on its
animation, or `subcaption="..."` on the `self.play()`. (produce.py also emits
the full SRT; in-video captions are the second safety net.)
