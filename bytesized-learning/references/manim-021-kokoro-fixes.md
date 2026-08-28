# Manim 0.21 + Kokoro Fixes (Session 2026-08-23)

## Write() on Text objects fails

**Error:** `TypeError: Write only works for vectorized Mobjects`

**Cause:** `Write()` only works on vectorized mobjects (shapes, paths). `Text` and `Code` objects are NOT vectorized.

**Fix:** Use `FadeIn()` instead of `Write()` for all `Text` and `Code` objects.

```python
# WRONG:
self.play(Write(title))  # title is a Text object

# RIGHT:
self.play(FadeIn(title))
```

This applies to ALL scenes — titles, code snippets, labels, everything that's a `Text` object.

## Code class doesn't accept inline code

**Error:** `TypeError: Code.__init__() got an unexpected keyword argument 'code'`

**Cause:** The `Code` class in Manim CE expects a file path, not inline code text.

**Fix:** Use `Text()` for inline code display.

```python
# WRONG:
code = Code(code='ages["k"] = v', language="python", font_size=24)

# RIGHT:
code = Text('ages["k"] = v', font_size=22, font=MONO)
```

## Kokoro API: create() not generate()

**Error:** `AttributeError: 'Kokoro' object has no attribute 'generate'`

**Cause:** The method is `k.create()`, not `k.generate()`.

**Fix:**
```python
# WRONG:
audio, sr = k.generate(text, voice="af_bella", speed=1.0)

# RIGHT:
audio, sr = k.create(text, voice="af_bella", speed=1.0)
```

## Kokoro style parameter

**Error:** `TypeError: Kokoro.create() got an unexpected keyword argument 'style'`

**Cause:** The `create()` method doesn't accept a `style` parameter. The voice embedding should be passed as the `voice` parameter.

**Fix:**
```python
# WRONG:
audio, sr = k.create(text, voice="af_bella", speed=1.0, style=style)

# RIGHT (string voice):
audio, sr = k.create(text, voice="af_bella", speed=1.0)

# RIGHT (custom embedding):
audio, sr = k.create(text, voice=style, speed=1.0)
```

## Kokoro style rank error

**Error:** `Invalid rank for input: style Got: 1 Expected: 2`

**Cause:** The voice embedding from `mean(axis=0)` on shape `(510, 1, 256)` already produces `(1, 256)` which is 2D. No extra reshape needed. If you see this error, the embedding is being passed incorrectly.

**Fix:** Use the embedding directly from `mean(axis=0)` — it's already the correct shape.

```python
voice_emb = k.voices["af_bella"]  # shape: (510, 1, 256)
style = voice_emb.mean(axis=0).astype(np.float32)  # shape: (1, 256) — already 2D
```
