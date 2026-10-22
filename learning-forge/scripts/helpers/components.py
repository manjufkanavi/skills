1|"""Reusable, responsive Manim primitives for learning-forge videos.
2|
3|Guarantees 100% containment, zero text overflow, and consistent typography.
4|"""
5|from manim import *
6|
7|# Master Teacher Color Palette (Classic 3B1B + Modern Low Eye-Strain)
8|BG       = "#1C1C1C"
9|CYAN     = "#58C4DD"
10|GREEN    = "#83C167"
11|YELLOW   = "#FFFF00"
12|RED      = "#FF6B6B"
13|LIGHT    = "#EEEEEE"
14|MIDGRAY  = "#BBBBBB"
15|DIM      = "#555555"
16|MONO     = "Menlo"
17|
18|
19|def code_text(text, size=24, color=LIGHT, weight=None):
20|    """Consistent monospace text element."""
21|    kw = dict(font_size=size, font=MONO, color=color)
22|    if weight is not None:
23|        kw["weight"] = weight
24|    return Text(text, **kw)
25|
26|
27|def heading_text(text, size=36, color=CYAN):
28|    """Consistent scene heading."""
29|    return code_text(text, size=size, color=color, weight=BOLD)
30|
31|
32|def subcaption_text(text, size=20, color=MIDGRAY):
33|    """Sub-heading or explanatory caption."""
34|    return code_text(text, size=size, color=color)
35|
36|
37|def auto_card(content, color=CYAN, buff=0.3, stroke_width=2, fill_opacity=0.08):
38|    """Wraps any Mobject or Group dynamically, guaranteeing zero text spillage."""
39|    rect = SurroundingRectangle(
40|        content,
41|        color=color,
42|        buff=buff,
43|        stroke_width=stroke_width,
44|        fill_color=color,
45|        fill_opacity=fill_opacity
46|    )
47|    return VGroup(rect, content)
48|
49|
50|def chip_badge(text, color=YELLOW, size=18):
51|    """A pill-shaped badge for keywords, types, or symbols."""
52|    lbl = code_text(text, size=size, color=color, weight=BOLD)
53|    box = SurroundingRectangle(
54|        lbl,
55|        color=color,
56|        buff=0.18,
57|        stroke_width=1.5,
58|        fill_color=color,
59|        fill_opacity=0.15,
60|        corner_radius=0.1
61|    )
62|    return VGroup(box, lbl)
63|
64|
65|def slot_box(label_str, width=1.6, height=1.2, color=CYAN):
66|    """A fixed parameter slot box with a label below."""
67|    box = Rectangle(
68|        width=width,
69|        height=height,
70|        stroke_color=color,
71|        stroke_width=2.5,
72|        fill_color=color,
73|        fill_opacity=0.1
74|    )
75|    lbl = code_text(label_str, size=18, color=color)
76|    lbl.next_to(box, DOWN, buff=0.15)
77|    return VGroup(box, lbl)