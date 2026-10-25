# Offline TTS + Reliable Diagram Rendering — tech_teacher

Session-specific detail for building narrated teaching videos when the hosted
Kokoro gateway is unreachable and cairosvg mis-renders fonts. Copy-paste starters;
adjust paths per machine.

## 1. Local Kokoro TTS fallback (hosted gateway unreachable)

When `orchestrate.py` fails to fetch the API key over SSH
(`Could not fetch API key from mkanavi@192.168.0.116 over SSH (returncode=255)`),
the homeserver is off-network. Generate TTS locally with the ONNX model instead:

```python
# gen_audio.py — one scene at a time, output MP3 for build_video.py
import os, re, subprocess

TTS = "/Users/manjunathkanavi/.hermes/skills/kokoro-tts/scripts/tts.py"
SCRIPT = "<workdir>/script.md"
OUTDIR = os.path.join("<workdir>", "audio")
os.makedirs(OUTDIR, exist_ok=True)

with open(SCRIPT) as f: text = f.read()
scenes = []
for m in re.finditer(r"##\s+(?:Scene\s+\d+[:\-]?\s*)?(.+)", text):
    scenes.append((m.group(1).strip(), m.group(0)))

for i, (title, block) in enumerate(scenes, 1):
    body = re.sub(r"\s+", " ", block.strip())
    out = os.path.join(OUTDIR, f"scene{i:02d}.mp3")
    if os.path.exists(out) and os.path.getsize(out) > 0: continue
    subprocess.run(["python3", TTS, body, "-v", "hm_omega",
                    "-s", "0.9", "-f", "mp3", "-o", out], check=True)
```

Notes:
- Requires `kokoro_onnx` installed + numpy/scipy. Model at
  `~/.hermes/skills/voice-bridge/assets/kokoro/model.onnx` (325 MB), voices at
  `voice-bridge/assets/voices-v1.0.bin`.
- Local model is slower per call (CPU ONNX) but fully offline — no SSH, no network.
- Tell the user which path ran; local quality is close but may differ from hosted.

## 2. Reliable diagram rendering with PIL + DejaVuSans

cairosvg does NOT resolve `Helvetica.ttc` reliably, causing titles to mis-align and
body text to truncate off the right edge / push off-center — silently. Use PIL with a
font bundled by matplotlib (DejaVuSans), measuring text width before drawing so nothing
exceeds the margin.

```python
import os
from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as fm

W, H = 1280, 720
def find_font():
    paths = ["/System/Library/Fonts/Helvetica.ttc",
             "/System/Library/Fonts/GillSans.ttc"]
    for f in fm.findSystemFonts():
        if any(k in os.path.basename(f).lower() for k in ("dejavu","helvetica")) \
           and f.endswith(".ttf"): paths.append(f)
    for c in paths:
        if os.path.exists(c): return c
    return fm.findfont(fm.FontProperties())

FONT_TITLE = ImageFont.truetype(find_font(), 46)
FONT_SUB   = ImageFont.truetype(find_font(), 28)
FONT_BODY  = ImageFont.truetype(find_font(), 34)

BG, BANNER, WHITE, CYAN, BODY = (13,27,42),(27,58,92),(255,255,255),(144,224,239),(224,225,221)

def wrap(text, font, max_w):
    d = ImageDraw.Draw(Image.new("RGBA",(1,1)))
    out, buf = [], []
    for para in text.split("\n"):
        if not para.strip(): out.append(" "); buf=[]; continue
        for w in para.split():
            test = (" ".join(buf)+" "+w).strip() if buf else w
            if d.textlength(test, font=font) <= max_w: buf.append(w)
            else: out.append(" ".join(buf)); buf=[w] if buf else []
        if buf: out.append(" ".join(buf)); buf=[]
    if buf: out.append(" ".join(buf))
    return [x for x in out]

def draw(title, subtitle, body_lines):
    img = Image.new("RGB",(W,H),BG); d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,150], fill=BANNER)
    d.text((W//2,60), title, font=FONT_TITLE, fill=WHITE, anchor="mm")
    d.text((W//2,130), subtitle, font=FONT_SUB, fill=CYAN, anchor="mm")
    y = 215; max_w = W - 180
    for raw in body_lines:
        if not raw.strip(): y += 30; continue
        for ln in wrap(raw, FONT_BODY, max_w):
            d.text((90,y), ln, font=FONT_BODY, fill=BODY); y += 62
    return img

img = draw("What is Polymorphism?", "poly = many, morphs = forms",
    ["One interface. Many implementations.",
     "Same method call, different behavior.",
     "Decided at RUNTIME (late binding).",
     "Makes C# code flexible and extensible."])
img.save("images/scene01.png")
```

Verify with `vision_analyze` on a full-width crop AND an edge crop before building the
video — confirm no line is clipped at the right margin and nothing is pushed off-center.
