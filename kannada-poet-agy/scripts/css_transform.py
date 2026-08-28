#!/usr/bin/env python3
"""
Transform main.py CSS for PDF-safe rendering (no flexbox, fixed heights).

Run this to automatically apply the CSS fixes needed to prevent WeasyPrint
from creating empty orphan pages. Use as a reference for build scripts.

Usage: python3 scripts/css_transform.py <main.py>
"""
import re
import sys
from pathlib import Path

def transform_css(raw_css: str) -> str:
    """Apply all PDF-safe CSS transformations."""
    css = raw_css

    # 1. .content: flex → block with fixed height
    css = re.sub(
        r'\.content\s*\{[^}]*display:\s*flex[^}]*flex-direction:\s*column[^}]*\}',
        """.content {
  padding: 14mm 26mm 6mm 26mm;
  display: block;
  height: 238mm;
  overflow: hidden;
  position: relative;
  z-index: 5;
}""",
        css, flags=re.DOTALL
    )

    # 2. .closing: remove margin-top: auto
    css = re.sub(
        r'\.closing\s*\{[^}]*margin-top:\s*auto[^}]*\}',
        """.closing {
  padding-top: 8mm;
  text-align: center;
  margin-top: 0;
}""",
        css, flags=re.DOTALL
    )

    # 3. .meaning-card: flex → block
    css = re.sub(
        r'\.meaning-card\s*\{[^}]*display:\s*flex[^}]*flex-direction:\s*column[^}]*\}',
        """.meaning-card {
  position: relative;
  padding: 5mm 6mm;
  border-radius: 3px;
  border: 1px solid var(--rule-light);
  display: block;
  break-inside: avoid;
  margin-bottom: 4mm;
}""",
        css, flags=re.DOTALL
    )

    # 4. .lesson-item: flex → block
    css = re.sub(
        r'\.lesson-item\s*\{[^}]*display:\s*flex[^}]*flex-direction:\s*column[^}]*\}',
        """.lesson-item {
  position: relative;
  padding: 5mm 0 5mm 14mm;
  border-bottom: 1px solid var(--rule);
  display: block;
  break-inside: avoid;
}""",
        css, flags=re.DOTALL
    )

    # 5. Remove flex-shrink: 0 from .meaning-grid
    css = css.replace('flex-shrink: 0;', '')

    return css

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 css_transform.py <main.py>")
        sys.exit(1)

    main_py = Path(sys.argv[1])
    if not main_py.exists():
        print(f"File not found: {main_py}")
        sys.exit(1)

    content = main_py.read_text()
    start = content.find('<style>') + 7
    end = content.find('</style>')
    if start < 7 or end < 0:
        print("No <style> block found")
        sys.exit(1)

    raw = content[start:end]
    transformed = transform_css(raw)
    print(transformed)
