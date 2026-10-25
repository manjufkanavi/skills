---
name: free-resource-curation
description: Use when downloading free study PDFs into a project repo.
---

# Free Resource Curation

Find legally free study/reference material (books, workbooks, PDFs) and deliver it into a project repo as verified, indexed files. (If the user says "use deep research" for this, the discovery discipline still applies — see the artifact-deliverable variant note there.)

## When to use

Use when the user asks to find/download freely available books, workbooks, or PDF study material for a learning project (e.g. per-JLPT-stage resources, course material, practice sheets into a repo).

## Standing rules

- **"Free" = officially free.** Publisher's own free PDF, university, government/foundation, CC-licensed, or public domain. Confirm the domain is the originator before downloading. Never use document-scraping aggregators (docslib, scribd-style mirrors, "pdf drive"-type sites) — unauthorized copies must not land in a public GitHub repo.
- **Match the user's stated criteria exactly.** List them (e.g. stroke order shown, English examples, actual writing space) in the README index and the commit message so the curation is auditable.

## Procedure

1. **Read the target project** (README/ROADMAP/RESOURCES) to pin the exact stage/level — criteria differ per stage.
2. **Discover**: 3+ `web_search` variants (publisher names, "free <topic> workbook pdf <criterion>", known official sites); `web_extract` for page text.
3. **Direct URLs**: `web_extract` strips links — grep the raw page instead: `curl -sL <page> | grep -oiE 'href="[^"]*\.pdf[^"]*"' | sort -u`. For "free download" buttons, also grep asset hosts (S3/CloudFront/`/downloads/`).
4. **Download**: `curl -sL --fail -o <source>-<purpose>.pdf <url>` into the project dir. Name by source + purpose, never `book1.pdf`.
5. **Verify each file with pypdf**: page count + text probes per criterion (script characters, "stroke", "practice", English markers). A file that is an HTML error page or misses a criterion → remove.
   - `pip install` may be PEP 668-blocked on this machine; `python3 -c "import pypdf"` first — it is often already present.
6. **Index**: write `<dir>/README.md` — table (book / covers / pages / use-for), suggested order, source + free-availability table, re-download links.
7. **Wire in + commit**: pointer line in project docs; check `.gitignore` for exclusions; `git config` identity if unset; `git add <dir> + docs && git commit && git push origin main`.

## Pitfalls

- Workbook PDFs are mostly vector art — text extraction is sparse. Verify by page count + a few probe strings, and note in the README that content is visual.
- A 1-page drill sheet does not satisfy a "book" ask — if the user wants books, include at least one multi-page workbook per skill area, plus the drill sheet for daily practice.
