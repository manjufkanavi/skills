---
name: kannada-poet-agy
description: Agy-powered Kannada poetry pipeline — uses Google agy for search, parsing, synthesis, and image generation instead of Tiny Fish API + local models.
tags: [kannada, poetry, antigravity, agy, web-search, image-gen]
---

# kannada-poat-agy — All-agy Kannada Poetry Pipeline

## Overview

A complete pipeline for generating illustrated, analyzed Kannada poetry — every step uses Google agy (Antigravity CLI).

### Pipeline (all agy)

1. **agy searches** → finds poem lyrics via `search_web`, returns already-parsed JSON with stanzas
2. **No parsing needed** → agy returns stanzas already split, explanations already generated
3. **agy synthesizes** → stanza explanations + life lessons in both Kannada and English
4. **agy creates image prompt** → included in the same JSON, or generated separately
5. **agy generates image** → uses `generate_image` tool directly
6. **HTML book** → generated locally (unified 3-page book template), then git committed & pushed

### Pipeline: Unified 3-Page Book Template

Each poem gets a single `combined_book.html` with 3 pages:

| Page | Content | Border Style | Color Theme |
|------|---------|-------------|-------------|
| 1 | Lyrics (ಪದ್ಯ) | Silk & Ink — double-line + corner brackets | Brown (#6b3a2a) + Gold (#b8860b) |
| 2 | Meaning & Explanation (ಅರ್ಥ ಮತ್ತು ವಿವರಣೆ) | Ember — triple-line + diamond markers | Orange (#c45e2e) + Orange-light |
| 3 | Life Lessons (ಜೀವನದ ಪಾಠಗಳು) | Forest — triple + mint accent bars | Forest (#2d4a3e) + Mint (#a8d5ba) |

**Design specs:**
- A4, `@page { size: A4; margin: 0 }`
- Content padding: 26mm from top, 26mm left/right, 8mm bottom
- Bold border: top/bottom inset 22mm from page edges, left/right inset 20mm
- Page numbers: 9pt, uppercase, top of each page
- No footers, no decorative section labels
- Full-page header gradient on pages 2-3

### How It Differs from kannada-poet

| Step | kannada-poet | kannada-poet-agy |
|------|-------------|------------------|
| Search | Tiny Fish API | agy `search_web` |
| Parse | Local regex | agy returns pre-split stanzas |
| Synthesize | agy CLI via script | agy included in search call |
| Image prompt | Local PromptEngineer | agy in same call |
| Image generation | mflux (local Flux2) | agy `generate_image` |
| HTML | Single unified book (3 pages) | Single unified book (3 pages) |
| Dependencies | Tiny Fish API key, mflux | agy CLI only |

## Quick Start

```bash
# Process all 81 poems (batch mode)
cd ~/.nanobot/workspace/personal_bot
python3 skills/kannada-poet-agy/main.py
```

## Output Structure

```
poems/<poet_name>/<poem_name>/
  combined_book.html           — 3-page unified book (standard output)
  poem_art.jpg                 — agy-generated image
  poem_analysis.json           — Full JSON (lyrics, stanzas, explanations, lessons, image prompt)
  image_generation_prompt.json — Image prompt + agy output filename
```

## agy Capabilities Used

- **`search_web`** — Web search for poem lyrics
- **`read_url_content`** — Fetch and read page content
- **`generate_image`** — Generate artwork from text prompts
- **`write_to_file` / `view_file`** — File system access

## Important: agy Usage Rules

1. **Never use `-p` with shell inline single quotes** — agy is an AI coding assistant, not a text generator. Shell single quotes consume the entire prompt. **ALWAYS use stdin piping via Python subprocess.**
2. **agy wraps JSON in single quotes with escaped characters** — The helper `parse_agy_json()` handles this: strips quotes, unescapes, extracts `{...}` block.
3. **agy may add prose prefix** — Extract JSON by finding first `{` to last `}`+1.
4. **Timeouts** — agy can take 30-180 seconds. Set timeout accordingly.
5. **agy model limits return `Error: Agent execution terminated due to error`** (exit 1) — **Wait 20 minutes** after the last limit hit before restarting. Never launch a batch without confirming limits cleared.

## File Location

**Working copy:** `~/.nanobot/workspace/personal_bot/skills/kannada-poet-agy/main.py`
**Template function:** `create_html_combined_book()` in main.py
**Knowledge base:** `data/poems/shishunala-sharifa/titles.json` (81 unique titles)

## Usage Example

```bash
# Process all 81 poems (batch mode)
python3 ~/.nanobot/workspace/personal_bot/skills/kannada-poet-agy/main.py

# Skips poems that already have combined_book.html
```

This will:
1. agy search for each poem's lyrics + stanzas + explanations + image prompt
2. agy generate the artwork image
3. Create `combined_book.html` (unified 3-page book) + save all files
4. Git commit and push to personal_bot repo

## Troubleshooting

### PDF generation fails (wrong approach)
The old "single-HTML → single-PDF" approach crashes WeasyPrint with `IndexError` on large documents. **Use the new integrated PDF module instead:**
- For individual poems: `generate_combined_pdf()` from `pdf_gen.py`
- For full books: `generate_tatvapagalu_pdf()` from `pdf_gen.py`
See `references/html-pdf-generation.md` for architecture details.

### agy returns no JSON — Check if agy is authenticated (`agy agents`). If not authenticated, run `agy` in TUI first and sign in.
- **Image not found** — agy saves images under `~/.gemini/antigravity-cli/brain/UUID/`. Use the 3-strategy image finder: exact filename match → partial match (strip timestamp suffix `_\d{13}`) → newest unused jpg.
- **Timeouts** — agy can take 2-3 minutes for complex prompts. Adjust timeout in `run_agy()` calls if needed.
- **Web search returns empty** — Some Kannada poems may not be well-indexed. agy may fall back to its training data, which can be incomplete.

## Pitfalls

### agy image filename mismatch
agy receives one filename in its response but the actual saved file has a timestamp suffix (e.g., `spiritual_guru_1784042296510.jpg`). Use the 3-strategy fallback:
1. Exact match of returned filename
2. Partial match — strip `_\d{13}` timestamp suffix and glob `name_part*`
3. Fallback — newest jpg in brain dir that isn't already copied to a poem directory

### agy model limits — silent "exit 1"
agy returns `Error: Agent execution terminated due to error` on model limits. **This kills every poem attempt.** Wait 20 minutes after the last limit hit before restarting. Never launch a batch without confirming limits have cleared — a batch starting with limits will fail ALL poems.

### Title matching for skip detection
Use word-level matching (not substring): count how many words of the title appear in the done directory name, require ≥2 matches with each word len > 3. Prevents "Anna" from colliding with other names and avoids Kannada-Unicode vs ASCII mismatches.

### Background process dead states
Background processes can die silently. Use `git log --since='...'` and `find poems -name combined_book.html | wc -l` as the reliable progress indicators, NOT the process log (which may be empty).

### Zero-output first-minutes is expected
The script uses `subprocess.run` with `capture_output=True` — output is NOT flushed in real-time to the parent process's stdout. The first `agy` call per poem has a 180-second timeout, so it's normal to see ZERO polling output for 2–3 minutes while the first API call is in flight. **Do not assume the process is hung** if polling returns empty. Use `ps -p <pid>` to confirm it's still alive, or check `find poems -name combined_book.html | wc -l` for progress. The process will eventually produce a burst of output once the first API call completes.

### Template migration: removed dual templates
The old system generated TWO files per poem (`poem_slideshow.html` + `poem_slideshow_coral_sky.html`). This was replaced with a single `combined_book.html`. The `create_html_mint_sand()` and `create_html_coral_sky_v2()` functions were removed from `main.py`. The `get_already_done()` function now checks for `combined_book.html` instead of the coral sky file. Old template files should be cleaned up before running the batch.

### Regenerating existing poems
When the template changes, existing poems can be regenerated using their saved `poem_analysis.json` and existing images. Use `importlib.util.spec_from_file_location` to load `main.py` and call `create_html_combined_book(data, safe_image)` for each poem dir that lacks `combined_book.html`.

### PDF generation for combined book

**Two rendering paths available:**

#### Path A: Per-HTML-page rendering (for individual poems)
Each poem's `combined_book.html` renders as a single PDF via:
```python
from skills.kannada-poet-agy.pdf_gen import generate_combined_pdf
generate_combined_pdf(poem_dir, poem_data, html_file)
```
The CSS in `main.py` is already fixed for per-page rendering (see below). Returns a PDF path or None on failure, with diagnostics (empty pages, low-content pages).

#### Path B: Full-book rendering (for tatvapadagalu and similar books)
For large multi-poem books, use the skill's integrated `generate_tatvapagalu_pdf()`:
```python
from skills.kannada-poet-agy.pdf_gen import generate_tatvapagalu_pdf
generate_tatvapagalu_pdf(poems_dir=..., skill_dir=..., repo_dir=...)
```
This does per-page rendering with auto-fit overflow fixes, then merges all PDFs. Strategy:
1. 52 HTML files (1 cover + 17 poems × 3 pages)
2. WeasyPrint each page individually
3. If a page overflows (>1 pages), reduce specific font-sizes surgically and retry
4. If still overflows, aggressive 2nd pass (all fonts → 7pt)
5. Merge all 51 page-PDFs into final book

**Current CSS (baked into main.py, no transformation needed):**
The template CSS now uses `display: block` (not flex) for `.content`, `.meaning-card`, `.lesson-item`. No more `margin-top: auto` on `.closing`. `break-inside: avoid` on cards and lessons. Tighter padding/line-heights throughout. These are the fix defaults — no manual transformation required.

**CSS extraction pitfalls (for custom builds):**
- **Strip `<style>` tag**: `mp[mp.find('<style>')+7:mp.find('</style>')]` — unstripped `<style>` creates blank pages.
- **Fix `calc()` syntax**: `calc(25% - 1px)` not `calc(25%) - 1px`
- **Cover CSS body selector**: Cover CSS has `body` selector that bleeds globally. Either remove it or scope to `.cover` only.

See `references/implementation-debt.md` for the plan to integrate PDF generation into the batch workflow.

**pypdf vs PyPDF2:** Both are installed in PDF venvs but have different import paths:
- `from pypdf import PdfMerger` (pypdf)
- `from PyPDF2 import PdfMerger` (PyPDF2)
Always try pypdf first, fall back to PyPDF2.

See `references/html-pdf-generation.md` for the full generation script template.

### CSS transformation checklist (legacy — CSS is now baked into main.py)
The template CSS in main.py already includes all page-fitting fixes. If you ever need to extract and adapt it (e.g., for a new book format), these are the transformations that were applied in the upgrade:
1. `.content`: `display: flex; flex-direction: column` → `display: block` (tighter padding: 10mm 22mm 5mm)
2. `.closing`: `margin-top: auto` → `margin-top: 0; padding-top: 4mm`
3. `.meaning-card`: `display: flex; flex-direction: column` → `display: block; break-inside: avoid` (tighter padding: 5mm 6mm)
4. `.lesson-item`: same as meaning-card (tighter padding: 4mm 0 4mm 14mm)
5. `.meaning-grid`: removed `flex-shrink: 0`, reduced gap to 5mm
6. `.lyrics-block`: reduced line-height 2.2→1.85, font-size 12pt→11.5pt, padding 8mm→5mm
7. `.header-band`: reduced padding 12mm→6mm top
8. `.page-header`: reduced padding 14mm→5mm top, 12mm→3mm bottom
9. `.footer`: reduced padding 6mm→2mm top, 8mm→3mm bottom
10. `.spiritual-msg`: reduced padding 8mm→3mm, margin 6mm→3mm
11. Meaning card text: en-text 9pt→8pt, kn-text 10pt→9.5pt with line-height 1.7→1.55
12. Lesson text: lesson-kn 11pt→10.5pt, lesson-en 10pt→9pt with line-height 1.7→1.55