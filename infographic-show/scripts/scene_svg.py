#!/usr/bin/env python3
"""
scene_svg.py — generate a full-bleed *cinematic scene* (SVG) that depicts a concept.

This is the "image generation via SVG" primitive. Instead of a text card (gradient +
title + bullets), it *paints a scene* — gradient sky, layered terrain, glow, and a
symbolic motif — that visually represents the narration concept. It is used inside
the theloop closed loop (generate -> render to PNG -> judge via ASCII view -> refine).

No mflux / no image model. Image generation is replicated with pure SVG.

Usage:
    python3 scene_svg.py --concept "meaning" --motif lighthouse --palette indigo --out scene.svg
    python3 scene_svg.py --concept "gratitude" --motif sunrise --palette amber --render-png scene.png

Motifs:  lighthouse, sprout, connected-nodes, stepping-stones, shield, sunrise, compass.
Palettes: indigo, teal, amber, emerald, rose, sky, violet.
"""

import argparse
import os

W, H = 1920, 1080

PALETTES = {
    "indigo": dict(sky_top="#0b1026", sky_mid="#1e2a5c", sky_bot="#3d2b6b", glow="#6366f1", accent="#818cf8"),
    "teal":   dict(sky_top="#04202a", sky_mid="#0c4a54", sky_bot="#0e7c6b", glow="#14b8a6", accent="#2dd4bf"),
    "amber":  dict(sky_top="#2a1a06", sky_mid="#7c4a12", sky_bot="#c77d1a", glow="#f59e0b", accent="#fbbf24"),
    "emerald":dict(sky_top="#05231a", sky_mid="#0a5c3a", sky_bot="#129a5a", glow="#10b981", accent="#34d399"),
    "rose":   dict(sky_top="#2a0a14", sky_mid="#7a1a3a", sky_bot="#c73a5e", glow="#f43f5e", accent="#fb7185"),
    "sky":    dict(sky_top="#08203a", sky_mid="#0e4d7c", sky_bot="#38bdf8", glow="#0ea5e9", accent="#38bdf8"),
    "violet": dict(sky_top="#1a0a2e", sky_mid="#4a2a6d", sky_bot="#8b5cf6", glow="#a855f7", accent="#c084fc"),
}

BODICE = {
    "lighthouse": "lighthouse", "sprout": "sprout", "connected-nodes": "connected-nodes",
    "stepping-stones": "stepping-stones", "shield": "shield", "sunrise": "sunrise", "compass": "compass",
}


def _def():
    return (
        '<defs>\n'
        '  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">\n'
        '    <stop offset="0%" style="stop-color:%(sky_top)s"/>\n'
        '    <stop offset="55%" style="stop-color:%(sky_mid)s"/>\n'
        '    <stop offset="100%" style="stop-color:%(sky_bot)s"/>\n'
        '  </linearGradient>\n'
        '  <radialGradient id="glow" cx="0.5" cy="0.42" r="0.62">\n'
        '    <stop offset="0%" style="stop-color:%(glow)s" opacity="0.85"/>\n'
        '    <stop offset="100%" style="stop-color:%(glow)s" opacity="0"/>\n'
        '  </radialGradient>\n'
        '  <filter id="soft"><feGaussianBlur stdDeviation="14"/></filter>\n'
        '  <filter id="softlg"><feGaussianBlur stdDeviation="3"/></filter>\n'
        '</defs>\n'
    ) % PALETTES[""]  # placeholder, replaced per-palette below


def _defs(pal):
    return (
        '<defs>\n'
        '  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">\n'
        '    <stop offset="0%" style="stop-color:%(sky_top)s"/>\n'
        '    <stop offset="55%" style="stop-color:%(sky_mid)s"/>\n'
        '    <stop offset="100%" style="stop-color:%(sky_bot)s"/>\n'
        '  </linearGradient>\n'
        '  <radialGradient id="glow" cx="0.5" cy="0.42" r="0.62">\n'
        '    <stop offset="0%" style="stop-color:%(glow)s" opacity="0.85"/>\n'
        '    <stop offset="100%" style="stop-color:%(glow)s" opacity="0"/>\n'
        '  </radialGradient>\n'
        '  <filter id="soft"><feGaussianBlur stdDeviation="14"/></filter>\n'
        '  <filter id="softlg"><feGaussianBlur stdDeviation="2.5"/></filter>\n'
        '</defs>\n'
    ) % pal


def _terrain(pal):
    # Three layered hills (depth via opacity) + foreground ground.
    return (
        '<rect width="%d" height="%d" fill="url(#sky)"/>\n'
        '<rect width="%d" height="%d" fill="url(#glow)"/>\n'
        '<path d="M0,700 C360,620 820,740 1920,660 L1920,1080 L0,1080 Z" '
        'fill="%(sky_bot)s" opacity="0.55"/>\n'
        '<path d="M0,780 C460,700 1080,830 1920,740 L1920,1080 L0,1080 Z" '
        'fill="%(sky_bot)s" opacity="0.75"/>\n'
        '<path d="M0,880 C560,820 1260,930 1920,860 L1920,1080 L0,1080 Z" '
        'fill="#000000" opacity="0.55"/>\n'
    ) % (W, H, W, H, pal["sky_bot"], pal["sky_bot"], pal["sky_bot"])


def motif_lighthouse(pal):
    # Tower with stripes + lamp + radiating beams on a rock.
    return (
        '<ellipse cx="0" cy="120" rx="150" ry="34" fill="#000000" opacity="0.35"/>\n'
        '<path d="M-58,118 L-40,-40 L40,-40 L58,118 Z" fill="%(glow)s" opacity="0.9"/>\n'
        '<path d="M-53,60 L-46,10 L46,10 L53,60 Z" fill="#ffffff" opacity="0.85"/>\n'
        '<path d="M-49,-10 L-43,-58 L43,-58 L49,-10 Z" fill="#ffffff" opacity="0.85"/>\n'
        '<rect x="-46" y="-70" width="92" height="16" fill="%(glow)s"/>\n'
        '<rect x="-30" y="-92" width="60" height="24" rx="4" fill="%(glow)s"/>\n'
        '<rect x="-18" y="-108" width="36" height="18" rx="3" fill="%(glow)s"/>\n'
        '<ellipse cx="0" cy="-98" rx="10" ry="8" fill="#fff" filter="url(#softlg)"/>\n'
        '<g opacity="0.28" filter="url(#soft)">\n'
        '  <path d="M0,-98 L380,-300 L380,-220 L0,-60 Z" fill="%s"/>\n'
        '  <path d="M0,-98 L380,-60 L380,20 L0,-40 Z" fill="%s"/>\n'
        '  <path d="M0,-98 L-340,-260 L-340,-180 L0,-60 Z" fill="%s"/>\n'
        '</g>\n'
    ) % (pal["glow"], pal["glow"], pal["glow"])


def motif_sprout(pal):
    # Soil mound + green stem + two leaves; a small sun.
    return (
        '<ellipse cx="0" cy="120" rx="140" ry="30" fill="#3a2a12" opacity="0.9"/>\n'
        '<path d="M-140,118 C-140,90 140,90 140,118 Z" fill="#4a3418"/>\n'
        '<path d="M0,110 C0,40 0,-20 0,-90" stroke="%s" stroke-width="10" fill="none" filter="url(#softlg)"/>\n'
        '<path d="M0,-30 C-46,-40 -66,-74 -40,-104 C-14,-80 18,-64 0,-30 Z" fill="%s"/>\n'
        '<path d="M0,-70 C46,-80 66,-114 40,-144 C14,-120 -18,-104 0,-70 Z" fill="%s"/>\n'
        '<circle cx="150" cy="-120" r="46" fill="%s" opacity="0.9"/>\n'
    ) % (pal["accent"], pal["accent"], pal["accent"], pal["glow"])


def motif_connected_nodes(pal):
    # Constellation of people/nodes connected by lines (social support).
    nodes = [(-140, 60, 30), (140, 70, 30), (-40, -40, 26), (90, -30, 26), (0, 96, 22), (-120, -70, 20)]
    lines = [(0, 2), (1, 3), (2, 4), (3, 4), (0, 5), (1, 3), (2, 5)]
    s = ''
    for a, b in lines:
        x1, y1, _ = nodes[a]; x2, y2, _ = nodes[b]
        s += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="%s" stroke-width="4" opacity="0.55"/>\n' % pal["accent"]
    for x, y, r in nodes:
        s += f'<circle cx="{x}" cy="{y}" r="{r+10}" fill="%s" opacity="0.25" filter="url(#soft)"/>\n' % pal["glow"]
        s += f'<circle cx="{x}" cy="{y}" r="{r}" fill="%s"/>\n' % pal["accent"]
        s += f'<circle cx="{x}" cy="{y}" r="{r-8}" fill="#ffffff" opacity="0.85"/>\n'
    return s


def motif_stepping_stones(pal):
    # A path of stones ascending diagonally (habits / discipline).
    s = ''
    stones = [(-160, 90, 60), (-70, 40, 64), (20, -8, 68), (100, -56, 72), (170, -104, 64)]
    for i, (x, y, r) in enumerate(stones):
        s += f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{int(r*0.42)}" fill="%s" opacity="0.9"/>\n' % pal["accent"]
        s += f'<ellipse cx="{x}" cy="{y-r*0.22}" rx="{r*0.7}" ry="{int(r*0.26)}" fill="#ffffff" opacity="0.35"/>\n'
    s += '<path d="M-220,120 C-60,60 120,0 240,-120" stroke="%s" stroke-width="6" stroke-dasharray="4 14" fill="none" opacity="0.7"/>\n' % pal["glow"]
    return s


def motif_shield(pal):
    # A shield standing firm (resilience) with a leaf/heart inside.
    return (
        '<path d="M0,120 C-110,90 -116,10 -116,-60 C-116,-120 -60,-150 0,-140 C60,-150 116,-120 116,-60 C116,10 110,90 0,120 Z" '
        'fill="%s" opacity="0.92"/>\n'
        '<path d="M0,108 C-96,82 -102,6 -102,-58 C-102,-110 -52,-136 0,-128 C52,-136 102,-110 102,-58 C102,6 96,82 0,108 Z" '
        'fill="%(sky_bot)s" opacity="0.9"/>\n'
        '<path d="M0,40 C-40,10 -46,-34 -18,-52 C-2,-62 0,-46 0,-36 C0,-46 2,-62 18,-52 C46,-34 40,10 0,40 Z" '
        'fill="%s" filter="url(#softlg)"/>\n'
    ) % (pal["glow"], pal["sky_bot"], pal["accent"])


def motif_sunrise(pal):
    # Sun rising over a horizon with rays + water reflection (gratitude / optimism).
    s = (
        '<circle cx="0" cy="-10" r="96" fill="%s" opacity="0.9"/>\n'
        '<circle cx="0" cy="-10" r="96" fill="%s" filter="url(#soft)"/>\n'
    ) % (pal["glow"], pal["glow"])
    for a in range(-70, 71, 14):
        rad = a * 3.14159 / 180
        x2, y2 = 640 * __import__("math").cos(rad), -10 + 640 * __import__("math").sin(rad)
        if y2 > -10:
            continue
        s += f'<path d="M0,-10 L{x2:.0f},{y2:.0f} L{x2*0.82:.0f},{y2*0.82:.0f} Z" fill="%s" opacity="0.22"/>\n' % pal["glow"]
    s += (
        '<rect y="20" width="%d" height="%d" fill="%(sky_bot)s" opacity="0.85"/>\n'
        '<rect y="20" width="%d" height="%d" fill="url(#glow)" opacity="0.28"/>\n'
        '<g opacity="0.5">\n'
        '  <path d="M0,60 L0,140" stroke="%s" stroke-width="8" opacity="0.5"/>\n'
        '  <path d="M-60,60 L-60,120" stroke="%s" stroke-width="6" opacity="0.4"/>\n'
        '  <path d="M60,60 L60,120" stroke="%s" stroke-width="6" opacity="0.4"/>\n'
        '</g>\n'
    ) % (W, H // 2, W, H // 2, pal["accent"], pal["accent"], pal["accent"])
    return s


def mot...[truncated]