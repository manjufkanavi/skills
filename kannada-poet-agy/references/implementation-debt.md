# IMPLEMENTATION DEBT: pdf_gen.py integration with main.py

## What was done
The PDF generation pipeline was extracted into `skills/kannada-poet-agy/pdf_gen.py` (21K), with:
- `generate_combined_poem()` — renders individual poem HTML to PDF
- `generate_tatvapagalu_pdf()` — full multi-poem book with auto-fit overflow

## What needs to happen
The `main.py` batch runner calls `process_poem()` which generates `combined_book.html` but does NOT generate the PDF. The PDF generation should be integrated into the batch flow so that every poem processed also gets its PDF.

## Integration plan
In `main.py`'s `process_poem()` function, after `html_file` is created and committed:
1. Call `from skills.kannada-poet-agy.pdf_gen import generate_combined_poem`
2. Call `generate_combined_poem(poem_dir, poem_data, html_file)`
3. If successful, the PDF is saved alongside the HTML
4. If it fails (weasyprint not found, etc.), log warning but continue

## Also needed
A `generate_all_poems_pdf_batch()` function that processes all poems' HTML files → PDFs in sequence (1s gap between WeasyPrint calls to avoid rate limiting).

## Priority
Medium — PDF generation is working standalone, just not yet part of the batch workflow.