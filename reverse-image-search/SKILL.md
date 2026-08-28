---
name: reverse-image-search
description: OSINT reverse image search skill. Queries no-login reverse image search engines (TinEye, Yandex Images, Bing Visual Search, Google Lens web UI) for a local image file or image URL, aggregates and deduplicates results, and outputs a structured report.
---

# Reverse Image Search (OSINT)

Reverse image search across free, **no-login** engines. Given a local image file or an image URL, this skill queries multiple engines, aggregates the hits, deduplicates them, and produces a structured report.

## When to use (trigger phrases)

- "reverse image search"
- "find this image online"
- "where is this photo from"
- "search this picture"
- "find the source of this image"
- "is this image used elsewhere"

## Requirements

- Python 3 with `requests`, `bs4` (BeautifulSoup), `PIL` (Pillow)
- Internet access to the target engines

## Usage

```bash
python3 skills/reverse-image-search/reverse_image_search.py \
  --image /path/to/image.jpg \
  --engines tineye,yandex,bing,google \
  --output report.json
```

Or search by image URL:

```bash
python3 skills/reverse-image-search/reverse_image_search.py \
  --url "https://example.com/photo.jpg" \
  --engines tineye,yandex
```

### Arguments

| Flag | Description |
|------|-------------|
| `--image` | Path to a local image file |
| `--url` | URL of an image to search (mutually exclusive with `--image`) |
| `--engines` | Comma-separated engines: `tineye,yandex,bing,google` (default: all) |
| `--output` | Path to write the JSON report (default: `reverse_image_report.json`) |
| `--timeout` | Per-engine request timeout in seconds (default: 20) |
| `--max-results` | Max results to keep per engine (default: 20) |

## Engines

All engines are queried **without login/account**:

- **TinEye** — best for finding the earliest copy and tracking edits; sort by oldest.
- **Yandex Images** — best free engine for face reverse search (65–75% accuracy).
- **Bing Visual Search** — good object/product matches Google misses.
- **Google Lens (web UI)** — strong for objects, products, landmarks, and text-in-image.

## Output

The script writes a JSON report with:

- `query` — the image source (file path or URL)
- `timestamp` — when the search ran
- `engines` — per-engine results (title, url, thumbnail, source)
- `aggregated` — deduplicated results across all engines
- `summary` — counts per engine and total unique hits

## Notes

- Engines may rate-limit or change their HTML; the script degrades gracefully and reports per-engine errors rather than failing the whole run.
- For face search, Yandex is the strongest free option.
- This skill does **not** modify any existing skills.

## Engine Endpoint Details

- **TinEye** — works via upload (`POST /api/v1/result_json/` multipart image upload, then `GET /api/v1/result_json/{query_hash}`). URL-based search fails (422/400) when TinEye can't fetch the image (e.g., redirecting URLs).
- **Yandex Images** — upload endpoint is `https://yandex.com/images/search?rpt=imageview` with `upfile` field (the `images-apphost` endpoint returns 400 "Incorrect avatar size"). Results are fully JS-rendered/obfuscated — parsing embedded URLs is unreliable, best-effort only.
- **Bing Visual Search** — works via URL (`q=imgurl:<url>`) parsing `murl` fields (~97 results). The upload POST path returns a JS-redirect page and needs a follow-up GET; URL-based approach works better.
- **Google Lens (web UI)** — upload endpoint is `https://lens.google.com/upload` with `encoded_image` field; results redirect to google.com/search. Result extraction is unreliable.
- **Self-hosted alternative** — CLIP + FAISS (or CLIP + pgvector) for local image similarity.
