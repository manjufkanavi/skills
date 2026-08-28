---
name: html-to-pdf
description: Convert HTML files to PDF on macOS using WeasyPrint in a venv (bypasses PEP 668 system block). Requires Homebrew pango. Handles bulk conversion with deduplication and merges into a single combined PDF.
tags: [html, pdf, weasyprint, macos, conversion]
---

# PDF and Document Processing

**Combined umbrella for PDF generation, PDF text editing, OCR/extraction, and document design.**
This skill covers: HTML→PDF conversion (WeasyPrint), natural-language PDF text editing (nano-pdf), PDF/scan OCR (pymupdf + marker-pdf), and Google DESIGN.md token specs.

## Table of Contents

- [1. HTML to PDF (WeasyPrint)](#1-html-to-pdf-weasyprint)
- [2. PDF Text Editing (nano-pdf)](#2-pdf-text-editing-nano-pdf)
- [3. PDF/OCR Extraction (pymupdf + marker-pdf)](#3-pdfocr-extraction-pymupdf--marker-pdf)
- [4. DESIGN.md Token Spec (design-md)](#4-designmd-token-spec-design-md)
- [5. HTML to PDF (Playwright Chromium)](#5-html-to-pdf-playwright-chromium)

---


## Overview

Convert HTML slideshow files (or any HTML) to PDF on macOS. Uses WeasyPrint in an isolated venv to bypass PEP 668 system pip restrictions. Requires Homebrew-installed `pango` library.

## Prerequisites

```bash
# 1. Install pango (WeasyPrint C dependency)
brew install pango glib gdk-pixbuf

# 2. Create isolated venv (uv preferred over pip — pip may be missing)
uv venv /tmp/pdf_converter_venv
uv pip install --python /tmp/pdf_converter_venv/bin/python weasyprint PyPDF2
```

## Required Environment Variable

**CRITICAL:** WeasyPrint's C extensions (Pango/GObject) need `DYLD_LIBRARY_PATH` on macOS:

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib /tmp/pdf_converter_venv/bin/python script.py
```

Without this, import fails with `OSError: cannot load library 'libgobject-2.0-0'`. Set this env var for EVERY Python execution that imports weasyprint.

## Single File Conversion

### Method 1: `uv run` (simplest for single files)

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run weasyprint input.html output.pdf
```

### Method 2: Python API (if `uv run` not available)

**IMPORTANT:** Do NOT use `python -m weasyprint` — it fails in the venv. Use the Python API:

```bash
/tmp/pdf_converter_venv/bin/python -c "
from weasyprint import HTML
HTML('input.html').write_pdf('output.pdf')
"
```

## Bulk Conversion Script

See `scripts/convert_html_to_pdf.py` (also available at `/tmp/convert_collection_pdf.py`) for the production-ready script that:
- Walks a directory tree for `.html` files
- Extracts poem/poet names for output naming
- Creates individual PDFs per HTML, then merges into a single combined PDF
- Uses **WeasyPrint Python API** (`from weasyprint import HTML`) — NOT the `-m` CLI which does not work in venv

**Usage:**
```bash
/tmp/pdf_converter_venv/bin/python /tmp/convert_collection_pdf.py
```

The script looks for HTML files and writes PDFs to `~/Desktop/<target_dir>/`.

## Combined PDF Creation

See `scripts/combine_pdfs.py` (also available at `/tmp/combine_pdfs.py`) for merging all PDFs in a directory into a single file using PyPDF2.

**Usage:**
```bash
/tmp/pdf_converter_venv/bin/python /tmp/combine_pdfs.py
```

## Method: Playwright Headless Chromium

Convert HTML→PDF using Playwright's headless Chromium (Node). Prefer this over WeasyPrint when you need CSS `page-break`, background colors, `@page` size/margins, or per-section pages (each section = one PDF page).

**Load this when:** "convert a report to PDF with page breaks / running footers / page numbers / background colors / per-section pages"

**One-time setup:**
```bash
npx playwright-core@latest install chromium
```

**Usage:**
```bash
node scripts/html2pdf.playwright.mjs input.html output.pdf Letter '{"top":"0.72in","bottom":"0.85in","left":"1in","right":"1in"}'
```

**Why prefer it:** WeasyPrint is great for bulk/simple conversion, but Chromium gives precise control over `@page` size, `page-break-after` per section, background colors, and running footers. Set `preferCssPageSize: true` to honor the CSS `@page` size (rather than forcing the viewport).

**See:** `references/bits-wilp-report-format.md` — a full BITS-Pilani report layout built on this method (US Letter, Times New Roman body, Calibri headings, running footers, accent numerals).

---

## Pitfalls

1. **PEP 668 blocks system pip** — macOS with `--break-system-packages` disabled. Always use a venv with `uv`. Don't try `pip install --system` or `--break-system-packages`.

2. **WeasyPrint needs pango** — `OSError: cannot load library 'libpango-1.0-0'`. Install via `brew install pango glib gdk-pixbuf` before running WeasyPrint.

3. **DYLD_LIBRARY_PATH missing** — WeasyPrint's C extensions need `DYLD_LIBRARY_PATH=/opt/homebrew/lib` set on macOS. Without this, import fails. **Always set this before every Python execution.**

4. **F-string + shell quoting** — Passing Python via `-c` with complex f-strings breaks shell quoting. Write a script file instead of inline `-c` for anything beyond trivial one-liners. This happened with WeasyPrint conversion of large combined_book.html files.

5. **Large files** — Each HTML-to-PDF takes 1-2 seconds for typical pages. For 50+ files, use the bulk script with a generous timeout. Timeout the process if needed.

6. **uv pip instead of pip** — Modern Python 3.13 on macOS ships without pip module. Use `uv pip install --python <venv> <packages>` instead of `<venv>/bin/pip install`.

7. **WeasyPrint `-m` CLI does NOT work** — `python -m weasyprint` in the venv fails. **Always use the Python API instead:**
   ```python
   from weasyprint import HTML
   HTML('input.html').write_pdf('output.pdf')
   ```
   Or write a script file that imports and uses the API directly.

8. **Bulk conversion via Python API** — For 50+ files, write a script that iterates with `HTML(path).write_pdf(out)` for each file, then merges with PyPDF2. The per-file conversion takes ~1-2 seconds each.

9. **Vision tool hallucination** — When converting/verifying a report, the vision tool may describe a *completely different, fabricated* document (it once reported a "Cloud Computing" report, then a "Global Macro Risk Report", for a single Solvarch PDF). **Trust programmatic ground truth, not the vision tool:** verify with pymupdf text extraction (`page.get_text()`) and pixel-color counts (confirm paper/ink/accent hex are present in the right proportions). See `references/bits-wilp-report-format.md` for the verification recipe.

- [4. DESIGN.md Token Spec (design-md)](#4-designmd-token-spec-design-md)

---

## 2. PDF Text Editing (nano-pdf)

Edit PDF text via natural language prompts using the `nano-pdf` CLI tool.

**Load this when:** "fix typo in PDF", "edit this PDF", "change text in PDF"

**Key constraint:** Requires an API key (configured in nano-pdf). Page numbers may be 0 or 1 based depending on the tool.

**Workflow:**
1. Load the PDF path
2. Issue natural language edit: "Replace 'foo' with 'bar' on page 3"
3. Verify output

**Pitfalls:**
- Always verify the edited PDF renders correctly after nano-pdf edits
- Page numbering: clarify 0-based vs 1-based when the PDF has multiple sections

---

## 3. PDF/OCR Extraction (pymupdf + marker-pdf)

Extract text from PDFs and scanned documents.

**Load this when:** "extract text from PDF", "OCR this scan", "read this document"

**Tool selection guide:**

| Tool | When to use | Install | Speed |
|------|-------------|---------|-------|
| `pymupdf` | Text-based PDFs, fast extraction, local-only | `pip install pymupdf` | Fast (local) |
| `marker-pdf` | Scanned documents needing OCR, complex layouts | ~3-5GB install | Heavy (OCR) |
| `web_extract` (Firecrawl) | URL-based documents (try first!) | N/A | Fast |

**Workflow preference:**
1. Try `web_extract` first for URLs
2. Use `pymupdf` for fast local text extraction
3. Fall back to `marker-pdf` only when OCR is needed

**See:** `references/pdf-ocr-workflow.md` for detailed tool comparison and usage patterns.

---

## 4. DESIGN.md Token Spec (design-md)

Author and validate Google's DESIGN.md token spec files.

**Load this when:** "author a DESIGN.md", "validate design tokens", "export design tokens"

**Key constraints:**
- YAML front matter for token definitions
- Markdown body for rationale
- Canonical section order enforced
- WCAG contrast validation
- Uses dotted paths (e.g., `{colors.primary}`)

**Workflow:**
1. Author tokens in YAML front matter
2. Write rationale in markdown body
3. Validate with DESIGN.md validator

---

## When to Use

- Converting HTML slideshows to printable PDFs
- Generating books/collections from web content
- Any HTML→PDF workflow on macOS with PEP 668 restrictions
- Building interview prep cheat sheets (use `templates/interview-cheatsheet-template.md` for structure)