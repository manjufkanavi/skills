---
name: resume-rebuild
description: Use when rebuilding or updating a resume PDF.
version: 1.0.0
author: hermes-agent
license: MIT
tags: [resume, pdf, design-tokens, ats, html]
related_skills: [html-to-pdf, markitdown]
metadata:
  hermes:
    tags: [resume, pdf, design-tokens, ats, html]
    related_skills: [html-to-pdf, markitdown]
---

# Resume Rebuild (PDF → design tokens → HTML → verified PDF)

Class: take an existing resume PDF, reverse-engineer its design, apply user-directed changes, rebuild faithful HTML, convert to a clean A4 text PDF, verify programmatically, and deliver. Standing protocol: (1) read the design as a senior UX designer → design tokens, (2) extract all content (text layer / OCR), (3) apply the changes the user specifies, (4) build the HTML from the tokens, (5) HTML→PDF, (6) send over Telegram.

## When to Use

- User sends a resume/CV PDF and asks to rebuild, restyle, or modernize it
- "Make my resume ATS-friendly / pass AI screening"
- Iterative resume edits (profile rewording, job/date updates, layout fixes) ending in PDF delivery
- "Check / score my resume against ATS" with no rebuild — run the external validation step directly (Workflow step 7)

Not for: creating a resume from scratch with no source design (start from a template), generic PDF text edits (nano-pdf, in html-to-pdf), or non-resume documents.

## Standing rules (user preferences)
- Content changes are user-directed. Never invent facts (dates, skills, employers, metrics, pin codes). If a fact is missing or suspect (start date, a handle that looks like a typo), surface it in the approval round — the user supplies it.
- When asked for expert improvement ("make it ATS-ready / more minimalist"), return one numbered list split into DESIGN vs CONTENT, each item with a one-clause reason, assumptions flagged; then take approval with a single clarify gate and apply the approved subset in one rebuild.
- Version files sequentially, continuing the user's own numbering (`…_4.pdf` → `_5`, `_6`, …). Never overwrite a delivered version.
- Each round delivers: final PDF + per-page preview PNGs in one message, plus a short "applied / verified" summary citing measured numbers (page rect, bottom slack, keyword/stale-string results) — not adjectives.
- Keep two sources of truth in the working dir: `content.json` (all resume text, structured) and `resume.html` (token-driven markup). Patch both on every change; the rebuild re-renders from resume.html.

## Workflow
1. **Analyze** the source PDF with pymupdf — `scripts/reverse-engineer.py <pdf>` prints page rect, every span (x/y/w/h, size, weight, color, text), every drawing fill, and font/size/color census. Then resolve ambiguous shapes: raw content stream (clip ops) + pixel sampling of a 2x render. Depth: `references/design-reverse-engineering.md`.
2. **Extract** all text into `content.json` (header/contact, each section, bullets with their bold spans, dates, lists). Preserve source wording exactly — this file is the edit surface.
3. **Write design tokens** as a CSS `:root` block (palette, type scale in pt, radii, bar/rule/dot sizes, margins) from measured values — no invented values.
4. **Apply changes** to content.json + resume.html.
5. **Convert** with Playwright Chromium: `@page { size: A4; margin: 0 }` in the CSS + explicit mm paper dims in `page.pdf()`, `preferCssPageSize: true`, `printBackground: true` — mechanics and the US-Letter trap live in the html-to-pdf skill (Playwright Chromium section).
6. **Verify — never skip, never eyeball**: page count + page rect (A4 = 595.92×841.92pt), per-page text extents + bottom slack, per-column overflow in multi-column rows, all new strings present, all stale strings absent, pixel-sampled key colors. Then render 2x previews.
7. **ATS-validate with Resume-Matcher** — when the user asked for ATS / AI-screening readiness, or on the first delivery after a change that affects extraction (tracking, ligatures, column structure). Run the repo's deterministic engine (parse checks + roundtrip + JD-scored breakdown) against the built PDF; fix CSS-level causes of failures and re-validate. Recipe: `references/ats-checklist.md` § External validation.
8. **Deliver** PDF + previews via `MEDIA:` paths, citing the ATS verdict (extractability, failing checks, overall score + the JD used).

## Pitfalls
- **US-Letter fit-scale trap**: with `preferCssPageSize`, a numeric `@page { size: 595pt 842pt }` can be ignored — Chromium then fit-scales A4-sized content to US Letter (~94%, centered). It looks plausible and is wrong. Use the `A4` keyword in CSS, matching mm dims in `page.pdf()`, and assert the output rect with pymupdf (full rule in html-to-pdf § Playwright Chromium).
- **Letter-spacing kills ATS**: wide tracking in the text layer extracts as per-character spaces and breaks phrase matching. Keep keyword text ≤ ~0.5pt tracking and verify the exact phrase extracts as one string.
- **Ligatures break keyword matching**: Chromium PDF output with the Helvetica family emits single-glyph ﬁ/ﬃ ligatures ("ﬁrewall", "Identiﬁed") that fail exact-word ATS searches even though they render fine. Set `font-variant-ligatures: none; font-feature-settings: "liga" 0, "clig" 0, "dlig" 0;` on the body; verify by pdfminer-extracting a word containing "fi".
- **Multi-column verification false positives**: a whole-page y-banded overflow check catches full-width sections above the columns. Scope the check to the column row's y-range, per column.
- **Vision may be down**: if vision_analyze connection-errors, run the whole verification programmatically (spans + fills + pixels) — do not block or retry-loop on it.
- **write_file stale-guard**: before overwriting an existing resume.html/content.json in a later round, `read_file` it fresh in the current task (or use targeted `patch`).
- **Bold fragments in bullets**: the source PDF may bold a fragment of a bullet (metric emphasis). Preserve it as `**strong**` in content.json so the rebuild keeps it.
