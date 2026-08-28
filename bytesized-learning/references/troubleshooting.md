# Manim 0.21 Compatibility Gotchas

## Animation: Write() vs FadeIn()

`Write()` only works on **vectorized mobjects** (shapes, paths, circles, rectangles). It does NOT work on:
- `Text` objects
- `Code` objects
- Any non-vectorized mobject

**Rule of thumb:** If it's text or code, use `FadeIn()`. If it's a shape/line/path, `Write()` is fine.

```python
# These FAIL with Write():
self.play(Write(Text("Hello")))        # TypeError
self.play(Write(Code(code="...")))     # TypeError

# These work with Write():
self.play(Write(Circle()))             # OK
self.play(Write(Rectangle()))          # OK
self.play(Create(Arrow()))             # OK (Create is the right one for arrows)
```

## Code class expects file path, not inline code

The `Code` class constructor takes a `file_path` parameter, not inline code.

```python
# WRONG:
code = Code(code='x = 1', language="python", font_size=24)

# RIGHT (inline code via Text):
code = Text('x = 1', font_size=22, font=MONO)

# RIGHT (Code from file):
code = Code(file_path="script.py", language="python", font_size=24)
```

## Arrow needs Create(), not Write()

```python
# WRONG:
self.play(Write(Arrow(start, end)))

# RIGHT:
self.play(Create(Arrow(start, end)))
```

## dash_ratio removed

The `dash_ratio` parameter on `DashedLine` is gone in 0.21.

## DOWN_LEFT → DOWN + LEFT

```python
# WRONG:
obj.move_to(DOWN_LEFT)

# RIGHT:
obj.move_to(DOWN + LEFT)
```

## Background in setup()

Set `self.camera.background_color` in `setup()` for Manim 0.21+.

## Number class removed

The `Number` class is gone. Use `Text(str(n))` or `MathTex(str(n))` instead.
