#!/usr/bin/env python3
"""Post-process markitdown PDF output that extracts words on separate lines."""
import sys, re

def clean_pdf_text(text):
    """Join lines split without proper spacing in PDFs."""
    lines = text.split('\n')
    joined = []
    buffer = ""
    for line in lines:
        line = line.strip()
        if not line:
            if buffer:
                joined.append(buffer)
                buffer = ""
            continue
        if buffer:
            if buffer.endswith('-') and line:
                buffer = buffer[:-1] + " " + line
            elif re.search(r'[.!?]$', buffer) and not line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                joined.append(buffer)
                buffer = line
            else:
                buffer += " " + line
        else:
            buffer = line
    if buffer:
        joined.append(buffer)
    return '\n\n'.join(joined)

def postprocess_md(text):
    """Remove page-number-only lines, page breaks, fix section headers."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip standalone page numbers
        if re.match(r'^\d+$', stripped) and cleaned and not re.match(r'^\d+\.\s', cleaned[-1]):
            continue
        if stripped == '\f' or stripped == '':
            continue
        cleaned.append(stripped)
    text = '\n'.join(cleaned)
    # Clean up section numbering artifacts
    text = re.sub(r'(\d+)\.\s+([A-Z][A-Za-z\s]+?)\s+(\d+)\.\s+', r'\n## \2\n\n', text)
    text = re.sub(r'\nContents\s*\n\s*\n\d+\.\s+\w', '', text)
    text = text.replace('## ##', '##')
    return text

if __name__ == '__main__':
    input_text = sys.stdin.read()
    # First clean lines, then postprocess
    cleaned = clean_pdf_text(input_text)
    final = postprocess_md(cleaned)
    print(final)
