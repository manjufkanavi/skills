#!/usr/bin/env python3
"""Combine all PDFs in a directory into one."""
import os
from PyPDF2 import PdfReader, PdfWriter

pdf_dir = os.path.expanduser("~/Desktop/shishunala_sharifa_pdfs")
output_path = os.path.join(pdf_dir, "Shishunala_Sharifa_Complete_Collection.pdf")

# Get all PDFs sorted, excluding the output itself
pdf_files = sorted([
    os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir)
    if f.endswith('.pdf') and f != 'Shishunala_Sharifa_Complete_Collection.pdf'
])

print(f"Combining {len(pdf_files)} PDFs...")

writer = PdfWriter()
total_pages = 0

for pdf_file in pdf_files:
    reader = PdfReader(pdf_file)
    num_pages = len(reader.pages)
    total_pages += num_pages
    for page in reader.pages:
        writer.add_page(page)

with open(output_path, "wb") as f:
    writer.write(f)

print(f"Combined {len(pdf_files)} PDFs into {output_path}")
print(f"Total pages: {total_pages}")

size = os.path.getsize(output_path)
print(f"File size: {size/1024/1024:.1f}MB")