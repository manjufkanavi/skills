#!/usr/bin/env python3
"""Convert HTML files to PDF and merge into a single combined PDF.

Uses WeasyPrint Python API (NOT the -m CLI which does not work in venv).
"""
import os
import sys

# Add the venv to path
sys.path.insert(0, "/tmp/pdf_converter_venv/lib/python3.11/site-packages")

from weasyprint import HTML
from PyPDF2 import PdfWriter, PdfReader

COLLECTION_DIR = "/Users/manjunathkanavi/.nanobot/workspace/personal_bot/shishunala-sharifa-collection/poems"
OUTPUT_PDF = "/Users/manjunathkanavi/.nanobot/workspace/personal_bot/shishunala-sharifa-collection/Shishunala_Sharifa_Collection.pdf"

def html_to_pdf(html_path, pdf_path):
    """Convert a single HTML file to PDF using WeasyPrint Python API."""
    try:
        HTML(filename=html_path).write_pdf(pdf_path)
        return True
    except Exception as e:
        print(f"  ✗ Failed: {os.path.basename(html_path)} - {e}")
        return False

def main():
    collection_path = COLLECTION_DIR
    dirs = sorted(os.listdir(collection_path))
    html_files = []
    for d in dirs:
        path = os.path.join(collection_path, d, "poem_slideshow.html")
        if os.path.exists(path):
            html_files.append((d, path))

    print(f"Found {len(html_files)} HTML files")
    print(f"Output: {OUTPUT_PDF}\n")

    # Step 1: Convert each HTML to individual PDF
    temp_pdfs = []
    success_count = 0
    fail_count = 0

    for i, (poem_name, html_file) in enumerate(html_files, 1):
        safe_name = "".join(c if c.isalnum() or c in ' _-' else '_' for c in poem_name)
        pdf_path = f"/tmp/poem_{i:03d}_{safe_name}.pdf"

        print(f"[{i}/{len(html_files)}] Converting: {poem_name}")
        if html_to_pdf(html_file, pdf_path):
            temp_pdfs.append(pdf_path)
            success_count += 1
        else:
            fail_count += 1

    print(f"\nConversion: {success_count} succeeded, {fail_count} failed")

    if success_count == 0:
        print("ERROR: No PDFs generated!")
        sys.exit(1)

    # Step 2: Merge all PDFs into one
    print(f"\nMerging {len(temp_pdfs)} PDFs...")

    writer = PdfWriter()
    for pdf_path in temp_pdfs:
        try:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            print(f"  ✗ Error merging {pdf_path}: {e}")

    with open(OUTPUT_PDF, 'wb') as f:
        writer.write(f)

    # Clean up temp files
    for pdf_path in temp_pdfs:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

    # Report
    file_size = os.path.getsize(OUTPUT_PDF)
    file_size_mb = round(file_size / 1024 / 1024, 2)
    print(f"\n✓ Combined PDF created: {OUTPUT_PDF}")
    print(f"  Pages: {len(writer.pages)}")
    print(f"  Size: {file_size_mb} MB")

if __name__ == "__main__":
    main()
