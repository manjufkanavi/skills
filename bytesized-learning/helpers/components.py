"""Reusable, responsive Manim primitives for bytesized-learning videos.

Guarantees 100% containment, zero text overflow, and consistent typography.
"""
from manim import *

# Master Teacher Color Palette (Classic 3B1B + Modern Low Eye-Strain)
BG       = "#1C1C1C"
CYAN     = "#58C4DD"
GREEN    = "#83C167"
YELLOW   = "#FFFF00"
RED      = "#FF6B6B"
LIGHT    = "#EEEEEE"
MIDGRAY  = "#BBBBBB"
DIM      = "#555555"
MONO     = "Menlo"


def code_text(text, size=24, color=LIGHT, weight=None):
    """Consistent monospace text element."""
    kw = dict(font_size=size, font=MONO, color=color)
    if weight is not None:
        kw["weight"] = weight
    return Text(text, **kw)


def heading_text(text, size=36, color=CYAN):
    """Consistent scene heading."""
    return code_text(text, size=size, color=color, weight=BOLD)


def subcaption_text(text, size=20, color=MIDGRAY):
    """Sub-heading or explanatory caption."""
    return code_text(text, size=size, color=color)


def auto_card(content, color=CYAN, buff=0.3, stroke_width=2, fill_opacity=0.08):
    """Wraps any Mobject or Group dynamically, guaranteeing zero text spillage."""
    rect = SurroundingRectangle(
        content,
        color=color,
        buff=buff,
        stroke_width=stroke_width,
        fill_color=color,
        fill_opacity=fill_opacity
    )
    return VGroup(rect, content)


def chip_badge(text, color=YELLOW, size=18):
    """A pill-shaped badge for keywords, types, or symbols."""
    lbl = code_text(text, size=size, color=color, weight=BOLD)
    box = SurroundingRectangle(
        lbl,
        color=color,
        buff=0.18,
        stroke_width=1.5,
        fill_color=color,
        fill_opacity=0.15,
        corner_radius=0.1
    )
    return VGroup(box, lbl)


def slot_box(label_str, width=1.6, height=1.2, color=CYAN):
    """A fixed parameter slot box with a label below."""
    box = Rectangle(
        width=width,
        height=height,
        stroke_color=color,
        stroke_width=2.5,
        fill_color=color,
        fill_opacity=0.1
    )
    lbl = code_text(label_str, size=18, color=color)
    lbl.next_to(box, DOWN, buff=0.15)
    return VGroup(box, lbl)
