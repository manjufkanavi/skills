# BITS Pilani WILP Report Format — Extracted Metrics

Reverse-engineered from the official **BITS Pilani WILP midsem report** (`../.corpus_backup/midsem_report.pdf`) and applied to the Solvarch final report. These are the concrete tokens to reproduce the institutional look without re-extracting from the PDF.

## Page & Layout

| Property | Value | Evidence |
|---|---|---|
| Page size | **US Letter** 8.5 × 11 in (612 × 792 pt) | `mediabox` of midsem report |
| Margins | top 0.72″, bottom 0.85″, left/right 1.0″ | letterbox |
| Content width | ~6.5 in | |
| Body text | **Times New Roman, 11 pt**, justified | span extraction |
| Running footer | section name (left, italic) + page number (right), 8 pt serif | |

## Typography

| Element | Font | Size | Weight | Case |
|---|---|---|---|---|
| Institutional header | Times New Roman | 11 pt | 400 | **UPPERCASE**, letter-spaced |
| Report title | Calibri | 19–20 pt | 800 | Title case |
| Section heading (h1) | Calibri | 14 pt | 800 | **UPPERCASE** |
| Subsection (h2) | Calibri | 12 pt | 700 | **UPPERCASE** |
| Section label | Calibri | 9.5 pt | 700 | UPPERCASE, tracked 0.08em |
| Field labels | Calibri | 11–12 pt | 400 | Title case |
| Abstract | Times New Roman | 10.5 pt | 400 | justified |
| Captions / footers | Times New Roman | 9 pt | 400 | — |
| Code / equation | monospace | 9 pt | 400 | — |

## Color System (Scholarly Ink)

| Token | Hex | Role |
|---|---|---|
| `--paper` | `#fdfcf8` | page background (warm off-white) |
| `--ink` | `#1c2833` | primary text / headings (charcoal) |
| `--text` | `#2f3942` | body text |
| `--muted` | `#6b7280` | secondary / rule text |
| `--accent` | `#0f5b5b` | section numerals, table header, key highlights (deep teal) |
| `--accent-2` | `#c29a3f` | subtle gold accent (rules, numerals on dark) |
| `--rule` | `#ddd8ca` | hairlines |

Applied pixel proportions on the generated cover (2× Letter): paper 88.5%, navy 1.1%, teal 0.08%, gold 0.05% — restrained, professional.

## Components

1. Cover — institution header (uppercase serif), report title (sans 800), author/meta block, abstract sheet card.
2. Abstract — justified block with a 4pt left accent rule.
3. Section header — 2-digit "01" numeral in accent box + "SECTION — NAME" (sans uppercase) + hairline.
4. Finding callout — light teal block, 4pt left bar, bold lead-in.
5. LoRA / hyperparameter table — accent header row, hairline separators, aligned numerics.
6. Benchmark table — three configuration columns, bold best-value cells.
7. Equation — monospace block, centered, inline `dW = (α/r)·B·A`.
8. Glossary — two-column definition table.
9. References — numbered, hanging indent.

## How to reverse-engineer a reference PDF (pymupdf)

```python
import fitz
doc = fitz.open("reference.pdf")
page = doc[0]

# 1. Page size (mediabox), in points
print(page.mediabox)                 # Rect(0, 0, 612, 792) -> US Letter

# 2. Font + size + flags per text span (decode flags: bit0=italic, bit1=bold, bit2=uppercase)
data = page.get_text("dict")
for block in data["blocks"]:
    if "lines" not in block: continue
    for line in block["lines"]:
        for span in line["spans"]:
            font = span["font"]
            size = span["size"]
            flags = span["flags"]     # 4 => uppercase, 20 => uppercase+bold(sans)
            print(size, font, flags)

# 3. Plain top-to-bottom text for structure
print(page.get_textbox(page.mediabox))

# 4. Render a page to PNG at scale 2.0 for visual/verification
M = fitz.Matrix(2.0, 2.0)
page.get_pixmap(matrix=M).save(f"page_{i}.png")
```

## Verifying the generated PDF was styled correctly (don't trust the vision tool)

The **vision tool hallucinates fabricated reports** — it described a "Cloud Computing" report, then a "Global Macro Risk Report", neither matching the actual file. **Trust programmatic ground truth instead:**

```python
import fitz, numpy as np
from PIL import Image
img = fitz.open("report.pdf")
img[0].get_pixmap(matrix=fitz.Matrix(2.0,2.0)).save("cover.png")
img.close()

im = np.asarray(Image.open("cover.png"))
H, W = im.shape[:2]
rgb = im[..., :3].reshape(-1, 3)
def near(c, tol=35):
    d = ((rgb - c) ** 2).sum(1)
    return int((d < tol*tol).sum())

# Confirm your palette + page size actually landed in the PDF:
print(f"size {W}x{H}  paper{near((253,252,248)):.0f}  navy{near((28,40,51)):.0f}  teal{near((15,91,91)):.0f}  gold{near((194,154,63)):.0f}")
```

A correct render shows cream paper as the dominant color (~85%+) with navy/teal/gold present in small proportions. If the vision tool's description contradicts this, ignore it — the pixel counts + text extraction are authoritative.
