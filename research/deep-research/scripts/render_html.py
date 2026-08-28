#!/usr/bin/env python3
"""
Render a deep-research markdown report to HTML using the heritage-essay template CSS.

Usage:
  python3 scripts/render_html.py <markdown_file>

This script:
1. Reads the markdown report
2. Converts it to HTML (headers, tables, code blocks, bold, italic, lists)
3. Extracts the CSS from `html_templates/03-heritage-essay.html`
4. Wraps the HTML content in a complete page with the same styling
5. Writes the output as `<slug>.html` next to the markdown file

The script is self-contained — no external dependencies beyond Python stdlib.

Example output filename:
  scale-up-grafana-monitoring-prometheus-12-million-metrics-20260728.html
  (derived from the markdown filename minus the `.md` extension)
"""
import os
import re
import sys
import glob

def find_template():
    """Find the heritage-essay template in any of these locations."""
    paths = [
        os.path.expanduser('~/hermes/skills/research/deep-research/html_templates/03-heritage-essay.html'),
        os.path.expanduser('~/hermes/skills/deep-research/html_templates/03-heritage-essay.html'),
        os.path.expanduser('~/.hermes/skills/research/deep-research/html_templates/03-heritage-essay.html'),
        os.path.expanduser('~/hermes/skills/deep-research/html_templates/03-heritage-essay.html'),
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    # Fallback: search from current directory
    candidates = glob.glob('**/html_templates/03-heritage-essay.html', recursive=True)
    for c in candidates:
        return c
    return None

def extract_css(template_path):
    """Extract the <style> block from an HTML template."""
    with open(template_path) as f:
        html = f.read()
    start = html.find('<style>') + len('<style>')
    end = html.find('</style>')
    if start < 0 or end < 0:
        return ''
    return html[start:end]

def md_to_html(text):
    """Convert markdown to HTML with proper semantic elements."""
    h = text

    # Code blocks (before inline code)
    h = re.sub(r'```(yaml|json|python|bash|txt)?\n(.*?)```',
               lambda m: '<pre class="code-block"><code>' +
                         m.group(2).replace('<', '&lt;').replace('>', '&gt;') +
                         '</code></pre>', h, flags=re.DOTALL)

    # Inline code
    h = re.sub(r'`([^`]+)`', r'<code>\1</code>', h)

    # Bold and italic
    h = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', h)
    h = re.sub(r'\*(.+?)\*', r'<em>\1</em>', h)

    # Headers — map to section-title classes
    h = re.sub(r'^# (.+)$', r'<h2 class="section-title">\1</h2>', h, flags=re.MULTILINE)
    h = re.sub(r'^## (.+)$', r'<h2 class="section-title">\1</h2>', h, flags=re.MULTILINE)
    h = re.sub(r'^### (.+)$', r'<h3 class="subsection-title">\1</h3>', h, flags=re.MULTILINE)
    h = re.sub(r'^#### (.+)$', r'<h4 class="subsection-title">\1</h4>', h, flags=re.MULTILINE)

    # Horizontal rules
    h = re.sub(r'^---$', '<hr class="section-divider">', h, flags=re.MULTILINE)

    # Tables (pipe-table syntax)
    lines = h.split('\n')
    new_lines = []
    in_table = False
    table_lines = []
    for line in lines:
        if line.strip().startswith('|') and '---' not in line and '::' not in line:
            if not in_table:
                in_table = True
                table_lines = [line]
            else:
                table_lines.append(line)
        else:
            if in_table:
                in_table = False
                rows = []
                for tl in table_lines:
                    cells = [c.strip() for c in tl.strip().rstrip('|').split('|') if c.strip()]
                    rows.append(cells)
                if len(rows) > 1:
                    header = rows[0]
                    body = rows[1:]
                    t = '<table class="report-table"><thead><tr>'
                    for hh in header:
                        t += '<th>' + hh + '</th>'
                    t += '</tr></thead><tbody>'
                    for row in body:
                        if len(row) == len(header):
                            t += '<tr>'
                            for cell in row:
                                t += '<td>' + cell + '</td>'
                            t += '</tr>'
                    t += '</tbody></table>'
                    new_lines.append(t)
                else:
                    new_lines.extend(table_lines)
            new_lines.append(line)
    # Handle table at end of file
    if in_table:
        rows = []
        for tl in table_lines:
            cells = [c.strip() for c in tl.strip().rstrip('|').split('|') if c.strip()]
            rows.append(cells)
        if len(rows) > 1:
            header = rows[0]
            body = rows[1:]
            t = '<table class="report-table"><thead><tr>'
            for hh in header:
                t += '<th>' + hh + '</th>'
            t += '</tr></thead><tbody>'
            for row in body:
                if len(row) == len(header):
                    t += '<tr>'
                    for cell in row:
                        t += '<td>' + cell + '</td>'
                    t += '</tr>'
            t += '</tbody></table>'
            new_lines.append(t)
    h = '\n'.join(new_lines)

    # Paragraphs
    h = re.sub(r'\n\n(.+?)\n\n', '\n<p>\1</p>\n', h)

    # Task lists
    h = re.sub(r'- \[x\] (.+)', r'<li class="task-done">' + chr(10003) + r' \1</li>', h)
    h = re.sub(r'- \[ \] (.+)', r'<li class="task-pending">' + chr(9744) + r' \1</li>', h)

    # Unordered lists
    h = re.sub(r'^- (.+)', r'<li>\1</li>', h, flags=re.MULTILINE)

    # Wrap consecutive <li> blocks in <ul>
    if '<li>' in h:
        parts = re.split(r'(<li>.*?</li>)', h)
        result = []
        li_buffer = []
        for part in parts:
            if part.startswith('<li>'):
                li_buffer.append(part)
            else:
                if li_buffer:
                    result.append('<ul>\n' + '\n'.join(li_buffer) + '\n</ul>')
                    li_buffer = []
                result.append(part)
        if li_buffer:
            result.append('<ul>\n' + '\n'.join(li_buffer) + '\n</ul>')
        h = ''.join(result)

    h = re.sub(r'\n{3,}', '\n\n', h)
    return h.strip()

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <markdown_file>")
        sys.exit(1)

    md_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(md_path):
        print(f"File not found: {md_path}")
        sys.exit(1)

    # Find template
    template_path = find_template()
    if not template_path:
        print("ERROR: Could not find html_templates/03-heritage-essay.html")
        sys.exit(1)

    # Extract CSS and markdown content
    with open(md_path) as f:
        md = f.read()

    css = extract_css(template_path)
    if not css:
        print("ERROR: Could not extract <style> block from template")
        sys.exit(1)

    # Convert markdown
    content_html = md_to_html(md)

    # Build output filename
    base = os.path.splitext(os.path.basename(md_path))[0]
    output_dir = os.path.dirname(md_path)
    output_path = os.path.join(output_dir, base + '.html')

    # Assemble HTML
    title = base.replace("-", " ").title()
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,300;1,400&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>

<header class="masthead page">
  <div class="masthead-rule"></div>
  <p class="masthead-tag">Research Report</p>
  <h1 class="masthead-title">{title}</h1>
  <p class="masthead-sub">Synthesized research findings.</p>
  <div class="masthead-rule-bottom"></div>
</header>

<article class="page article">
{content_html}
</article>

<footer class="report-footer page">
  <p>Deep Research Report &nbsp;·&nbsp; {os.popen("date +%B %Y").read().strip()}</p>
</footer>

</body>
</html>'''

    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Written: {output_path}")
    print(f"Size: {os.path.getsize(output_path)} bytes")

if __name__ == '__main__':
    main()
