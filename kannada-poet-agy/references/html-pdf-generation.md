# HTML-to-PDF Generation for Kannada Poetry

## Quick Reference

### For Individual Poems
```python
from skills.kannada-poet-agy.pdf_gen import generate_combined_pdf
generate_combined_pdf(poem_dir, poem_data, html_file)
```
Single call — renders the poem's `combined_book.html` to PDF. Handles diagnostics (empty/low-content detection).

### For Full Books (Tatvapadagalu-style)
```python
from skills.kannada-poet-agy.pdf_gen import generate_tatvapagalu_pdf
generate_tatvapadagalu_pdf(poems_dir=..., skill_dir=..., repo_dir=...)
```
Per-page rendering with auto-fit overflow. ~52 pages, 0 empty. See `pdf_gen.py` for details.

## Architecture

### CSS (baked into main.py)
The template CSS uses `display: block` throughout (no flexbox on content). No transformation needed before rendering. Key: `break-inside: avoid` on cards/lessons, tight padding/line-heights.

### Rendering Strategy
**Individual page → individual PDF → merge** (not single-HTML):
- Each `.page-base` page renders independently
- If overflow detected (>1 pages), surgical font-size reduction on specific selectors
- If still overflows, aggressive 2nd pass (all fonts → 7pt)
- Merged with pypdf

### Why not single-HTML?
Single-HTML + page-break-after creates inconsistent page counts because content overflows from page to page unpredictably. Per-page rendering with overflow detection + retry gives reliable 1-page-per-page output.

## Known Constraints
- WeasyPrint slow with Kannada: 30-60s per page
- PDF venv at `/tmp/pdf_venv` — verify exists before rendering
- pypdf for PDF merge (import from pypdf, not PyPDF2)

## Legacy Troubleshooting (superseded by pdf_gen.py)
The old approach of single-HTML generation crashed WeasyPrint with `IndexError` on large documents. The per-page rendering approach bypasses this entirely. The old `references/html-pdf-generation.md` content has been consolidated into this page.
