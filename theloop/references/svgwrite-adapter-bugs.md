# svgwrite_adapter.py — Known Bugs & Fixes

Session: 2026-08-22 — Indian wedding image generation via theloop.

## Bug 1: `font_shape` is not a valid svgwrite kwarg

**Error:**
```
ValueError: Invalid attribute 'font-shape' for svg-element <text>.
```

**Cause:** The `_add_text()` function passed `font_shape=shape.get("font-family")` as a keyword argument to `dw.text()`. svgwrite's `Drawing.text()` does not accept `font_shape`.

**Fix (in `scripts/svgwrite_adapter.py`, line ~71):**
```python
# BEFORE (broken):
dw_text = dw.text(
    shape.get("text", shape.get("label", "")),
    (_num(shape.get("x")), _num(shape.get("y"))),
    font_size=_num(shape.get("size", shape.get("font-size", 16))),
    font_shape=shape.get("font-family"),  # ← REMOVE THIS LINE
)

# AFTER (fixed):
dw_text = dw.text(
    shape.get("text", shape.get("label", "")),
    (_num(shape.get("x")), _num(shape.get("y"))),
    font_size=_num(shape.get("size", shape.get("font-size", 16))),
)
# font-family is applied later via dw_text["font-family"] = shape["font-family"]
```

## Bug 2: svgwrite Text objects have no `.set()` method

**Error:**
```
AttributeError: 'Text' object has no attribute 'set'
```

**Cause:** After creating the Text object, the code tried `dw_text.set(k, value)` to set presentation attributes. svgwrite elements use dict-style `__setitem__`, not a `.set()` method.

**Fix (in `scripts/svgwrite_adapter.py`, line ~79):**
```python
# BEFORE (broken):
for k in ("fill", "text-anchor", "dominant-baseline", "font-weight",
          "font-style", "opacity"):
    if k in shape and shape[k] is not None:
        dw_text.set(k, shape[k])

# AFTER (fixed):
for k in ("fill", "text-anchor", "dominant-baseline", "font-weight",
          "font-style", "opacity"):
    if k in shape and shape[k] is not None:
        dw_text[k] = shape[k]  # dict-style assignment
```

## Summary

Both bugs are in `scripts/svgwrite_adapter.py` in the `_add_text()` function. They prevent ANY SVG with `<text>` shapes from being generated. The fixes are trivial — remove the `font_shape` kwarg and replace `.set()` with dict-style assignment.
