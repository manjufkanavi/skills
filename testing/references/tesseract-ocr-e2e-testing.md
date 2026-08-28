# Real (Non-Mocked) OCR End-to-End Testing with Local Tesseract

When you need an end-to-end test that exercises **real OCR** on a document
pipeline (PDF/DOCX/image -> structured data) instead of a stubbed/mock external
service. Captured from the resume-platform `api/services/ocr.py` pipeline
(`extract_text_from_file` -> `parse_text_to_json` -> `calculate_ats_score`).

## When to use this

- The user asks to "run OCR locally" or test a document pipeline end-to-end.
- You want the test to catch real OCR failures (bad extraction, section
  misclassification) that a mock would hide.
- External services (resume-api, MinIO, Ollama) are unreachable offline, but a
  local OCR engine is installed.

## Prerequisites (verify before writing the test)

```bash
which tesseract        # local OCR engine binary (Homebrew: brew install tesseract)
.venv/bin/python -c "import pypdf, PIL; print('pypdf + PIL OK')"
```

`pypdf` extracts text from text-layered PDFs; PIL renders text to an image for
generating "scanned" PDFs. `pytesseract`/`easyocr`/`pdf2image`/`pymupdf` are
**not** required -- shell out to the `tesseract` binary directly.

## Core technique

### 1. Force the OCR path with a "scanned" PDF

A text-layered PDF extracts via pypdf (no OCR). To force the OCR path, render
text onto an image with PIL and save it as a PDF **with no text layer**:

```python
from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGB", (960, 520), "white")
draw = ImageDraw.Draw(img)
font = ImageFont.truetype("/System/Library/Fonts/Geneva.ttf", 30)  # larger = cleaner OCR
y = 45
for line in sample_lines:
    draw.text((30, y), line, fill="black", font=font); y += 66
buf = io.BytesIO(); img.save(buf, "PDF")   # embedded image, NO text layer
```

Sanity check that this actually has no text layer (so the test is meaningful):

```python
reader = PdfReader(io.BytesIO(buf.getvalue()))
assert not (reader.pages[0].extract_text() or "").strip()   # empty -> real OCR will run
```

### 2. Run the real pipeline

```python
from services.ocr import extract_text_from_file, parse_text_to_json
text = extract_text_from_file(pdf_bytes, "application/pdf")
parsed = parse_text_to_json(text)
```

### 3. OCR a scanned PDF with no text layer

Extract each embedded page image via `pypdf`'s `page.images` and OCR it with the
`tesseract` binary (write bytes to a temp `.png`, run `tesseract <file> stdout`):

```python
def _ocr_with_tesseract(image_bytes: bytes) -> str:
    import os, subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "ocr.png")
        open(path, "wb").write(image_bytes)
        result = subprocess.run(["tesseract", path, "stdout"],
                                capture_output=True, text=True, timeout=120)
    return result.stdout.strip()

# In extract_text_from_pdf, scanned path:
for page in reader.pages:
    for image in page.images:          # image.data = embedded image bytes
        text = _ocr_with_tesseract(image.data)
```

In `ocr.py`, `_ocr_with_tesseract` is wired as the fallback in both the image
path (when Surya isn't installed) and the scanned-PDF path.

## tesseract accuracy caveat

Tesseract is a **rule-based** OCR engine (no ML model). It is accurate on clean
rendered text but noisier on real scans (e.g. "reduction" -> "reductior"). Use
larger font sizes / higher resolution for cleaner output. If tesseract is
missing, skip the test rather than failing:

```python
import shutil
@pytest.mark.skipif(shutil.which("tesseract") is None,
                    reason="tesseract binary not installed")
```

## GOTCHA: `parse_text_to_json` header heuristic

Section detection has two constraints -- **both** must hold or a section is never
populated:

1. **Header line must be < 60 chars.** Lines >= 60 chars are never treated as
   headers, so they get swallowed into the current section.
2. **A header must be followed by body lines.** The parser only *saves* a
   section when body lines accumulate *after* the header. If every line is a
   header (no body after it), `sections` ends up empty and everything falls into
   `raw_text`.

Craft fixtures so each header is short (< 60 chars) and has body lines after it:

```python
SAMPLE_LINES = [
    "Summary: Senior software engineer.",          # header
    "Focused on building scalable microservices.", # body -> populates summary
    "Experience: Built microservices, 90% faster.", # header
    "Led distributed engineering teams.",          # body -> populates experience
    "Skills: Python, Docker, Kubernetes.",         # header + body...
    "Open source contributor and mentor.",
    "Education: BS Computer Science.",
    "Specialized in distributed systems.",
]
```

Assertions should be **substring-based** and lenient to tolerate OCR noise
("microservice" not "microservices"; "reductior" not "reduction").
