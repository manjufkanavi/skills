# Stage 1 — Research (for teaching, not for market briefs)

## Purpose
Collect a tight, credible source set for ONE topic that lets the pedagogy stage
build: a definition, a mechanism, misconceptions, analogies, worked examples,
and quotable claims. **Breadth of subtopic > depth in one source family.**

## Run
```bash
python3 scripts/research.py "<topic>" --max-pages 25 --out projects/<slug>/research
```
- ~8 education-tuned queries (definition / mechanism / misconceptions / example /
  analogy / history / expert debate / real use).
- Authority scoring per source: official docs 3, recognized experts 2, community 1,
  marketing 0 (dropped). Pages are fetched in authority order.
- Output: `research/pages.json` → `[{url, title, domain, authority, content}]`.
- Progress prints with timestamps. 403s are expected rate limits: 60 s wait + 1 retry.

## TinyFish pacing (never violate)
- SERIALIZED calls only. 0.8 s between searches, 1.0 s between fetches.
- Never a thread pool. On 403 → 60 s wait → one retry → then move on.
- Stop at `--max-pages` (default 25). Do NOT force 80 pages; that is the
  old-style market-brief behavior and it dilutes pedagogy.

## Coverage checklist (before stage 2)
Confirm the collected pages can answer all six:
1. What IS it (authoritative definition)?
2. How does it WORK (mechanism, at least one source that shows internals)?
3. What do beginners get WRONG (≥2 distinct misconceptions)?
4. What is a GOOD physical analogy (and where does it break)?
5. What does a real, minimal example look like (code/data, copyable)?
6. What do experts DEBATE (history, controversies, common debates)?

If a bucket is empty, run a targeted top-up: add `--max-queries` or do a manual
web_search for the missing bucket and append its pages to `pages.json` (same shape).

## No API key?
If `TINYFISH_API_KEY` is unset, research.py exits 2 with an empty pages.json.
Then YOU (agent) do the research with your own web_search/web_extract tools:
pick ≥8 URLs (authority-weighted the same way), extract content, and write
`research/pages.json` in the exact same shape:
```json
[{"url": "...", "title": "...", "domain": "...", "authority": 3, "content": "…up to 60000 chars…"}]
```
Mark honestly: authority 1 for pages you could not verify.

## Anti-patterns (things that made old reports boring)
- 26 generic queries + academic fan-out on a practical topic (noise).
- Keyword-scan theme grouping instead of pedagogical extraction.
- Shipping scraped HTML. pages.json is INPUT for you, not output for humans.
