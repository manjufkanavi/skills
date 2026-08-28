# HTML Report Rendering from Markdown

The deep research pipeline produces two outputs from the same research data:
1. **Markdown report** (`.md`) — authored by the agent
2. **HTML report** (`.html`) — rendered from a static template, then populated with actual content

## The Process (2026-07-17 workflow)

1. Write the `.md` report to `reports/<topic-slug>-<timestamp>/<topic-slug>.md`
2. Copy `html_templates/03-heritage-essay.html` into the report directory
3. Replace all placeholder content (headings, paragraphs, references) with actual synthesized report content
4. The HTML template uses embedded CSS only (no JS dependencies, no external frameworks)
5. Font: Google Fonts `Crimson Pro` serif — ideal for scholarly aesthetic
6. Commit both files and push

## Template Structure (`03-heritage-essay.html`)

The heritage essay template has a fixed layout:
- `<div class="masthead">` — title, tagline, metadata
- `<article class="page article">` — main content
- `<section class="article-section">` — each thematic section
- `<div class="callout">` — highlighted quotes
- `<table class="report-table">` — comparison data
- `<div class="ref-list">` — references list
- `<footer class="report-footer">` — footer

## Rendering Strategy

Since there is no templating engine, the agent replaces placeholder content by:
1. Starting from a clean HTML skeleton (copy the template)
2. Building the HTML content inline — headings, paragraphs, tables, lists
3. Using the markdown report as the source of truth for what goes into each section
4. The HTML uses semantic class names matching the template; just fill in the body content

## Pitfalls

- **Do NOT use a templating engine** — the skill uses static HTML replacement, not Jinja/Handlebars/etc.
- **Do NOT copy-paste the markdown directly** — the HTML needs proper `<p>`, `<h2>`, `<table>`, `<div>` wrapping
- **Font loading**: `Crimson Pro` is loaded from Google Fonts CDN; ensure the `<link>` tag is preserved in the `<head>`
- **Responsive**: The template includes a `@media (max-width: 700px)` breakpoint — don't break the grid layout
- **One file only**: The HTML report must be self-contained — no external JS, no CSS files outside the `<style>` block
