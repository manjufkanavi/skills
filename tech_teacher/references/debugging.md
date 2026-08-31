# Debugging & Pitfalls — tech_teacher pipeline

Durable lessons from building narrated teaching videos (Kubernetes architecture
video, 2026-08-31). Class-level: applies to any topic.

## Manifest null-image trap

`orchestrate.py` writes `manifest.json` with `"image": <path if exists else null>`.
If it runs BEFORE scene PNGs exist, every image is `null`, and
`build_video.py` composes black backgrounds silently.

**Fix:** generate scene images first, then regenerate the manifest (or patch
image paths). Re-run `orchestrate.py` after PNGs exist, or update the manifest
in place:

```bash
python3 -c "
import json, os
m = json.load(open('<workdir>/manifest.json'))
for i, s in enumerate(m['scenes'], 1):
    img = os.path.join('<workdir>/images', f'scene{i:02d}.png')
    s['image'] = img if os.path.exists(img) else None
json.dump(m, open('<workdir>/manifest.json','w'), indent=2)
"
```

## `--outdir` is a .mp4 FILE path, not a directory

`build_video.py --outdir <dir>` fails with:
```
Unable to choose an output format ... use a standard extension for the filename
Error opening output files: Invalid argument
```

`--outdir` (or the manifest `out` field) must be a `.mp4` file path. Omit
`--outdir` to use the manifest's `out`.

## cairosvg: undefined markers -> AttributeError

A `<line ... marker-end="url(#arrow)"/>` referencing a marker not defined in
`<defs>` crashes cairosvg:
```
AttributeError: 'NoneType' object has no attribute 'get'  (draw_markers)
```

**Fix:** define the marker in `<defs>` before use. See scripts/gen_diagrams.py
for a working pattern using xml.etree.ElementTree with an `arrow()` helper.

## cairosvg: unescaped & -> XML parse error

Literal `&` in text (e.g. `"A & B"`) breaks XML parsing:
```
xml.etree.ElementTree.ParseError: not well-formed (invalid token)
```

**Fix:** escape `&`, `<`, `>` in all text content. Prefer building SVGs with
python's `xml.etree.ElementTree` (it never lets raw text through) rather than
string concatenation. For string-built SVGs, run every label through an `esc()`
helper before it reaches the XML.

## ffmpeg 8.x: writing a single PNG needs -frames:v 1

```
The specified filename '.../bg.png' does not contain an image sequence pattern
Cannot write more than one file with the same name. Are you missing -update?
```

**Fix:** add `-frames:v 1` (or `-update 1`) when ffmpeg should emit exactly one
frame.

## Rendering diagrams reliably

Prefer `xml.etree.ElementTree` to build SVGs (entities/text handled safely), then
rasterize with cairosvg:
```bash
cairo scene.svg -o scene.png --output-width 1280 --output-height 720
```
