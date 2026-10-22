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

Generic — adapt the headings to the topic, never ship another topic's structure:
1. Definition (what it is)
2. Evolution (why it emerged)
3. Mechanics (how it works)
4. Challenges & common problems
5. Real-world applications
6. Future outlook
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
- **Retention**: Keep only the latest *report* per topic; **never delete raw data** (`data/raw/<slug>/pages.json`, `pdfs.json`) — downstream consumers (e.g. the learning-forge video pipeline) re-derive scenes from it on later runs
- **Synthesis**: Use the agent's own LLM for report synthesis, NOT Tiny Fish API
- **New directory per run**: Every research creates a fresh `<topic-slug>-<timestamp>` subdirectory — never reuse or overwrite
- **Both files mandatory**: Every run must produce both `.md` and `.html` — no exceptions
- **Git commit + push mandatory**: After generating files, commit and push with `git push origin HEAD` (the skills repo default branch is `main` — never origin/master)

## Synthesis Pitfalls (grounded content)

- **Confirm the collector persisted full text before synthesizing.** Length-limited scrapers and custom collectors often store only a preview length, metadata, or URL — not the cleaned body. Before synthesizing grounded content, check that your collected data (e.g. `pages.json`) actually contains full text; if it stores only lengths/metadata, re-fetch the authoritative/official URLs (serialized and paced for Tiny Fish rate limits) and synthesize from that. Never author grounded content from thin air, and never paste raw scraped HTML into a report.
- **Validate authored artifacts against the downstream consumer's parse format before committing.** A markdown compiler may require a specific shape — for example `---` frontmatter with `topic`/`source`, and non-empty `## Section` bodies. Mirror the consumer's parser in a small validation script (frontmatter-fence + `##`-split regex) and fix format errors before commit rather than shipping artifacts the consumer rejects.

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
- **Run non-trivial Python from a file, not inline `python3 -c`** — shell mangling of f-strings/nested quotes wastes turns. Write the script to a file and run `python3 path.py`.

See `references/runner-adaptation.md` for adapting the bundled runners to rate limits and arbitrary topics.

## Bundled runners: legacy status

- `scripts/run_synthesize.py` is a **topic-hardcoded legacy example** (theme map, copy, and advice strings baked in from one prior topic). Do not run it on new topics — follow `references/runner-adaptation.md` and write a fresh synthesis per run.
- `synthesize_for_video.py` is a one-off Kannada news-video experiment (agy-based); reference only.

## Dependencies

- `pypdf`, `pdfplumber`, `pdftotext` (poppler)

## Known Issues

- IEEE Xplore and Semantic Scholar consistently return HTML instead of binary PDFs
- Report generation must support thematic synthesis, not just concatenation

## TinyFish API Rate Limits (operational)

- The TinyFish search/fetch APIs **rate-limit when calls are parallelized**. Never fire multiple `tinyfish_search` or `tinyfish_fetch` requests concurrently — **serialize** them (one at a time, with a small delay between queries).
- On an `403 Forbidden` from the Firecrawl-backed search endpoint, wait **~60 seconds**, then proceed (retry). Do not escalate it as a broken tool.
- Pacing pattern: one search query → collect URLs → fetch those pages (batched, but sequentially) → then the next query. This keeps you under the rate limit while still scraping in batches of ~10.
- **Check subtopic coverage before curating.** After a multi-subtopic collection, walk the digest against every planned subtopic — rank-prioritized URL selection can let one source family consume the entire fetch quota (a 12-page quota once produced 8 pages from a single service and zero from two other planned services). For each gap, run a targeted top-up: fetch the specific missing URLs (the official docs for that subtopic) serially with the same 60s retry discipline, append to the checkpoint `pages.json`, and rebuild the digest before authoring.
