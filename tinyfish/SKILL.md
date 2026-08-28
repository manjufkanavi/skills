---
name: tinyfish
description: Search the web and scrape web pages using Tiny Fish AI API.
---

# Tiny Fish

Search the web and scrape web pages using the Tiny Fish AI API.

## When to use (trigger phrases)

Use this skill immediately when the user asks any of:
- "search the web"
- "search online"
- "look this up"
- "scrape this page"
- "fetch this URL"
- "get content from"
- "what's on this page"
- "tiny fish search"
- "tiny fish scrape"
- "tiny fish fetch"

## API Key

The API key is stored in `personal_bot/README.md` as `X-API-Key: sk-tinyfish-vHbgNi2R-tVLAXFixslJ3lk5iz71dIsE`

## Search

Search the web and get structured results with snippets:

```bash
curl -s "https://api.search.tinyfish.ai?query=your+search+query" \
  -H "X-API-Key: sk-tinyfish-vHbgNi2R-tVLAXFixslJ3lk5iz71dIsE"
```

Example:
```bash
curl -s "https://api.search.tinyfish.ai?query=best+ramen+in+nyc" \
  -H "X-API-Key: sk-tinyfish-vHbgNi2R-tVLAXFixslJ3lk5iz71dIsE"
```

Response includes:
- `query` — the search query
- `results` — array of results with `position`, `site_name`, `title`, `snippet`, `url`, `date`
- `total_results` — total number of results
- `page` — current page

## Scrape / Fetch

Fetch and extract content from any URL in markdown format:

```bash
curl -s -X POST https://api.fetch.tinyfish.ai \
  -H "X-API-Key: sk-tinyfish-vHbgNi2R-tVLAXFixslJ3lk5iz71dIsE" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com"], "format": "markdown"}'
```

Example:
```bash
curl -s -X POST https://api.fetch.tinyfish.ai \
  -H "X-API-Key: sk-tinyfish-vHbgNi2R-tVLAXFixslJ3lk5iz71dIsE" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://news.ycombinator.com"], "format": "markdown"}'
```

Response includes:
- `results` — array with `url`, `final_url`, `title`, `text` (markdown), `latency_ms`
- `errors` — any errors encountered

## Workflow

1. **Search first** — Use the search endpoint to find relevant URLs
2. **Then scrape** — Use the fetch endpoint on the most relevant URLs to get full content
3. **Summarize** — Present the results concisely to the user

## Tips

- URL-encode spaces in search queries: `best+ramen+in+nyc`
- The fetch endpoint supports multiple URLs in one request
- Response format defaults to markdown — great for summarization
- The API is fast (~300ms for fetch), so it's suitable for real-time use
