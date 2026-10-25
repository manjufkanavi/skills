---
name: markdown-formatting
description: "Format Markdown docs for clean GitHub rendering."
version: 1.0.0
license: MIT
author: Hermes Agent
tags: [markdown, formatting, tables, github-flavored]
metadata:
  hermes:
    tags: [markdown, formatting, tables, github-flavored]
    related_skills: [github/github]
---

# Markdown Formatting & Repair

Take a messy or legacy-formatted Markdown document and produce clean, consistently-rendered output. The two things that most often break rendering are **tab-separated "tables"** (which GitHub shows as raw text, not a table) and content inside **code fences** that gets accidentally reformatted. This skill converts the former without touching the latter.

## When to Use

- A Markdown document renders poorly on GitHub — raw text where tables should be, or a table that never rendered.
- You need to convert tab-separated "tables" into aligned pipe-delimited rows with a header + separator.
- A doc contains code fences or union-syntax content (`confidence: high|medium|low`) that must survive a formatting pass untouched.
- You are reformatting or restructuring an existing doc (README, design spec) and want consistent output.

## Always-On Rules

- **Never reformat anything inside a code fence.** A ```text / ```yaml / ```json block is verbatim. Lines like `confidence: high|medium|low` or `{ "verdict": "PASS|FAIL" }` contain pipes but are *not* table rows — leave them exactly as-is.
- **Tab-separated "tables" do not render.** GitHub ignores whitespace-delimited columns; convert them to aligned `|`-delimited pipe rows with a header + separator (`|---|`) so they render as real tables.
- **Every row in a table block must share the same column count.** The header, separator, and all data rows align on one column width; a mismatched row leaves empty trailing cells.
- **Indented list items are not tables.** A line starting with a tab that splits into one field is prose (e.g. "Architect / PM: Sections 2–3…"), not a table — preserve it as-is.
- **Keep heading structure intact.** Numbered sections (1., 4.1, …) are cross-referenced elsewhere in the doc; never renumber or drop them while formatting.

## Procedure

1. **Read the whole doc** and map its structure: headings, fenced blocks (```text/```yaml/```json), table-like rows, and list items. Know what is a table vs content before touching anything.
2. **Preserve code fences verbatim.** Walk line by line tracking fence depth; emit fenced content untouched. Union-syntax pipe lines inside fences are data, not tables.
3. **Convert tab-separated table rows to aligned pipe rows.** Group consecutive non-fenced, non-indented tab/cell lines into one block; compute each column's max width and emit `| cell |` rows padded to equal widths, with a `|---|` separator after the header.
4. **Normalize spacing.** Collapse 3+ consecutive blank lines to a single blank line; ensure one blank line around tables and headings for clean rendering.
5. **Verify output.** Confirm every table block has a header + separator + data rows all sharing column count, no union-syntax line was turned into a table row, and headings are unchanged.

A deterministic base formatter is in `scripts/markdown_tables.py` — run it as a starting point and adapt edge cases (e.g. tables with no explicit header row). See `references/table-conversion-pitfalls.md` for the pitfalls by type.

## Pitfalls

- **Turning a union-syntax line into a table row.** A pipe inside `high|medium|low` is value syntax, not column delimiting. Only treat a line as a table row if it's delimited (`|…|`) or tab-separated — never because it merely contains a `|`.
- **Converting an indented list item into a table.** Lines beginning with a tab that yield one field are prose bullets, not rows. Detect tables by content shape (2+ fields), not merely by the presence of a tab character.
- **Creating empty trailing cells.** If data rows have fewer columns than the widest row, padding adds blank cells. Reconcile counts so header and data agree before emitting.
- **Reformatting content inside a code fence.** Fenced blocks are verbatim; the formatter must track ``` depth and skip them entirely, or it will mangle JSON/YAML/ASCII diagrams.
- **Breaking cross-referenced headings.** Numbered section titles are linked from other sections; formatting must preserve them verbatim rather than "cleaning" the numbering.
