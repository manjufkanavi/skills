# Table-Row Classification Pitfalls

When normalizing a Markdown doc, the first decision per line is "is this a table row?" Getting it wrong either mangles content (a union-syntax or list line turned into a table) or leaves real tables un-rendered. Classify by shape, in this order.

## 1. Is it inside a code fence?
- If the line is between ``` markers, **leave it verbatim**. Fenced content (```text diagrams, ```yaml/```json schemas) is data.
- WHY: fences signal "verbatim block"; a pipe inside `confidence: high|medium|low` is value syntax, not a column. Reformating it produces garbage tables and corrupts the schema/diagram.

## 2. Does it start with a tab (indented)?
- Indented lines that split into **one** field are list items/prose (e.g. "Architect / PM: Sections 2–3…"). Preserve them as prose, not a table.
- WHY: the leading tab is indentation/whitespace, not a column separator — splitting on it would invent columns that don't exist.

## 3. Is it delimited by pipes (`|…|`)?
- Treat as a table row only if the delimiter is at both ends (a real delimited row), not because the line merely contains a `|` somewhere in the middle.
- WHY: an interior pipe (e.g. `"PASS|FAIL"`) is union syntax; splitting there over-segments the row and creates phantom columns.

## 4. Is it tab-separated with 2+ fields?
- A non-indented line containing tabs that yields 2+ fields is a table row. Convert to aligned `|` rows, padding each column to the block's max width with a `|---|` separator after the header.
- WHY: GitHub renders whitespace-delimited columns as literal text; only `|`-delimited rows with a matching header+separator render as tables.

## Reconciliation check (after converting)
- Every row in a block must share the same column count. If data rows have fewer fields than the widest, padding produces empty trailing cells — reconcile counts first by confirming the intended column structure (the header usually defines it).

## Decision table
| Line shape | Inside fence? | Leading tab + 1 field? | Delimited `|…|` or ≥2 fields? | Action |
|---|---|---|---|---|
| `yaml` schema line with `high|medium|low` | yes (fence) | n/a | interior pipe only | leave verbatim |
| `Architect / PM: Sections 2–3…` | no | yes (1 field) | n/a | leave as prose list |
| `\| Cell A \| Cell B \|` | no | no | yes (delimited) | convert to aligned pipe row |
| `Cloud Concepts\tThe Shire` | no | no | yes (2 fields) | convert to aligned pipe row |
