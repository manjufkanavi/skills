# PageZen Mock Server Pattern

## Background

The PageZen service in the IacGenie stack is deployed as a mock Node.js/Express server
(`lightserp-pagezen:latest`). It provides basic content extraction from URLs.

## What It Does

- `GET /health` → `{"status":"ok","service":"pagezen","version":"1.0.0"}`
- `POST /extract` with `{"url":"https://example.com"}` → Extracted content with:
  - `title`, `content`, `excerpt`, `finalUrl`
  - `images`, `videos`, `wordCount`, `readingTime`, `language`

## Limitations

- No JavaScript rendering (pure HTTP fetch + basic HTML parsing)
- No PDF processing
- No authentication/authorization
- Basic word count and reading time estimation

## Integration

LightSerp API connects to PageZen via `LIGHTSERP_PAGEZEN_API=http://pagezen:8082`.
LightSerp falls back to its own Readability engine when PageZen is unavailable.

## Production Replacement

For production, replace the mock with the real Page Zen service:
https://github.com/pagezen/pagezen

The real service uses headless Chrome for full JS rendering and supports:
- JavaScript-rendered pages
- PDF content extraction
- Image extraction
- Social media metadata

## Docker Compose Configuration

```yaml
pagezen:
  image: lightserp-pagezen:latest
  container_name: iacgenie_pagezen
  restart: unless-stopped
  ports:
    - "127.0.0.1:8081:8082"
  networks:
    - iacgenie-network
  deploy:
    resources:
      limits:
        memory: "256m"
```
