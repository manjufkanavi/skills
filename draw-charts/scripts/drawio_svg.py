#!/usr/bin/env python3
"""
drawio_svg.py — Render a .drawio (mxGraphModel XML) to SVG, then PNG via cairosvg.

Fallback renderer for macOS where the draw.io desktop CLI hangs headless (no
display). Parses mxGraphModel XML, draws vertices/edges to SVG using cairosvg's
native primitives (rect/circle/polygon/path/text), then converts PNG.

Usage:
    python3 drawio_svg.py input.drawio -o out.png [-s SCALE] [--width W]
    python3 drawio_svg.py input.drawio -o out.svg   (svg only, no cairosvg needed)

Shapes handled: rectangle/rounded/cylinder/polygon/path/image/text.
Styles are parsed into a dict (draw.io `key=value;` format). This is NOT a full
mxGraph renderer — it covers the shapes used by this project's diagrams.
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET


def parse_style(style):
    """Parse a draw.io style string like 'rounded=1;fillColor=#fff' into dict."""
    if not style:
        return {}
    d = {}
    for part in re.split(r'(?<!\\);', style):
        if '=' in part:
            k, v = part.split('=', 1)
            d[k] = v.replace('\\;', ';')
    return d


def parse_points(points):
    """Parse draw.io points '[[0,1],[2,3]]' into list of (x,y) tuples."""
    if not points:
        return []
    pairs = re.findall(r'\[\s*([-\d.]+)\s*,\s*([-\d.]+)', points)
    return [(float(a), float(b)) for a, b in pairs]


def hex_to_rgba(h):
    """Convert #rrggbb to (r,g,b,a) tuple. Returns None if invalid/None."""
    if not h or h == 'none' or h == 'transparent':
        return None
    if h.startswith('#'):
        h = h[1:]
    try:
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r, g, b, 255)
    except ValueError:
        return None


class DrawioSVGRenderer:
    def __init__(self, xml_path):
        self.tree = ET.parse(xml_path)
        self.root = self.tree.getroot()
        # Build index of cells by id: (id, parent) -> element + geometry
        self.cells = {}          # id -> cell element (mxCell with data)
        self.geoms = {}          # id -> geometry element or None
        for cell in self.root.iter('mxCell'):
            cid = cell.get('id')
            geom = None
            for child in cell:
                if child.tag == 'mxGeometry':
                    geom = child
            self.cells[cid] = cell
            self.geoms[cid] = geom

    def _get_geom(self, cid):
        g = self.geoms.get(cid)
        if g is None:
            return {'x': 0, 'y': 0, 'width': 100, 'height': 40}
        return {
            'x': float(g.get('x', 0) or 0),
            'y': float(g.get('y', 0) or 0),
            'width': float(g.get('width', 100) or 0),
            'height': float(g.get('height', 40) or 0),
        }

    def _parent(self, cid):
        return self.cells[cid].get('parent', '1')

    def _children(self, parent_id):
        kids = [cid for cid in self.cells if self._parent(cid) == parent_id]
        return kids

    def _is_edge(self, cid):
        return self.cells[cid].get('edge') == '1'

    def _vertex(self, cid):
        return self.cells[cid].get('vertex') == '1'

    def _style(self, cid):
        return parse_style(self.cells[cid].get('style', ''))

    def _label(self, cid):
        return self.cells[cid].get('value', '')

    def render(self, scale=1.0):
        """Return (svg_string, width_px, height_px)."""
        parts = []
        # Determine canvas bounds from all cells with geometry
        minx, miny = float('inf'), float('inf')
        maxx, maxy = -float('inf'), -float('inf')
        for cid in self.cells:
            if self._is_edge(cid):
                continue
            g = self.get_geom_safe(cid)
            x, y, w, h = g['x'], g['y'], g['width'], g['height']
            if self._is_edge(cid):
                continue
            minx = min(minx, x)
            miny = min(miny, y)
            maxx = max(maxx, x + w)
            maxy = max(maxy, y + h)
        if minx == float('inf'):
            minx = miny = 0
            maxx = maxy = 100

        # Add padding and apply scale
        pad = 40 * scale
        minx -= pad
        miny -= pad
        maxx += pad
        maxy += pad

        svg_w = int((maxx - minx) * scale)
        svg_h = int((maxy - miny) * scale)

        # Draw edges first (behind vertices), then vertices
        # Group by parent so containers draw their children on top correctly.
        edges = [cid for cid in self.cells if self._is_edge(cid)]
        # vertices grouped by parent (1 = top-level)
        verts_by_parent = {}
        for cid in self.cells:
            if not self._is_edge(cid) and self._vertex(cid):
                verts_by_parent.setdefault(self._parent(cid), []).append(cid)

        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{svg_w}" height="{svg_h}" '
            f'viewBox="0 0 {svg_w} {svg_h}">')

        # White background
        parts.append(f'<rect x="0" y="0" width="{svg_w}" height="{svg_h}" '
                      f'fill="#ffffff"/>')

        def tx(x): return (x - minx) * scale
        def ty(y): return (y - miny) * scale

        # Draw edges
        for cid in edges:
            s = self._svg_edge(cid, tx, ty)
            if s:
                parts.append(s)

        # Draw vertices by parent (top-level first, then nested children on top)
        for pid in sorted(verts_by_parent.keys(), key=lambda p: (p != '1')):
            for cid in verts_by_parent[pid]:
                s = self._svg_vertex(cid, tx, ty)
                if s:
                    parts.append(s)

        # Container backgrounds should be drawn first among their group; we
        # draw them last within the parent so child nodes sit on top of the
        # container fill but containers still behind their children. To keep it
        # simple, draw non-container verts first then container verts last so
        # labels inside containers remain visible. Re-sort: draw containers late.
        parts.append('</svg>')

        svg = '\n'.join(parts)
        return svg, svg_w, svg_h

    def get_geom_safe(self, cid):
        g = self._get_geom(cid)
        return g

    def _svg_vertex(self, cid, tx, ty):
        cell = self.cells[cid]
        style = self._style(cid)
        shape = style.get('shape', '')
        label = self._label(cid)
        g = self._get_geom(cid)
        x, y, w, h = tx(g['x']), ty(g['y']), g['width'], g['height']
        fill = hex_to_rgba(style.get('fillColor'))
        stroke = hex_to_rgba(style.get('strokeColor'))

        # Container (dashed box) — draw as rect with dashed stroke if requested
        dashed = '1' in style.get('dashArray', '') or \
            (style.get('dashed') == '1' and style.get('shape', '') != 'rect')
        dash_style = ''
        if dashed and style.get('dashArray'):
            ds = re.sub(r'\s*', '', style['dashArray'])
            dash_style = f' stroke-dasharray="{ds.replace(" ", "")}"'

        rounded = style.get('rounded') == '1'
        arc = style.get('arcSize', '')
        rx = ''
        if rounded and arc:
            try:
                av = float(arc) / 100.0 * (min(w, h) if min(w, h) > 0 else 1)
                rx = f' rx="{int(av)}" ry="{int(av)}"'
            except ValueError:
                pass

        # Image shape (client logos) — try to draw a placeholder box if we can't
        img = style.get('shape', '') == 'image' or \
            ('backgroundImage=' in (style.get('fillColor', '') if False else ''))
        image_bg = 'backgroundImage=' in (style.get('fillColor', '') or '')

        # Determine if this is an image shape via style key
        img_shape = False
        for k in ('shape', 'fillColor'):
            if style.get(k, '').startswith('mxgraph') or \
               ('image=' in (style.get('fillColor', '') if False else '')):
                pass
        # Check for mxgraph shape (icons) — has 'shape=mxgraph...' or is a known icon
        if style.get('shape', '').startswith('mxgraph') or \
           (style.get('aspect') == 'fixed' and style.get('points')):
            return self._svg_icon(cid, x, y, w, h)

        # cylinder3 -> database
        if shape == 'cylinder3':
            return (f'<g>'
                    f'<path d="M{x},{y} '
                    f'L{x},{y+h} '
                    f'A{w/2:.1f},{h*0.3:.1f} 0 0 0 {x+w},{y+h} '
                    f'L{x+w},{y} '
                    f'A{w/2:.1f},{h*0.3:.1f} 0 0 0 {x},{y} Z" '
                    f'fill="{self._fmt(fill)}" '
                    f'stroke="{self._fmt(stroke)}" stroke-width="2"/>'
                    f'<ellipse cx="{x+w/2:.1f}" cy="{y:.1f}" '
                    f'rx="{w/2:.1f}" ry="{h*0.3:.1f}" '
                    f'fill="{self._fmt(fill)}" stroke="{self._fmt(stroke)}"/>'
                    f'{self._svg_label(label, x, y, w, h)}</g>')

        # polygon/path shapes (kubernetes icons) — draw a rounded rect placeholder
        if style.get('points'):
            pts = parse_points(style['points'])
            if pts and w > 0 and h > 0:
                poly = ' '.join(f'{tx(0)+p[0]*w:.1f},{ty(0)+p[1]*h:.1f}' for p in pts)
                return (f'<polygon points="{poly}" '
                        f'fill="{self._fmt(fill)}" '
                        f'stroke="{self._fmt(stroke)}" stroke-width="2"/>'
                        + self._svg_label(label, x, y, w, h))

        # Default: rounded or plain rectangle
        if shape == 'rect' and style.get('rounded') != '1':
            rx = ''
        rect_attrs = (f'fill="{self._fmt(fill)}" ' if fill else 'fill="none" ')
        stroke_attr = (f'stroke="{self._fmt(stroke)}"' if stroke else '')
        dash_attr = (dash_style or ('' if not dashed else ' stroke-dasharray="4 4"'))
        return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                f'height="{h:.1f}"{rx} {rect_attrs} {stroke_attr}{dash_attr}/>'
                + self._svg_label(label, x, y, w, h))

    def _svg_icon(self, cid, x, y, w, h):
        """Draw a colored rounded-rect placeholder for mxgraph icons (with emoji-ish marker)."""
        style = self._style(cid)
        fill = hex_to_rgba(style.get('fillColor')) or (48, 120, 200, 255)
        stroke = hex_to_rgba(style.get('strokeColor')) or (255, 255, 255, 255)
        # Draw a subtle rounded rect as icon placeholder (icon image not embedded,
        # but the shape + color communicates intent)
        return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                f'height="{h:.1f}" rx="6" ry="6" '
                f'fill="{self._fmt(fill)}" '
                f'stroke="{self._fmt(stroke)}" stroke-width="2"/>'
                + self._svg_label(self._label(cid), x, y, w, h))

    def _svg_edge(self, cid, tx, ty):
        g = self._get_geom(cid)
        style = self._style(cid)
        color = hex_to_rgba(style.get('strokeColor')) or (72, 111, 165, 255)
        width = float(style.get('strokeWidth', '2') or '2')

        # Find source and target points from geometry
        src_pt = None
        tgt_pt = None
        geom_el = self.geoms.get(cid)
        if geom_el is not None:
            for sp in geom_el.findall('SourcePoint'):
                src_pt = (float(sp.get('x', 0)), float(sp.get('y', 0)))
            for tp in geom_el.findall('TargetPoint'):
                tgt_pt = (float(tp.get('x', 0)), float(tp.get('y', 0)))

        # Fallback: use source/target cell ids to get their centers
        if src_pt is None or tgt_pt is None:
            src_id = self.cells[cid].get('source')
            tgt_id = self.cells[cid].get('target')
            if src_id and src_id in self.geoms:
                sg = self._get_geom(src_id)
                src_pt = (sg['x'] + sg['width'] / 2, sg['y'] + sg['height'] / 2)
            if tgt_id and tgt_id in self.geoms:
                tg = self._get_geom(tgt_id)
                tgt_pt = (tg['x'] + tg['width'] / 2, tg['y'] + tg['height'] / 2)

        if not src_pt or not tgt_pt:
            return None

        s = f'<line x1="{tx(src_pt[0]):.1f}" y1="{ty(src_pt[1]):.1f}" '
        s += f'x2="{tx(tgt_pt[0]):.1f}" y2="{ty(tgt_pt[1]):.1f}" '
        s += f'stroke="{self._fmt(color)}" stroke-width="{width}" '
        s += 'stroke-linecap="round"/>'

        # Arrowhead — simple polygon at target
        dx = tgt_pt[0] - src_pt[0]
        dy = tgt_pt[1] - src_pt[1]
        mag = (dx * dx + dy * dy) ** 0.5
        if mag > 0:
            ux, uy = dx / mag, dy / mag
            px, py = -uy, ux  # perpendicular
            ah = 10
            base_x = tx(tgt_pt[0] - ux * 8)
            base_y = ty(tgt_pt[1] - uy * 8)
            tip_x = tx(tgt_pt[0])
            tip_y = ty(tgt_pt[1])
            p1x, p1y = base_x + px * ah / 2, base_y + py * ah / 2
            p2x, p2y = base_x - px * ah / 2, base_y - py * ah / 2
            s += (f'<polygon points="{tip_x:.1f},{tip_y:.1f} '
                  f'{p1x:.1f},{p1y:.1f} {p2x:.1f},{p2y:.1f}" '
                  f'fill="{self._fmt(color)}"/>')

        # Edge label (if any)
        lbl = self._edge_label(cid)
        if lbl:
            mx = (tx(src_pt[0]) + tx(tgt_pt[0])) / 2
            my = (ty(src_pt[1]) + ty(tgt_pt[1])) / 2
            s += (f'<rect x="{mx-30:.1f}" y="{my-12:.1f}" width="60" height="24" '
                  f'fill="#ffffff" stroke="#ccc" rx="3"/>'
                  f'<text x="{mx:.1f}" y="{my+4:.1f}" font-size="12" '
                  f'text-anchor="middle" fill="#333">{lbl}</text>')
        return s

    def _edge_label(self, cid):
        # Labels on edges are stored as child mxCells with vertex=1 and parent=cid
        for c in self.cells.values():
            if c.get('parent') == cid and c.get('vertex') == '1':
                return self._label(c.get('id', ''))
        return None

    def _svg_label(self, label, x, y, w, h):
        if not label:
            return ''
        # Wrap newlines into tspan
        lines = label.split('\n')
        if len(lines) == 1:
            cx = x + w / 2
            cy = y + h / 2 if h > 0 else y
            anchor = 'middle'
        else:
            cx = x + w / 2
            cy = y + h * 0.3 if h > 0 else y
            anchor = 'middle'
        ts = ''.join(
            f'<tspan x="{cx:.1f}" dy="{dy}">{DrawioSVGRenderer._esc(l)}</tspan>'
            for i, l in enumerate(lines)
            for dy in (('0', ) if i == 0 else ('1.2em', ))
        )
        return (f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="13" '
                f'text-anchor="{anchor}" fill="#222">{ts}</text>')

    @staticmethod
    def _fmt(c):
        if c is None:
            return 'none'
        r, g, b = c[0], c[1], c[2]
        a = c[3] if len(c) > 3 else 255
        return f'rgba({r},{g},{b},{a/255:.2f})'

    @staticmethod
    def _esc(s):
        return (s.replace('&', '&amp;').replace('<', '&lt;')
                .replace('>', '&gt;'))


def main():
    ap = argparse.ArgumentParser(description='Render .drawio to SVG/PNG')
    ap.add_argument('input', help='path to input .drawio file')
    ap.add_argument('-o', '--output', help='output path (.png or .svg)')
    ap.add_argument('-s', '--scale', type=float, default=1.0)
    ap.add_argument('--width', type=int, help='target width in px')
    args = ap.parse_args()

    out = args.output or 'out.png'
    renderer = DrawioSVGRenderer(args.input)

    if out.lower().endswith('.svg'):
        svg, w, h = renderer.render(args.scale)
        with open(out, 'w') as f:
            f.write(svg)
        print(f'Wrote {out} ({w}x{h})')
        return

    # PNG: render SVG then convert with cairosvg
    svg, w, h = renderer.render(args.scale)
    if args.width:
        scale = args.width / w if w > 0 else 1.0
        svg, w, h = renderer.render(scale)

    import cairosvg
    png_bytes = cairosvg.svg2png(bytestring=svg.encode('utf-8'),
                                  scale=max(args.scale, 1.0))
    with open(out, 'wb') as f:
        f.write(png_bytes)
    print(f'Wrote {out} ({w}x{h})')


if __name__ == '__main__':
    main()
