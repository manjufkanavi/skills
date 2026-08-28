---
name: whats-trending
description: Fetch and save trending topics in 3 categories (India, Karnataka, Global) using Google Trends + Google News RSS. Results are stored as JSON files. Trigger: "what's trending", "trending topics", "run trending".
---

# What's Trending

Fetches current trending topics across 3 categories:

| Category | Source | Method |
|----------|--------|--------|
| **India** | Google Trends (`trends.google.com/trending?geo=IN`) | Direct HTML fetch → Jina Reader fallback → TinyFish news-search top-up to **exactly 10** |
| **Karnataka** | Google News RSS (`news.google.com/rss/search?q=karnataka+Bengaluru&hl=en-IN&gl=IN&ceid=IN:en`) | RSS XML parse → TinyFish news-search top-up to **exactly 10** |
| **Karnataka (Dork)** | Google dork queries via TinyFish search | Runs `after:<date>` dork queries against a curated list of 10 Karnataka + 10 India news sites (`site:` operator) plus generic Karnataka queries. Filters to news domains, keeps articles <1 week old (auto-computed 7-day window), deduplicates by title → top 10 |
| **Global** | Google Trends GLOBAL + Google News RSS top stories | Google Trends (`geo=GLOBAL`) → Google News RSS top stories → TinyFish news-search top-up to **exactly 10** |

## Karnataka Dork List (46 queries)

The Karnataka dork category builds 46 queries at runtime:
- **6 generic** Karnataka/Bengaluru news queries
- **20 curated news sites × 2 city keywords** (karnataka, bengaluru) using `site:<domain> <city> after:<date>`
- `after:<date>` is auto-computed as 7 days back at runtime (not hardcoded)

**Curated Karnataka news sites (10):** Deccan Herald, The Hindu, TOI, New Indian Express, Indian Express, Hans India, Bangalore Mirror, Vijay Karnataka, Prajavani, Udayavani

**Curated India news sites (10):** NDTV, TOI, The Hindu, Indian Express, Hindustan Times, News18, The Print, Economic Times, Mint, Republic World

The RSS-based list and the dork-based list are complementary (zero overlap in test runs).

## Guarantee: 10 topics per category

Every category is **guaranteed to return exactly 10 topics** (`MIN_TRENDS = 10`). If the primary source (Google Trends / Google News RSS) returns fewer than 10, the script automatically **tops up** the list using TinyFish news searches (`top_up_to_ten()`), filtering to news domains and deduplicating by normalized title until 10 are reached. This prevents any category from being short.

## Usage

```bash
python3 scripts/trending.py --output /path/to/output
```

Default output: `./trending_output/`

## Output Files

| File | Category |
|------|----------|
| `india_trends.json` | India trending topics (search volume from Google Trends) |
| `karnataka_trends.json` | Karnataka news articles (from Google News RSS) |
| `karnataka_dork_trends.json` | Karnataka news via Google dork + TinyFish (news <1 week old, deduped) |
| `world_trends.json` | Global trending stories (from Google News RSS) |

## Output Format

```json
{
  "category": "karnataka",
  "label": "Karnataka",
  "timestamp": "2026-07-25T12:00:00+00:00",
  "total_results": 10,
  "trends": [
    {
      "rank": 1,
      "title": "Headline of the article",
      "snippet": "Source · date",
      "source": "The Hindu / Deccan Herald / ...",
      "url": "https://news.google.com/...",
      "pubdate": "Sat, 25 Jul 2026 ..."
    }
  ]
}
```

## API Key

Tiny Fish API key stored in `trending.py`. Falls back to `TINYFISH_API_KEY` env var.
