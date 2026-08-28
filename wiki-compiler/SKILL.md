---
name: wiki-compiler
description: >
  Multi-source research workflows: search discovery, multi-page scraping,
  deduplication, structured compilation. Covers general wiki compilation,
  deep research pipelines (100+ sources), benchmarking/search-scrape pipelines,
  ML paper writing, and domain-specific data extraction.
version: 2.0.0
author: Hermes Agent
tags: [research, scraping, wiki, documentation, multi-source, deep-research, benchmark, paper-writing]
created: 2026-06-28
updated: 2026-07-11
---

# Research Wiki Compiler

## When to use

You need to research a topic, compile information from multiple sources, or generate a structured document (wiki, report, paper, or dataset).

- User says "research X", "compile wiki for Y", "deep dive into Z"
- User wants a comprehensive reference document from web sources
- User needs search+scrape+analysis benchmarks
- User wants to write an ML paper for a conference
- User needs domain-specific data extraction (contact info, college details, etc.)

## Core Research Engine (shared across all workflows)

All research workflows share the same foundational steps. Master these first:

### Step 1: Discover Sources

Run multiple `search_web` queries targeting different content types:
```
search_web(query: "topic OR keywords site:medium.com")
search_web(query: "topic guide tutorial 2026")
search_web(query: "topic reddit OR site:reddit.com")
search_web(query: "topic blog OR dev blog OR developer blog")
```

Target 15-25 unique URLs across dev blogs, Medium, documentation, and community forums.

### Step 2: Scrape All Sources

For each URL, run `scrape_page(url)`. Collect results into a structured array.

**Scrape reliability patterns** (see `references/pagezen-scrape-reliability.md`):
- ✅ Reliable: GitHub, AWS Blog, Red Hat, IBM Think, DeepSource, Wiz, simple blogs
- ❌ Always fails (0 chars): HackerNews, Reddit, Deloitte, Apple, most enterprise sites, Snyk (metadata only)
- ⚠️ Why: Page Zen uses Node.js `fetch()` — NOT a browser. No JS execution, no SPA rendering, no bot bypass.
- **Workaround:** Accept failures, skip to next URL. Prioritize GitHub. Use search titles/snippets as fallback when scrape fails.

### Step 3: Compile

Aggregate all scraped content into a structured document:
1. Identify the core topic and sub-topics
2. Group sources by theme
3. Write sections using synthesized content
4. Include a "Key Resources" table with all source URLs
5. Save to the appropriate output location

### Step 4: Deliver Summary

Report number of sources scraped, key findings, file path, and any sources that failed.

### Shared Pitfalls

- **Reddit always blocked via scrape:** Extract from search snippets only. wordCount 6 on all Reddit URLs.
- **Login-gated sites** (LinkedIn, Facebook, RocketReach): Return "Error: Scraping failed" or login boilerplate. Extract from snippets.
- **Cloudflare-protected sites:** Return "Just a moment..." pages. Skip entirely.
- **Timeouts:** Don't retry indefinitely — move on.
- **Content overlap:** Deduplicate in the output rather than repeating.
- **SearXNG may be down:** If search fails, pre-flight check services; start Docker or colima.
- **MCP exit code is misleading:** `mcp-client.js` returns exit code 0 even when search fails. Check stdout for `Error:` prefix.
- **Page Zen on Google/Indeed/Naukri often blocked:** Google → 429, Indeed → 403. Use MCP search snippets as primary data source.
- **Rate limiting:** MCP has ~30 requests/minute rate limit. Space out searches. After ~40-50 searches in a single session, SearXNG gets Google-banned and ALL MCP searches timeout.

## Workflow Modules

Choose the module that matches your task. Each builds on the core engine above.

---

### 1. General Wiki Compilation (lightweight)

Best for: quick reference documents, technology overviews, setup guides.

Build a wiki/reference document from multi-source research. Covers search discovery, scraping, deduplication, and structured compilation.

**Output:** `~/.hermes/wiki/<topic>-wiki.md`

**See:** `references/diffusiongemma-mac-studio.md` for an example of condensed knowledge-bank compilation from 20+ sources.

---

### 2. Deep Research Pipeline (heavyweight)

Best for: comprehensive reports requiring 100+ unique sources across multiple disciplines.

The deep research agent performs a 5-phase pipeline:
```
Topic → Query Generation → Batch Search → Multi-page Crawl → Deduplication → Synthesis → Research Report
```

#### Phase 1: Query Generation (15-30 queries)
Generate diverse queries covering:
- Definition & Overview (3-5)
- Technical Deep Dive (3-5)
- Industry/Application (3-5)
- Comparative Analysis (3-5)
- Trends & Future (3-5)
- Challenges & Limitations (3-5)
- Expert Opinion (3-5)
- Data & Statistics (3-5)
- Case Studies (3-5)
- Resources & Tools (3-5)

#### Phase 2: Batch Search Execution
Execute via LightSerp MCP in batches of 5 (3-5s gaps between batches). Collect ALL results.

#### Phase 3: Multi-Page Crawl (MANDATORY 100 unique websites)
**Every deep research MUST scrape a minimum of 100 unique websites.** This is non-negotiable.

If insufficient URLs, generate additional queries, broaden scope, continue until 100+ unique domains scraped.

URL selection:
- Top 3 results from each query always crawled
- Diverse source types: academic, industry, news, community, government
- Skip duplicates and low-quality sources
- **Priority: unique domains over multiple pages from same domain**

#### Phase 4: Content Synthesis
For each page: extract key facts, arguments, metadata, relevance score, cross-references.
Cluster by theme. Detect consensus and conflicts. Assign confidence levels (HIGH/MEDIUM/LOW/UNCERTAIN).

#### Phase 5: Report Generation
Generate Gemini-style research report with:
- Executive Summary (2-3 paragraphs)
- 12 structured sections (Introduction through Resources & Further Reading)
- Sources & Methodology appendix
- Limitations & Gaps

**Output:** `~/.hermes/research/{topic_slug}_research.md`

### Report Template Selection (Post-Synthesis)

After synthesizing the report, choose an HTML template from `html_templates/` (available at `skills/deep-research/html_templates/` in the personal_bot repo):

| Template | File | Best For | Aesthetic |
|---|---|---|---|
| Ethereal Scroll | `01-ethereal-scroll.html` | Academic, humanities, general introspection | Warm serif, soft gradients, editorial magazine |
| Binary Chronicle | `02-binary-chronicle.html` | Technical, CS, engineering, security | Dark terminal, monospace, sidebar nav |
| Heritage Essay | `03-heritage-essay.html` | Historical, philosophy, literary, policy | Classic serif, drop caps, Roman numerals |
| Modern Glass | `04-modern-glass.html` | Business, market analysis, data-heavy | Dark navy hero, gradient accents, metric cards |
| GitHub Dark | `05-github-dark.html` | Software engineering, open-source, dev tools | GitHub dark theme, Plex Mono, pipeline viz |

**Selection heuristic:** Developers → 05 or 02; Historical/philosophical → 03; Business/market → 04; General academic/prose → 01 (default); User has preference → follow it.

See `references/template-design-guide.md` for full CSS features, WeasyPrint compatibility notes, and design rationale for each template.

**Rate Limiting:** Max 30 requests/min. Search: 5 queries/batch with 3s gaps. Scrape: 2-3s between calls.

**See:** `references/batch-research-pattern.md` for parallel batch research patterns.
**See:** `references/mcp-search-scrape-patterns.md` for MCP response format and pitfalls.
**See:** `references/mcp-search-debugging.md` for MCP failure troubleshooting.

---

### 3. Web Benchmarking (search+scrape at scale)

Best for: validating scraping quality, benchmarking search systems, generating research papers from web data, curating LLM fine-tuning data.

#### Process:
1. **Define queries:** 20+ related queries covering topic from different angles
2. **Execute multi-query search:** Sequential with 500ms delays. Deduplicate URLs. Target 100+ unique URLs.
3. **Scrape:** 3 URLs concurrently max. Store as JSON files. Add 1s delays between batches.
4. **Analyze:** Calculate metrics (success rate, avg content length, top concepts, domain breakdown)
5. **Generate research paper:** Comprehensive markdown with abstract, methodology, findings, recommendations, references.

**Key Pitfalls:**
- SearXNG returns ~30 results/query. Run 20+ queries to get 100+ URLs.
- Content quality varies — filter URLs with content < 50 chars as failed.
- Port conflicts: MCP may already run on port 3000. Always check first.

---

### 4. ML Paper Writing Pipeline

Best for: producing publication-ready ML/AI papers for NeurIPS, ICML, ICLR, ACL, AAAI, COLM.

Covers: experiment design, execution, monitoring, analysis, paper writing, review, revision, submission.

**Not a linear pipeline** — iterative loop. Results trigger new experiments. Reviews trigger new analysis.

**Output:** Conference-ready LaTeX paper with experiments, results, analysis.

**Templates:** `templates/` subdirectory contains conference-specific templates:
- `templates/neurips2025/`, `templates/icml2026/`, `templates/iclr2026/`, `templates/acl/`, `templates/aaai2026/`, `templates/colm2025/`

**Reference:** `references/research-paper-writing-templates.md` for conference-specific formatting and submission patterns.

---

### 5. Karnataka College Data Extraction (domain-specific)

Best for: discovering engineering colleges and extracting contact details (name, address, phone, email, placement cell info).

#### Workflow:
1. **Discover colleges:** Search for comprehensive lists (AICTE directory, careers360, shiksha)
2. **Extract contact info:** For each college, search for contact/about pages, scrape home page footer, scrape placement page
3. **Google dork for contact info:** `site:{domain} "contact" "phone" "email"`, etc.
4. **Save results:** Structured JSON with college, address, phone, email, placement_email, placement_phone

**Key rules:**
- Always use LightSerp MCP first (search_web, scrape_page)
- Only use fallback (curl SearXNG, browser scrape) when MCP is confirmed down
- Rate limit: 30 req/min. Add delays between batches.

---

### When to Use Each Module

| Task | Module |
|------|--------|
| Quick reference document | General Wiki Compilation |
| Comprehensive report (100+ sources) | Deep Research Pipeline |
| Benchmark search/scrape quality | Web Benchmarking |
| Write ML paper for conference | ML Paper Writing |
| Extract college contact data | Karnataka College Data Extraction |

---

## File Organization

```
~/.hermes/wiki/              # Compiled wiki documents
~/.hermes/research/          # Deep research reports and artifacts
~/.hermes/personas/          # OSINT persona dossiers (see osint-persona-builder)
```

## Related Skills

- **blogwatcher** — Blog/RSS feed monitoring (separate CLI tool, different workflow). See subsection below.

**When arXiv alone isn't enough:** Use wiki-compiler's general wiki compilation for broader web research on the same topic.

---

### Blog/RSS Monitoring (from blogwatcher skill)

Track blog and RSS/Atom feed updates with the `blogwatcher-cli` tool.

**Installation:**
```bash
# macOS Apple Silicon
curl -sL https://github.com/JulienTant/blogwatcher-cli/releases/latest/download/blogwatcher-cli_darwin_arm64.tar.gz | tar xz -C /usr/local/bin blogwatcher-cli
```

**Common Commands:**
- Add a blog: `blogwatcher-cli add "My Blog" https://example.com`
- Add with explicit feed: `blogwatcher-cli add "My Blog" https://example.com --feed-url https://example.com/feed.xml`
- List tracked blogs: `blogwatcher-cli blogs`
- Scan all blogs: `blogwatcher-cli scan`
- List unread articles: `blogwatcher-cli articles`
- Mark article read: `blogwatcher-cli read 1`
- Import from OPML: `blogwatcher-cli import subscriptions.opml`

**Docker:** `docker run --rm -v blogwatcher-cli:/data -e BLOGWATCHER_DB=/data/blogwatcher-cli.db ghcr.io/julientant/blogwatcher-cli scan`

**Key notes:** Auto-discovers RSS/Atom feeds. Falls back to HTML scraping. Database at `~/.blogwatcher-cli/blogwatcher-cli.db`.

---

## arXiv Paper Discovery

**Load this when:** "search arXiv for papers about X", "find recent ML papers on arXiv"

See the `arxiv` skill for the full arXiv search interface. Quick reference:

```bash
# Search by keyword
arxiv search "transformer attention mechanism"

# Search by category
arxiv search "cs.CL"

# Get paper details
arxiv info <paper-id>

# Download paper PDF
arxiv download <paper-id>
```

**When arXiv alone isn't enough:** Use wiki-compiler's general wiki compilation for broader web research on the same topic.

---

### PDF Reference Compilation (from reference-compilation skill)

When sources are PDFs rather than web pages, use this workflow to download, extract, and compile PDF reference materials.

**Search for PDFs:** Use Google dorks — `site:github.com "topic" filetype:pdf`, `"topic cheat sheet" filetype:pdf`, `interview "topic cheat sheet" filetype:pdf`. See `references/google-dorks-for-pdfs.md` for a full dork table.

**Download PDFs:** Verify each is non-empty (>1KB). Remove duplicates by URL.

**Extract text (PyMuPDF):**
```python
import fitz
doc = fitz.open("file.pdf")
text = ""
for page in doc:
    text += page.get_text()
doc.close()
```
⚠️ PDFs from OCR sources may contain embedded HTML tags (`<br/>`, `<font>`). Handle aggressively.

**Deduplicate & categorize:** Extract section headers + content, classify by topic keywords, merge with deduplication, only include sections >30 chars.

**Generate output PDF (reportlab):**
```python
from reportlab.platypus import Table, TableStyle
from reportlab.lib.colors import HexColor
t = Table([[text]], colWidths=[4.8*inch])
t.setStyle(TableStyle([
    ('FONT', (0,0), (-1,-1), 'Courier', 7),
    ('TEXTCOLOR', (0,0), (-1,-1), HexColor('#e0e0e0')),
    ('BACKGROUND', (0,0), (-1,-1), HexColor('#1e1e3f')),
]))
```

**HTML cleaning for PDF output:**
```python
import re
def strip_html_tags(text):
    text = re.sub(r'<[^>]*>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ').replace('&#39;', "'")
    return text
```

**Pitfalls:**
- Reportlab `<font>` tag ignores border-color, border-radius, backColor. Use Table/TableStyle instead.
- Style name collisions: `getSampleStyleSheet()` pre-defines Normal, Title, Code. Use custom names.
- PDF text from OCR has embedded HTML — strip aggressively before rendering.
- On macOS, weasyprint often fails due to missing brew deps — prefer reportlab.

**- **osint-persona-builder** — Deep OSINT persona building from college data (sequential pipeline with Sherlock/Maigret)
- **phone-finder** — Phone number discovery from name (OSINT investigation)
- **college-phone-scraper** — Indian college phone number discovery via Google dorks
- **lightserp** — Underlying MCP service (search + scrape engine for all research workflows)
- **arxiv** — Academic paper discovery on arXiv (keyword/author/category search)
