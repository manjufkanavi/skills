---
name: deep-research
description: Deep research skill that generates search queries, scrapes web pages and research sites, extracts PDF content, and produces a PhD-level synthesized research report.
---

# Deep Research

## When to use

Use when the user asks for:
- "deep research on [topic]"
- "comprehensive research on [topic]"
- "research report about [topic]"
- "deep dive into [topic]"
- "thorough analysis of [topic]"

## How to run

```bash
python3 skills/deep-research/deep_research.py "your query here"
```

## Workflow

### Phase 1: General Search
1. Generates ~26 diverse search queries (overview, history, technical, comparisons, use cases, market, challenges, future)
2. Executes queries via Tiny Fish Search API
3. Deduplicates URLs from results
4. Scrapes content via Tiny Fish Fetch API in batches of 10
5. Iterative deepening: if fewer than 80 unique pages, generates follow-up queries from discovered content (up to 3 rounds)

### Phase 2: Research Site Searches
Searches 8 research sites: arXiv, Google Scholar, PubMed, Semantic Scholar, Nature, Science, IEEE Xplore, ACM Digital Library

### Phase 3: PDF Extraction
Discovers PDF URLs and extracts text using pypdf → pdfplumber → pdftotext (fallback chain)

### Phase 4: Report Generation
Compiles a **concise report** (~8K chars, 5-10 pages, 5-10 min read) with thematic synthesis and deduplication, plus a **beautiful HTML slideshow** presentation. Both are committed to git.

## Output

Each research run creates:

### Reports (under `skills/deep-research/reports/`)

A **new subdirectory** named `<topic-slug>-<timestamp>` containing:
- **Markdown report**: `<topic-slug>-<timestamp>.md`
- **HTML slideshow**: `<topic-slug>-<timestamp>.html`

Example:
```
reports/
  loop-engineering-ci-cd-20260710-053000/
    loop-engineering-ci-cd-20260710-053000.md
    loop-engineering-ci-cd-20260710-053000.html
```

### Raw Data (under `skills/deep-research/data/raw/<topic-slug>/`)

- **`pages.json`** — All scraped web pages with full content, URL, title, timestamp
- **`pdfs.json`** — All extracted PDF content with source URLs
- **`research.json`** — Research site search results (arXiv, Scholar, etc.)

### Synthesized Data (under `skills/deep-research/data/synthesized/<topic-slug>/`)

- **`deduped.json`** — Deduplicated content items (title, content, url)
- **`themes.json`** — Theme clusters with evidence and source references
- **`report_data.json`** — Structured payload for LLM synthesis (same as `research_data.json`)

### Global Index

- **`data/index.json`** — Maps topic slug to data paths, page counts, query counts, and timestamps for all past runs

### Other

- **`research_data.json`** — Structured JSON at `skills/deep-research/research_data.json` (kept for backward compatibility)

### Mandatory post-generation steps
After generating both files:
1. **Commit and push** — run `git add`, `git commit -m "Add deep research report: <topic>"`, then `git push`.
2. **Delete old iterations** — remove previous report directories for the same topic (keep only the latest).
3. **Verify** — confirm both `.md` and `.html` exist in the new directory and the push succeeded.

## Report Structure (Markdown)

1. What Is Loop Engineering? (Definition)
2. From Prompt to Loop: The Paradigm Shift (Evolution)
3. How Loop Engineering Works (Mechanics)
4. Common Problems & Fixes (Challenges)
5. Real-World Applications
6. Future Outlook
7. References (top 30 sources)

## Slideshow Features

- Beautiful dark-themed HTML/CSS presentation
- Gradient accents, smooth CSS transitions
- Keyboard navigation (← → arrows, Home/End, Space)
- Progress dots and slide counter
- Responsive design for mobile/desktop
- Key takeaways summary slide

## Constraints

- **Timeout**: 600s hard limit
- **Target**: ~80 unique pages per run
- **Report quality**: Concise, readable, 5-10 pages max (~8K chars) — never merge raw scraped sources
- **Deduplication**: Use `` tags during generation to facilitate duplicate removal
- **Text cleaning**: Aggressively strips YouTube metadata, Instagram boilerplate, Reddit headers, and creator names
- **PDF extraction**: IEEE Xplore and Semantic Scholar return HTML wrappers — extraction will fail on these sources
- **Retention**: Keep only the latest report per topic; delete previous iterations
- **Synthesis**: Use the agent's own LLM for report synthesis, NOT Tiny Fish API
- **New directory per run**: Every research creates a fresh `<topic-slug>-<timestamp>` subdirectory — never reuse or overwrite
- **Both files mandatory**: Every run must produce both `.md` and `.html` — no exceptions
- **Git commit + push mandatory**: After generating files, always commit and push to origin/master

## Output Format

### Phase 1–3 Output: `research_data.json`

Structured JSON at `skills/deep-research/research_data.json` containing:
- `topics`: array of researched topics
- `themes`: identified thematic clusters
- `sources`: deduplicated source URLs with metadata

### Phase 4 Output: Synthesized Report

Uses the agent's own LLM to produce:
1. Executive Summary
2. Theme Sections (with evidence from sources)
3. References (top 30 sources)

Then generates:
- A markdown report (`.md`) with full research findings
- An HTML slideshow (`.html`) with responsive, animated presentation

Both files go into a new `<topic-slug>-<timestamp>` directory under `skills/deep-research/reports/`, then are committed and pushed to git.

## Tool Access Notes

- **Do NOT use shell `exec` to read `research_data.json`** — safety guards block access to `skills/` directory from exec sandbox. Use the `read_file` tool instead.
- Exec sandbox is restricted to workspace directory only.

## Dependencies

- `pypdf`, `pdfplumber`, `pdftotext` (poppler)

## Known Issues

- IEEE Xplore and Semantic Scholar consistently return HTML instead of binary PDFs
- Report generation must support thematic synthesis, not just concatenation
