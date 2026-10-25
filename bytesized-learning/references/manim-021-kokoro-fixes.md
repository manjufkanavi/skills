# Manim + Audio Compatibility Fixes

Symptom -> mechanism -> fix, for the mistakes that cost iteration building the bytesized-learning pipeline. Version-labeled so old and new Manim behavior do not get confused.

## Write() on Text objects fails (all versions)
**Error:** `TypeError: Write only works for vectorized Mobjects`

**Cause:** `Write()` draws a vectorized path; `Text` and `Code` are not vectorized.

**Fix:** use `FadeIn()` for every `Text`/`Code` object (titles, code snippets, labels).

## Code class rejects inline text
**Error:** `TypeError: Code.__init__() got an unexpected keyword argument 'code'`

**Cause:** `Code` expects a file path, not inline text.

**Fix:** use `Text()` for inline code: `Text('ages["k"] = v', font_size=22, font=MONO)`.

## Kokoro: create() not generate()
**Error:** `AttributeError: 'Kokoro' object has no attribute 'generate'`

**Fix:** the method is `k.create()`. Pass a voice name string, or pass the embedding as the `voice` parameter (never `style`).

## Kokoro voice-embedding rank
**Error:** `Invalid rank for input: style Got: 1 Expected: 2`

**Cause:** `mean(axis=0)` on a `(510, 1, 256)` embedding already yields the correct `(1, 256)`; reshaping again breaks it.

**Fix:** pass the embedding straight from `mean(axis=0)` -- do not reshape or flatten it further.

## Manim 0.22: CENTER is no longer exported
**Error:** `NameError: name 'CENTER' is not defined` (usually from `.align_to(m, CENTER)`).

**Cause:** 0.22 dropped the scalar `CENTER` constant; only LEFT/RIGHT/UP/DOWN are exported.

**Fix:** align to a cardinal axis -- `.align_to(lines, LEFT)` centers vertically (LEFT is the vertical axis), `RIGHT` likewise; use UP/DOWN to center horizontally.

## Manim 0.22: get_center_x()/get_center_y() removed; *_left/right/top/bottom return arrays
**Error:** `AttributeError: 'Rectangle' object has no attribute 'center_x'` or `'numpy.ndarray' object has no attribute 'x'`.

**Cause:** the `get_center_x()/y()` helpers were removed and `.get_left()/.get_top()` etc. now return numpy Point3D arrays, so there is no `.x`/`.y`.

**Fix:** use `get_center()` and index it -- `cx, cy = rect.get_center()[:2]`. For one coordinate use the index directly: `x = strip.get_left()[0]; ytop = strip.get_top()[1]`.

## Manim 0.22: Create() only accepts VMobjects
**Error:** `TypeError: Create only works for VMobjects.` when passing a `Group` (or other non-VMobject) to `Create`.

**Cause:** Create traces a vectorized path; `Group`/Text are not VMobjects.

**Fix:** reserve `Create()` for shapes (`Rectangle`, `Circle`, `Line`, `Arrow`, `Polygon`...); use `FadeIn()`/`FadeOut()` for Groups and Text.

## Manim 0.22: Triangle(flat_bottom=True) removed
**Error:** `TypeError: Mobject.__init__() got an unexpected keyword argument 'flat_bottom'`.

**Cause:** `flat_bottom` was a Polygon kwarg dropped in 0.22.

**Fix:** drop the kwarg (`Triangle` is apex-up by default), or build a custom marker with `Polygon([...])` from explicit points.

## ffmpeg: select=lastframe unsupported
**Error:** `[Eval] Undefined constant or missing '(' in 'lastframe'` when using `-vf "select=lastframe"`.

**Cause:** this ffmpeg build does not expose the `lastframe` select value.

**Fix:** grab the last frame with a reverse trick and write one image --
`ffmpeg -i clip.mp4 -vf "reverse,select=eq(n\,0)" -vframes 1 -update 1 last.png`
(the `\,` escapes the comma so it is not parsed as a filter separator).

## Python version: pin Manim to <= 3.12
**Mechanism:** on bleeding-edge interpreters (e.g. 3.14) Manim's C deps -- `pycairo`, `pydantic-core` -- have no wheels and fail to build from source.

**Fix:** run Manim AND the narration/audio step in one venv pinned to Python 3.10-3.12 (homebrew `python@3.11`). Using a different interpreter for narration leaves you without numpy/`kokoro_onnx`.

## ffmpeg concat -c copy causes video freeze/stall after scene boundaries
**Error/Symptom:** Video plays for 5-7 seconds and then freezes, drops frames, or player stops playing at the first scene transition or padded frame boundary.

**Cause:** Concat demuxer with `-c copy` fails when stitching clips with slight differences in timebase, non-matching SPS/PPS parameter sets, or synthetic frozen-frame clips (`-loop 1`). Players encounter timestamp jitter/PTS jumps and stall.

**Fix:** Never use `-c copy` for stitching disparate clips. Always re-encode with `libx264` and `yuv420p`:
```bash
ffmpeg -y -f concat -safe 0 -i concat.txt -c:v libx264 -pix_fmt yuv420p -profile:v high -level 4.2 -movflags +faststart -c:a aac -b:a 192k final.mp4
```

## Manim 0.21: Text.set_font() does not exist
**Error:** `TypeError: Mobject.__getattr__.<locals>.setter() got an unexpected keyword argument 'weight'` when calling `text.set_font(weight=BOLD)`.

**Cause:** 0.21's `Text` has no `set_font` method; the name falls through to `Mobject.__getattr__`'s generic single-value setter, which rejects kwargs.

**Fix:** bake the weight into the constructor: `Text('x', font=MONO, weight=BOLD)` (works in 0.21).

## Kokoro `speed` is nonlinear — calibrate empirically
**Observation (kokoro_onnx, af_bella):** a 143-word script measures 54.5s @ speed=1.0, 58.6s @ 0.9, 70s @ 0.8, 35s @ 1.5 — duration-vs-speed is a steep nonlinear curve (stepped AR loops), not 1/speed.

**Fix:** before building, synthesize all segments at a trial speed, measure the total, and pick the speed that lands ~58–60s (143 words -> 0.9 -> ~59.8s with padding). Do not assume 2.4 wps or linear scaling.

**Voices path:** `scripts/produce.py`'s `VOICES_DEFAULT` points at `assets/kokoro/voices-v1.0.bin` — the file actually lives at `assets/voices-v1.0.bin` (one level up). Pass the correct path explicitly.

## Venv location (this machine)
Manim 0.21.0 + kokoro_onnx venv: `~/.venvs/bytesized-learning` (Python 3.12; `manim` binary inside it, no pip). Kokoro assets: `~/.hermes/skills/voice-bridge/assets/kokoro/model.onnx` + `~/.hermes/skills/voice-bridge/assets/voices-v1.0.bin`. `~/.hermes/skills` is a symlink to `~/.hermes/git_clone_dir/skills`.

## Text overflowing container boxes / cards
**Error/Symptom:** Code or explanatory text spills horizontally or vertically outside surrounding rectangles, cards, or boxes.

**Cause:** Hardcoding box dimensions (e.g., `width=8.5`) while text length exceeds the container width.

**Fix:** Dynamically compute container dimensions from content:
```python
# Option 1: Automatic bounding rectangle with margin buff
box = SurroundingRectangle(content, color=BLUE, buff=0.25, stroke_width=2, fill_color=BLUE, fill_opacity=0.1)

# Option 2: Derive width with padding
w = max(min_width, content.width + 0.6)
box = Rectangle(height=content.height + 0.5, width=w, ...)
```
Alternatively, scale content if it exceeds maximum allowable width: `if content.width > max_w: content.scale_to_fit_width(max_w)`.