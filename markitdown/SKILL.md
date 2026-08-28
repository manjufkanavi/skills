---
name: markitdown
description: Convert PDF, PPTX, DOCX, HTML, and other files to Markdown using Microsoft's markitdown tool. Handles re-reading already-converted docs, cleaning PDF extraction artifacts, and formatting for downstream analysis.
version: 1.0.0
tags: [conversion, pdf, pptx, docx, markdown, document-processing]
---

# MarkItDown — PDF/PPTX/DOCX to Markdown Converter

Convert PDFs, PPTX presentations, DOCX documents, and other files to clean Markdown.

## Installation

```bash
uv venv markitdown-env && source markitdown-env/bin/activate
uv pip install "markitdown[all]" pypdf pdfplumber
```

**Critical:** Always use a venv — never `--break-system-packages` on macOS native Python. The `"markitdown[all]"` extra includes pdf, pptx, docx, and image converters. You also need `pypdf` and `pdfplumber` explicitly installed.

## Usage

```bash
source /path/to/markitdown-env/bin/activate
python3 -m markitdown input.pdf --output output.md
python3 -m markitdown presentation.pptx --output slides.md
python3 -m markitdown document.docx --output doc.md
```

## PDF Pitfalls

- **Words on separate lines:** Some PDFs extract with words on separate lines (no space characters between words). This is common in academic papers and government docs. Always post-process.
- **Page numbers and footers** appear as orphan lines — filter them out.
- **Section numbering** often gets mixed with body text — clean with regex patterns.

## Post-processing

Use the included `scripts/postprocess_pdf.py` to clean PDF extraction artifacts:

```bash
source markitdown-env/bin/activate
python3 -m markitdown input.pdf --output /dev/stdout | python3 scripts/postprocess_pdf.py > clean_output.md
```

The script:
1. Joins lines that were split without proper spacing
2. Removes standalone page numbers
3. Removes page break markers (form feeds)
4. Cleans up section numbering artifacts
5. Fixes double-`##` headers

## Workflow

1. Convert source → markdown with markitdown
2. Post-process to fix PDF artifacts
3. Verify content is readable (not single words per line)
4. Use cleaned markdown for analysis, summarization, or further processing

## Linked Files

- `scripts/postprocess_pdf.py` — Script to clean PDF extraction artifacts (word-wrapping issues, page numbers, section numbering)
- `scripts/convert.sh` — Convenience script to convert multiple PDF/PPTX/DOCX files at once with automatic post-processing