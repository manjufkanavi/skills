#!/usr/bin/env python3
"""Normalize tab-separated tables in a Markdown file into aligned, GitHub-renderable pipe-delimited tables.

Code fences (```text / ```yaml / ```json) are preserved verbatim, including any
union-syntax lines like `confidence: high|medium|low` that merely contain a pipe.
Indented list items (leading tab -> single field) are left alone: they are prose,
not tables.

Usage:
    python3 markdown_tables.py INPUT.md [OUTPUT.md]

This is a deterministic base formatter. Adapt edge cases for your doc, e.g.
tables with no explicit header row (the first data row is treated as the header),
or blocks whose intended column count differs from the widest observed row.
"""
import re
import sys


def split_pipe_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def is_sep_row(cells):
    """A row of only dashes/colons/spaces (the |---| separator)."""
    return all(c.strip() and re.fullmatch(r"[:\- ]+", c.strip()) for c in cells)


def is_table_like(line, fence_depth):
    if fence_depth % 2 == 1:          # inside a code fence -> never a table
        return False
    if line.startswith("\t"):         # indented list item -> not a table
        return False
    if "|" in line:                   # only delimited pipe rows count as tables
        s = line.strip()
        return s.startswith("|") or s.endswith("|")
    if "\t" in line:                  # tab-separated cell row (2-col+), not leading-tab
        return True
    return False


def flush_block(block, out):
    """Emit one table block as aligned pipe rows (header + separator + data)."""
    if len(block) <= 1:
        out.extend(b[0] for b in block)
        return
    data = [(o, c) for (o, c) in block if not is_sep_row(c)]
    ncols = max((len(c) for _, c in data), default=1)

    col_w = [0] * ncols
    for _, cells in data:
        cc = list(cells) + [""] * (ncols - len(cells))
        for k in range(ncols):
            col_w[k] = max(col_w[k], len(cc[k]))

    def render(cells):
        cc = list(cells) + [""] * (ncols - len(cells))
        return "| " + " | ".join(c.ljust(col_w[k]) for k, c in enumerate(cc)) + " |"

    sep = "| " + " | ".join("-" * col_w[k] for k in range(ncols)) + " |"
    out.append(render(data[0][1]))
    out.append(sep)
    for _, cells in data[1:]:
        out.append(render(cells))


def main():
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    out = []
    fence_depth = 0
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.strip().startswith("```"):
            fence_depth += 1
            out.append(line)
            i += 1
            continue
        if fence_depth % 2 == 1:
            out.append(line)
            i += 1
            continue

        if is_table_like(line, fence_depth):
            block = []
            while i < n and is_table_like(lines[i], fence_depth):
                if "|" in lines[i]:
                    cells = split_pipe_row(lines[i])
                else:
                    cells = [c.strip() for c in lines[i].split("\t")]
                block.append((lines[i], cells))
                i += 1
            flush_block(block, out)
            # ensure a blank line after the block for clean rendering
            if i < n and lines[i].strip() != "" and not lines[i].strip().startswith("```"):
                out.append("")
            continue

        out.append(line)
        i += 1

    result = "\n".join(out)
    result = re.sub(r"\n{3,}", "\n\n", result)

    with open(sys.argv[2] if len(sys.argv) > 2 else path, "w", encoding="utf-8") as f:
        f.write(result)


if __name__ == "__main__":
    main()
