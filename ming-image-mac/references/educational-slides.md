# Educational slides with Ming-Image on Mac

How to use `MingImageT2I` for teaching slides where students must read real code.
This is the hard-won lesson from generating 8 decorator slides (2026-09-28).

## The core constraint — know it before prompting

The 4-bit Ming-Image model renders **code** differently from **illustrations**:

- It handles ONE short, simple line of code cleanly (e.g. `greet = say_hi`,
  `def greet(): print('Hello')`).
- It garbles multi-line code, complex syntax (`**kwargs`, nested `def`),
  stacked decorators (`@timer @requires_auth`), and any prompt with decorative
  language. The text becomes scrambled gibberish that LOOKS like code but is
  unreadable.

**Bottom line:** treat this model as a concept-illustration generator, NOT a
code renderer. It is fine for backgrounds/metaphors; unreliable for teaching real code.

## Prompt recipe that actually works (minimal, single-line)

Bad (decorative fluff dilutes code rendering):
> "a clean educational infographic slide on a light background with charts and labels..."

Good (minimal, says exactly what code to show):
> "a white educational slide showing the Python code greet = say_hi"

Rules:
- Start every prompt with "a white educational slide showing the Python code".
- Then give ONLY the single line of code to render. No other description.
- Use `--width 896 --height 512` (landscape, ~37s per image).
- Keep `--steps 14`.

## When slides still come out garbled — options

Looping/regenerating does NOT fix it: the model doesn't converge on correct
code, so there's no passing threshold. Do one of these instead:

1. Overlay real code yourself. Generate the concept/metaphor background with
   Ming-Image, then type clean Python in Keynote/PowerPoint. Reliable path for real
   teaching slides (this is what the user should do when code must be legible).

2. Use 8-bit tier for text quality. The `mlx-community/Ming-Image-0.1-Design-8bit`
   model (~28 GB, best quality on a 64GB Mac) renders text more faithfully than
   4-bit — but still cannot reliably render multi-line code.

## Legibility check (always, before sending)

After each generation, run `vision_analyze` on the image and ask:
"Read exactly what is written line by line. Is it legible, or garbled?"
Only send images where the code reads clearly and correctly. If a slide has even
scrambled fragments, it is not usable for teaching — regenerate with an
overlay or switch to 8-bit.

## Session data (for reference)

- Working single-line example: `def greet(): print('Hello'); greet();` rendered cleanly.
- Failed cases (garbled): `@make_logger`, nested `def repeat(times)/def deco(func)`,
  stacking `@timer @requires_auth`.
