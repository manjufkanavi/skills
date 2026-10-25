# ATS / AI-Screening Hardening Checklist

The resume must parse as clean text, carry the right phrases, and read well for the human who gets past the filter.

## Text-layer integrity
- Real selectable text only (never images of your own output). Embedded font subsets (e.g. Helvetica Neue) are fine.
- Set PDF metadata after conversion: pymupdf `set_metadata({ title: "Name — Role", author, subject: "Resume", keywords: "top 15 phrases" })`.
- No wide letter-spacing on keyword text: tracking extracts as per-character spaces and breaks phrase matching. Keep ≤ ~0.5pt and verify the exact phrase survives pymupdf extraction as one string.
- Kill ligatures: `font-variant-ligatures: none; font-feature-settings: "liga" 0, "clig" 0, "dlig" 0;` — Chromium + the Helvetica family renders ﬁ/ﬃ/ﬄ as single glyphs ("ﬁrewall") that fail exact-word searches. Verify by extracting a word containing "fi" with pdfminer.
- Avoid tables; multi-column is OK for modern systems (Workday, Greenhouse, Avionté) when text-layer order is logical — keep DOM order = reading order and verify per-column overflow.

## Phrases & placement
- Skills section with exact job-posting phrases near the top (skills-first works for senior ICs — early placement gets weighting).
- Only add skills that existing content evidences (a degree, a tool named in a bullet). Flag inferred ones (e.g. Agile from JIRA use) to the user in the approval round.
- Dates: title case + en-dash ("Jun 2022 – Present"); a completed degree shows a full range, never "Ongoing/Expected".
- Contact: full `https://` URLs; verify handle spellings and pin codes with the user, never silently "fix" them.
- Job titles as actually held; normalize brand spellings (JIRA → Jira).

## Bullets
- ≤ 2 lines, action-verb openers, a metric in most, trim tails that restate the lead.
- Keep every existing metric — they are the resume's evidence.

## Length
- 2 pages is fine at 9+ years; never pad. Check bottom slack per page after every rebuild.

## External validation (Resume-Matcher, srbhr/Resume-Matcher — Apache-2.0, ~29k★)

Independent, local, deterministic — no LLM, no key, no upload. The repo's `apps/backend/app/services/` holds the engine:
- `ats_parse` — pdfminer extraction + checks (text_layer, garbled_glyphs, text_coverage, multi_column, header_footer, images, page_count, contact_info, section_headings, dates) + roundtrip vs a structured dict (content_recall / order_fidelity).
- `refiner.calculate_keyword_match(resume_dict, jd_dict)` — word-boundary match % ("python" ≠ "pythonic").
- `ats.compute_ats_score(...)` — weighted composite: keyword_match .40 / skills_coverage .20 / title_match .15 / section_completeness .15 / date_consistency .10 (unevaluable → None, weight redistributed).

Run:
1. `git clone --depth 1 https://github.com/srbhr/Resume-Matcher.git <workdir>/resume-matcher`
2. `cd resume-matcher/apps/backend && uv venv .venv && uv pip install -r requirements.txt --python .venv/bin/python` (litellm is only imported; the score path never calls an LLM).
3. Write a runner at the repo root with `sys.path.insert(0, "<abs path to apps/backend>")`; import `extract_pdf` (sync, bytes → ExtractedDocument), `build_report(doc, source="upload", resume_data=dict)` → ParseCheckReport, plus `calculate_keyword_match` / `job_keyword_terms` / `compute_ats_score`.
4. Build the resume dict in ResumeData shape (pydantic-validated): `personalInfo{name,title,email,phone,location,linkedin}`, `summary`, `workExperience[{id,title,company,location,years,description[]}]`, `education[{id,institution,degree,years,description:str}]`, `additional{technicalSkills:[...]}`, `customSections{<name>:{sectionType:"stringList",strings:[...]}}` — a CustomSection missing `sectionType` fails validation. Map years verbatim from content.json, single date style.
5. JD dict `{role, required_skills[], preferred_skills[], keywords[]}`: real posting terms when the user has one; otherwise synthesize a representative role for the resume's niche and label it as such in the report.

Reading the output:
- `extractability: full` + 0 garbled glyphs = text layer healthy.
- `section_headings` failing with almost nothing found is usually tracking/ligature breakage of the rendered headings, not a content gap — grep the raw extracted lines for the heading; `P R O F I L E`-style output = tracking bug in the HTML.
- `multi_column` failing = a page has a 2+ column band (skill grids, 3-col footer rows). Content is usually fully present (roundtrip recall 1.0); it flags interleaved reading order — low/medium severity.
- keyword/skills/title components are JD-relative — always report the JD used with them; the JD-independent verdicts are the parse checks + section_completeness + date_consistency.
