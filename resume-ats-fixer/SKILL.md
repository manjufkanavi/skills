---
name: resume-ats-fixer
description: "Use when rebuilding a resume for ATS: check, fix, send."
tags: [resume, ats, pdf, hiring, quality]
---

# Resume ATS Fixer

## When to Use

- User shares a resume PDF and wants it checked / fixed / rebuilt so it survives ATS screening.
- User asks to "make my resume ATS-safe", "fix the ATS score", or rebuild a resume and verify it parses cleanly.
- Do NOT use for a plain content rewrite with no PDF deliverable, or for a resume that only needs wording changes.

Input: an existing resume PDF. Output: a rebuilt, ATS-safe resume PDF delivered via Telegram (MEDIA: /abs/path/to/file.pdf in the final reply).

Pipeline: **analyze → tokens+content → rebuild HTML → PDF → ATS check → fix loop → re-verify → send.**

All artifacts live in the scratch dir under `resume-ats/`.

## Step 0 — ATS engine setup (one-time per machine)

Resume-Matcher (github.com/srbhr/Resume-Matcher, Apache-2.0, 28k★) provides the deterministic check engine. Its **ATS parse-check, ATS score, and keyword-match need NO LLM** — only the PDF parse and refine steps do.

```
cd $scratch/resume-ats
git clone --depth 1 https://github.com/srbhr/Resume-Matcher.git resume-matcher
cd resume-matcher/apps/backend && uv venv .venv && uv pip install -r requirements.txt --python .venv/bin/python
```

Run the engine: `apps/backend/.venv/bin/python <skill>/scripts/ats_check.py <resume.pdf> [content.json] [--jd jd.json]`
It prints: extractability, every parse check (pass/warn/fail), roundtrip recall/order, and the 5-component ATS score (keyword_match .40, skills_coverage .20, title_match .15, section_completeness .15, date_consistency .10). Set RESUME_MATCHER_DIR if the clone lives elsewhere.

If no JD is available, the built-in representative JD scores it — always label that clearly in the report.

## Step 1 — Read the source resume (programmatic, not vision)

`<skill>/scripts/extract_design.py <resume.pdf> [--out dir]` dumps: page geometry, font/size/color usage (PyMuPDF text spans), vector shape inventory (fills/strokes), 2x rendered PNGs, and PIL pixel runs across the mid-page line for exact panel/bar colors.

- Text layer present (normal resumes are) → PyMuPDF `get_text("dict")` is ground truth; no OCR needed.
- Scanned/image-only PDF → OCR fallback: `markitdown` or tesseract on the 2x renders.
- Vision tools (vision_analyze) frequently fail with "Connection error" — never gate the pipeline on them; PIL pixel sampling + span/drawing dumps are the reliable path.

## Step 2 — Design tokens + content

Write `design-tokens.css` (palette as CSS custom properties, type scale, radii, layout metrics) and `content.json` (structured: header/contact, profile, skill groups, experience entries {title, company, dates, bullets}, education, certifications, languages).

- Colors come from pixel sampling of the source (exact hex), fonts/sizes from span stats.
- Content is transcribed verbatim from the source — never paraphrase, invent, or "improve" without user approval. Content edits (rewording, adding keywords) get presented for approval first.

## Step 3 — Rebuild HTML

Single file, tokens inlined, one `.page` div per page. Non-negotiable rules:

- `@page { size: A4; margin: 0; }` and `.page { width: 210mm; height: 297mm; overflow: hidden }` — Chromium IGNORES pt-based `@page` sizes (falls back to US Letter); mm + A4 keyword is the fix.
- **`letter-spacing` ≤ 0.5pt on every element an ATS must read** (headings, taglines, labels). Above that, pdfminer extracts spaced letters: `P R O F I L E` — sections become unrecognizable.
- **`font-variant-ligatures: none; font-feature-settings: "liga" 0, "clig" 0, "dlig" 0, "calt" 0;` on body.** Chromium's Helvetica Neue emits ﬁ/ﬃ ligature glyphs → "firewall" extracts as "ﬁrewall" and keyword matches silently fail.
- Standard section heading words, synonym at line start: PROFILE/SUMMARY, (PROFESSIONAL) EXPERIENCE, EDUCATION, SKILLS, CERTIFICATIONS. The check engine matches synonyms at line start, so `CORE SKILLS` warns while `SKILLS` passes — prefer the bare word when design allows.
- One date format everywhere (e.g. `Jun 2022 – Present`); contact info (email+phone) in the top of page 1.

## Step 4 — HTML → PDF

`node <skill>/scripts/html2pdf.js <resume.html> <out.pdf>` — Playwright Chromium, explicit `210mm x 297mm`, zero margins, `preferCssPageSize:true`, `printBackground:true`. The script auto-detects the cached Chromium revision and a resolvable playwright-core.

## Step 5 — ATS check + fix loop

Run `ats_check.py` on the new PDF (+ content.json for the score/roundtrip). Triage, most important first:

| Finding | Meaning | Fix |
|---|---|---|
| `garbled_glyphs` fail | unembedded/broken font, (cid:NN) or U+FFFD | switch to an embeddable font family; re-render |
| `text_layer` fail | no extractable text | image-only source → OCR step, or rebuild from content.json |
| spaced letters in raw dump | tracking too high | cap letter-spacing at 0.5pt (step 3 rule) |
| ﬁ/ﬃ glyphs in raw dump | ligatures on | ligature-off CSS (step 3 rule) |
| `section_headings` fail/warn | parser can't map sections | canonical heading words, synonym at line start, single-column sections |
| `contact_info` fail | email/phone missing or buried | both in top third of page 1 |
| `dates` fail | no recognizable dates | month-name + 4-digit year, single format |
| `multi_column` fail | 2+/3-band layout (grids, side columns) | usually ACCEPTABLE: keep if roundtrip content_recall=1.0 and order_fidelity ≥ 0.9 (word interleaving only); otherwise convert grids to stacked lists |
| `header_footer_content` fail | repeated lines look like page chrome | remove repeating header on page 2 |
| keyword/skills gaps in score | JD terms absent | present to user for approval, then add — never fabricate experience |

**Verify after every rebuild** (never trust the edit): 1) re-run `ats_check.py`, 2) raw pdfminer line dump (search for spaced letters + ligature range U+FB00–FB4F), 3) PyMuPDF: page size = A4 (595.27×841.89pt ±3), page count, every span inside the page rect, 4) spot-check key keywords present.

Loop until: no fail except accepted `multi_column`; recall 1.0; no ligature/spaced artifacts; no overflow.

## Step 6 — Finish

Set PDF metadata (title = "Name — Role", author, keywords, creator = "Hermes rebuild vX"). Report: parseability score, extractability, ATS score breakdown (label the JD used), what was fixed, what was accepted (with reason). Deliver `MEDIA:<abs path>.pdf`.

## Pitfalls (learned)

- Chromium `page.pdf()` silently emits US Letter unless width/height are explicit mm — assert A4 in the output every time.
- PyMuPDF `get_text()` and pdfminer space differently; the Resume-Matcher pdfminer path is the ATS-correct one — verify with IT, not with PyMuPDF alone.
- The engine's `section_headings` check wants the synonym at line start; `CORE SKILLS` warns, `SKILLS` passes.
- `write_file` refuses to overwrite files not read first in-task — read before rewrite.
- On this Mac playwright-core lives at `/opt/homebrew/lib/node_modules/@playwright/mcp/node_modules/playwright-core`; Chromium under `~/Library/Caches/ms-playwright/chromium-<rev>/` (rev changes — the script globs it).
- Resume-Matcher `customSections` entries require `sectionType` (stringList + `strings`, or itemList + `items`); the Education model has no `location` field. Pydantic ignores extra keys, missing required keys raise.
- Never invent content to raise the keyword score; missing-JD-term findings go to the user as suggestions.
