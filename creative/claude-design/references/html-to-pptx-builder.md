# HTML-to-PPTX Slide Deck Builder

Convert a multi-slide HTML presentation into a `.pptx` file using Playwright + PyMuPDF + python-pptx.

## When to Use

- User asks to "build a PPTX from the HTML presentation"
- "Create a PowerPoint from the deck"
- "Export the HTML slides as PPTX"
- After building an HTML slide deck, user wants a downloadable .pptx

## Prerequisites

```bash
pip3 install --break-system-packages python-pptx PyMuPDF playwright
playwright install chromium
```

## Workflow

### 1. Render HTML slides to images

The HTML template has all `.page` slides. Extract each slide's HTML, render to PDF via Playwright, then convert PDF page to PNG via PyMuPDF.

```python
import os, re
from pathlib import Path
from playwright.sync_api import sync_playwright
import fitz  # PyMuPDF

PROJECT_ROOT = Path("/path/to/project")
HTML_SRC = PROJECT_ROOT / "path/to/template.html"
OUTPUT_DIR = PROJECT_ROOT / "output/pptx_images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

html_content = HTML_SRC.read_text()

# Extract individual slides by comment markers
slide_markers = [(m.start(), m.end()) for m in re.finditer(
    r'<!-- ==================== SLIDE \d+ —', html_content
)]

pages = []
for i, (start, _) in enumerate(slide_markers):
    end = slide_markers[i+1][0] if i+1 < len(slide_markers) else len(html_content)
    pages.append(html_content[start:end])

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for i, page_html in enumerate(pages[:12], 1):
        embedded = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
@page {{ size: A4 portrait; margin: 0; }}
body {{ background: #fafafa; display: flex; flex-direction: column; align-items: center; padding: 0; }}
.page {{ width: 210mm; min-height: 297mm; background: white; display: flex; flex-direction: column; overflow: hidden; }}
</style></head><body>{page_html}</body></html>"""
        tmp_html = OUTPUT_DIR / f"slide_{i:02d}.html"
        tmp_html.write_text(embedded)
        tmp_pdf = OUTPUT_DIR / f"slide_{i:02d}_temp.pdf"
        pg = browser.new_page(viewport={"width": 1920, "height": 2800})
        pg.goto(f"file://{tmp_html}")
        pg.wait_for_timeout(3000)
        pg.pdf(path=str(tmp_pdf), format="A4", print_background=True,
               margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"},
               prefer_css_page_size=True)
        pdf_doc = fitz.open(str(tmp_pdf))
        pix = pdf_doc[0].get_pixmap(dpi=200, matrix=fitz.Matrix(2, 2))
        pix.save(str(OUTPUT_DIR / f"slide_{i:02d}.png"))
        tmp_html.unlink(); tmp_pdf.unlink()
    browser.close()
```

### 2. Build the PPTX

```python
from pptx import Presentation
from pptx.util import Inches

prs = Presentation()
prs.slide_width = Inches(10)
prs.slide_height = Inches(7.5)

for i in range(1, 13):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    img_path = str(OUTPUT_DIR / f"slide_{i:02d}.png")
    slide.shapes.add_picture(img_path, Inches(0), Inches(0),
                             prs.slide_width, prs.slide_height)
prs.save(str(OUTPUT_DIR.parent / "presentation.pptx"))
```

### 3. Cleanup

```python
import shutil
shutil.rmtree(OUTPUT_DIR)
```

## Key Pitfalls

- **`page-break-after` doesn't work with Playwright PDF** — CSS page breaks are often ignored. Render each slide individually instead.
- **`data:` URLs may clip content** — Very long HTML via `data:text/html,` may not render fully. Write to a temp `.html` file.
- **Small image sizes (21 KB for A4)** — The viewport is clipping. Use `viewport={"width": 1920, "height": 2800}` to capture the full tall page.
- **Low DPI** — Default Playwright render produces blurry slides. Use PyMuPDF's `get_pixmap(dpi=200, matrix=fitz.Matrix(2, 2))` for sharp images.
- **Template CSS overrides** — Override `body { display: flex }` and `.page` display to show only the target slide. Hide nav bars with `display: none !important`.
- **python-pptx takes `Inches(0)` not `0`** — Left/top must be `Inches(0)`, not integer 0.

## Output Specs

- Each slide: ~140-200 KB PNG at 1653×2339 px (200 DPI A4)
- Final PPTX: typically 1-2 MB for 12 slides
- All images embedded, file is portable
