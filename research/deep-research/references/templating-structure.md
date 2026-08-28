# Heritage-Essay HTML Template CSS Class Reference

The `03-heritage-essay.html` template provides a complete CSS stylesheet for
rendering research reports with a scholarly, printed aesthetic. This file
documents the available classes for agents that generate HTML reports.

## Palette

| Variable | Value | Usage |
|----------|-------|-------|
| `--bg` | `#fdfcfb` | Page background (warm white) |
| `--ink` | `#1c1917` | Body text color (near-black) |
| `--muted` | `#78716c` | Secondary text (warm gray) |
| `--accent` | `#b45309` | Accent color (amber/brown) |
| `--accent-light` | `#fef3c7` | Light accent fill |
| `--parchment` | `#f5f0e8` | Subtle section backgrounds |
| `--border` | `#e7e5e4` | Dividers, table borders |

## Typography

- **Font family:** `Crimson Pro, Georgia, 'Times New Roman', serif`
- **Base size:** 18px, weight 300
- **Google Fonts CDN:** `https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,300;1,400&display=swap`
- **Max page width:** 680px (centered)

## Structural Classes

| Class | Element | Purpose |
|-------|---------|---------|
| `.page` | `<header>`, `<article>`, `<footer>` | Centered container, max-width 680px, padding 0 2rem |
| `.masthead` | `<header>` | Title block at page top, centered |
| `.masthead-rule` | `<div>` | Horizontal accent line (40px wide) |
| `.masthead-tag` | `<p>` | Small uppercase tagline above title |
| `.masthead-title` | `<h1>` | Main report title (3.8rem at desktop) |
| `.masthead-sub` | `<p>` | Subtitle/abstract paragraph |
| `.masthead-rule-bottom` | `<div>` | Gradient fade-out line below title |
| `.article` | `<article>` | Main content wrapper |
| `.article-section` | `<section>` | Thematic section with 3rem vertical padding |
| `.section-number` | `<span>` | Roman numeral or ordinal indicator |
| `.section-divider` | `<hr>` | Divider between sections |
| `.separator` | `<div>` | Thin separator line |
| `.report-table` | `<table>` | Comparison/summary tables |
| `.callout` | `<div>` | Highlighted quote or insight block |
| `.two-col` / `.two-col-col` | `<div>` | Two-column layout for comparisons |
| `.references` | `<div>` | References section header |
| `.ref-list` | `<ol>` | Numbered reference list |
| `.report-footer` | `<footer>` | Footer with date |

## Content Classes

| Class | Purpose |
|-------|---------|
| `.section-title` | H2 headings in report content |
| `.subsection-title` | H3/H4 headings in report content |
| `.lead` | Lead/summary paragraph |
| `.drop-cap` | First paragraph with drop cap effect |
| `.code-block` | Pre/formatted code blocks |
| `.task-done` | Checked task list item |
| `.task-pending` | Unchecked task list item |

## Pitfalls

- **No external CSS files** — all styles must be in the `<style>` block. The template is self-contained.
- **No external JS** — the template has no JavaScript dependencies.
- **Do NOT use `@import` for fonts** — use a `<link>` tag in `<head>` (Google Fonts CDN).
- **Responsive breakpoint** at 700px hides `.two-col` columns and stacks them. Don't use `.two-col` with content wider than 500px.
- **Drop caps** only work on the first letter of `.lead` paragraphs — they're not supported for arbitrary paragraphs.
