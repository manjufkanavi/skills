# Adapting the Deep-Research Runners

The bundled runners (`scripts/run_curated.py`, `scripts/run_synthesize.py`) are written for
one legacy project. They must be adapted before reuse, or they violate rate limits and/or
target the wrong topic.

## Why the bundled runners are unsafe as-is

- **`run_curated.py` fetches in parallel.** It wraps `tinyfish_fetch` calls in
  `ThreadPoolExecutor(max_workers=5)`. TinyFish rate-limits concurrent requests, so parallel
  fetches trip a `403` and stall the run. Fetch must be **serialized** (one request at a time).
- **`run_synthesize.py` is topic-hardcoded.** Its theme groupings, summary copy, and title
  are all written for a single prior topic. Reuse requires re-targeting every string, which is
  error-prone — easier to write a fresh synthesis than to patch them.
- **`run_curated.py`'s deepening queries are domain-specific.** The follow-up query templates
  (`"best {word} tool for business 2026"`) assume a SaaS-buzzword corpus and produce junk on
  other domains.

## Correct sequential pattern (rate-limit-safe)

1. **Search one query** via `tinyfish_search`; collect its result URLs.
2. **Pause ~0.8s** before the next query (pacing keeps searches under the limit).
3. **Fetch each URL one at a time** via `tinyfish_fetch` — never with a thread pool. Pause
   ~1s between fetches.
4. **One request may batch many URLs**, but never issue multiple concurrent requests across
   queries or pages.
5. **On HTTP 403**, stop, wait ~60s, then retry the same call. Do not escalate as a broken
   tool; it is an expected rate-limit signal.
6. **Stop deepening** once the page target for this topic is reached (e.g. 25 pages), rather
   than forcing a fixed count.

## Re-targeting for a new topic set

- Define the topics and their query lists in a small JSON index (one entry per topic with an
  `id`, display name, weighting, and ordered `queries`).
- Run **one topic at a time**, serializing all its searches and fetches, saving each
  `pages.json` before moving on. Do not run two topics concurrently.
- Synthesize from the saved `pages.json` with the agent's own reasoning, not a hardcoded
  theme map. Write output as markdown (optionally an HTML companion) per topic.
