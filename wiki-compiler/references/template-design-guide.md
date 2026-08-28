# Report Template Design Guide

## Purpose

Reference guide for selecting the appropriate HTML report template based on research domain and topic.

## Template Overview

### 01-ethereal-scroll.html — Warm Editorial
- **Font pairing:** Playfair Display (serif headlines) + Inter (sans body)
- **Palette:** Cream `#faf9f7` background, terracotta `#c4956a` accent
- **Best for:** Academic papers, humanities, general introspection, consumer tech explainers
- **Why it works:** Serif typography + warm tones create trust and readability for long-form prose
- **CSS features used:** CSS variables, radial gradient overlays, thin decorative lines, hover effects on key-point cards
- **WeasyPrint notes:** Clean — no flexbox layout, block-based with explicit heights avoids empty pages

### 02-binary-chronicle.html — Dark Terminal
- **Font pairing:** JetBrains Mono (monospace) + Space Grotesk (sans)
- **Palette:** Near-black `#0a0a0a`, green `#00e59b` accent, subtle grid overlay
- **Best for:** Technical research, cybersecurity, DevOps, data infrastructure, security audits
- **Why it works:** Terminal aesthetic signals precision and technical authority; monospace aids code/data readability
- **CSS features used:** CSS grid layout (sidebar + main), `linear-gradient` borders, data card hover glow effects
- **WeasyPrint notes:** Grid layout may need flexbox workarounds for pagination

### 03-heritage-essay.html — Classic Printed
- **Font pairing:** Crimson Pro (serif, all weights)
- **Palette:** Off-white `#fdfcfb`, amber `#b45309` accents, parchment `#f5f0e8` callouts
- **Best for:** Historical analysis, philosophy, policy research, literary studies, cultural studies
- **Why it works:** Drop caps + Roman numerals + two-column references evoke scholarly journals
- **CSS features used:** `::first-letter` for drop caps, `columns` for references, manual decorative separators
- **WeasyPrint notes:** CSS `columns` (multi-column) may need single-column fallback; `::first-letter` drop caps render correctly

### 04-modern-glass.html — Dark Gradient Deck
- **Font pairing:** DM Serif Display (headlines) + DM Sans (body)
- **Palette:** Deep navy hero (`#1e1b4b` → `#0a1628`), blue `#2563eb`, green `#3fb950`
- **Best for:** Business research, market analysis, startup decks, data-heavy reports, competitive intelligence
- **Why it works:** Gradient hero + metric strip + data cards feel modern and executive
- **CSS features used:** `background-clip: text` for gradient text, `::before` pseudo-elements for overlay patterns
- **WeasyPrint notes:** `background-clip: text` may not render in PDF; fallback to solid color

### 05-github-dark.html — Developer First
- **Font pairing:** IBM Plex Mono (code/metrics) + IBM Plex Sans (body)
- **Palette:** GitHub dark `#0d1117`, blue `#58a6ff`, green `#3fb950`
- **Best for:** Software engineering, open-source projects, developer tooling, API documentation
- **Why it works:** Familiar GitHub dark theme signals developer audience; structured metrics panel and pipeline visualization
- **CSS features used:** Noise texture `::before` overlay, pipeline step cards, reference tables
- **WeasyPrint notes:** Tables render correctly; `::before` noise is decorative (can skip for PDF)

## Selection Heuristics

1. Audience = developers/engineers? → **05-github-dark** or **02-binary-chronicle**
2. Topic = historical, philosophical, literary? → **03-heritage-essay**
3. Topic = business/market/competitive intel? → **04-modern-glass**
4. Topic = general academic or long-form prose? → **01-ethereal-scroll**
5. No preference? → Default **01-ethereal-scroll** (safest for most topics)

## WeasyPrint Compatibility Checklist

For HTML-to-PDF conversion of these templates:
- Use `display: block` instead of `display: flex; flex-direction: column` for page containers
- Set explicit `height` on page containers (e.g., `238mm` for A4)
- Add `overflow: hidden` to prevent empty orphan pages
- Remove `margin-top: auto` from children (pushes content to top, leaving dead space)
- Use `break-inside: avoid` on individual items/cards instead of flex containers
- `background-clip: text` (template 04) will not render in PDF — fallback to solid color
