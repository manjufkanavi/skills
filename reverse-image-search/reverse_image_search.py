#!/usr/bin/env python3
"""
Reverse Image Search (OSINT) — no-login engine wrapper.

Queries free reverse image search engines that do NOT require login:
  - TinEye
  - Yandex Images
  - Bing Visual Search
  - Google Lens (web UI)

Given a local image file or an image URL, aggregates and deduplicates results
into a structured JSON report.

Usage:
  python3 reverse_image_search.py --image /path/to/img.jpg [--engines tineye,yandex]
  python3 reverse_image_search.py --url https://example.com/photo.jpg
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from PIL import Image
except ImportError:
    Image = None

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def log(msg):
    print(f"[reverse-image-search] {msg}", file=sys.stderr)


def http_get(url, timeout=20, headers=None, params=None):
    """GET with requests if available, else urllib fallback."""
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    if requests is not None:
        r = requests.get(url, headers=h, params=params, timeout=timeout)
        r.raise_for_status()
        return r.text, r.url
    full = url
    if params:
        full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace"), resp.geturl()


def http_post(url, timeout=20, headers=None, data=None, files=None):
    """POST with requests if available."""
    if requests is None:
        raise RuntimeError("requests library required for POST uploads")
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    r = requests.post(url, headers=h, data=data, files=files, timeout=timeout)
    r.raise_for_status()
    return r.text, r.url


def load_image_bytes(image_path):
    """Read a local image file into bytes."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    with open(image_path, "rb") as f:
        return f.read()


def image_mime(image_path):
    ext = os.path.splitext(image_path)[1].lower()
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
        ".tif": "image/tiff", ".tiff": "image/tiff", ".avif": "image/avif",
    }.get(ext, "image/jpeg")


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

def search_tineye(image_path=None, image_url=None, timeout=20, max_results=20):
    """TinEye — no login for web search. Best for earliest copy / edits.
    Uses the public /api/v1/result_json/ endpoint."""
    results = []
    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        s.get("https://tineye.com/", timeout=timeout)  # get cookies
        params = {"sort": "score", "order": "desc"}
        if image_url:
            params["url"] = image_url
            r = s.get("https://tineye.com/api/v1/result_json/", params=params, timeout=timeout)
        else:
            files = {"image": ("image.jpg", load_image_bytes(image_path), image_mime(image_path))}
            r = s.post("https://tineye.com/api/v1/result_json/", files=files,
                       params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        for m in data.get("matches", [])[:max_results]:
            backlinks = m.get("backlinks", [])
            bl = backlinks[0].get("backlink", "") if backlinks else ""
            results.append({
                "title": m.get("domain", ""),
                "url": bl or m.get("image_url", ""),
                "image_url": m.get("image_url", ""),
                "crawl_date": m.get("crawl_date", ""),
                "source": "tineye",
            })
    except Exception as e:
        log(f"TinEye error: {e}")
    return results


def search_yandex(image_path=None, image_url=None, timeout=20, max_results=20):
    """Yandex Images — no login. Best free engine for face search.
    Uses the imageview URL endpoint and parses embedded result URLs."""
    results = []
    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        if image_url:
            url = "https://yandex.com/images/search?rpt=imageview&url=" + urllib.parse.quote(image_url, safe="")
            html, _ = http_get(url, timeout=timeout)
        else:
            # Upload via Yandex image upload endpoint
            files = {"upfile": ("image.jpg", load_image_bytes(image_path), image_mime(image_path))}
            html, _ = http_post(
                "https://yandex.com/images-apphost/image-download?cbird=1&rpt=imageview",
                timeout=timeout, files=files,
            )
        # Yandex embeds result image URLs in the page; extract external ones.
        # The HTML contains plain https://...jpg URLs (not JSON-escaped), so a
        # simple URL regex is more reliable than the img_href/originalUrl keys.
        seen = set()
        for m in re.finditer(r"https?://[^\"\\ <>]+\.(?:jpg|jpeg|png|webp)", html):
            u = m.group(0).replace("\\u002F", "/")
            if "yandex" in u or "favicon" in u or "yastatic" in u:
                continue
            if u in seen:
                continue
            seen.add(u)
            results.append({"title": u, "url": u, "source": "yandex"})
            if len(results) >= max_results:
                break
    except Exception as e:
        log(f"Yandex error: {e}")
    return results


def search_bing(image_path=None, image_url=None, timeout=20, max_results=20):
    """Bing Visual Search — no login via web UI.
    Parses the murl (media URL) fields embedded in the results page."""
    results = []
    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        if image_url:
            url = "https://www.bing.com/images/search?q=imgurl:" + urllib.parse.quote(image_url, safe="")
            html, _ = http_get(url, timeout=timeout)
        else:
            # Upload via Bing visual search endpoint
            files = {"image": ("image.jpg", load_image_bytes(image_path), image_mime(image_path))}
            html, _ = http_post(
                "https://www.bing.com/images/search?view=detailv2&iss=sbiupload",
                timeout=timeout, files=files,
            )
        # Extract murl (media URL) and turl (thumbnail) fields
        murls = re.findall(r'murl&quot;:&quot;(.*?)&quot;', html)
        titles = re.findall(r't&gt;.*?&lt;/a&gt;', html)
        for i, u in enumerate(murls[:max_results]):
            u = u.replace("\\/", "/")
            results.append({
                "title": titles[i][:80] if i < len(titles) else u,
                "url": u,
                "source": "bing",
            })
    except Exception as e:
        log(f"Bing error: {e}")
    return results


def search_google(image_path=None, image_url=None, timeout=20, max_results=20):
    """Google Lens web UI — no login via lens.google.com.
    Lens redirects to a google.com/search results page; extract result links."""
    results = []
    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        if image_url:
            url = "https://lens.google.com/uploadbyurl?url=" + urllib.parse.quote(image_url, safe="")
            html, _ = http_get(url, timeout=timeout)
        else:
            files = {"encoded_image": ("image.jpg", load_image_bytes(image_path), image_mime(image_path))}
            html, _ = http_post("https://lens.google.com/upload", timeout=timeout, files=files)
        # Lens redirects to google.com/search; extract result links
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a[href^='http']")[:max_results]:
            href = a.get("href", "")
            if "google" in href or "lens" in href or "gstatic" in href:
                continue
            results.append({"title": a.get_text(" ", strip=True) or href, "url": href, "source": "google"})
    except Exception as e:
        log(f"Google Lens error: {e}")
    return results


ENGINES = {
    "tineye": search_tineye,
    "yandex": search_yandex,
    "bing": search_bing,
    "google": search_google,
}


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def normalize_url(u):
    """Normalize a URL for dedup: strip tracking, lowercase host, drop fragments."""
    if not u:
        return ""
    u = u.strip()
    try:
        p = urllib.parse.urlparse(u)
        host = p.netloc.lower()
        path = p.path.rstrip("/")
        return f"{host}{path}"
    except Exception:
        return u


def aggregate(engine_results, max_results=20):
    """Deduplicate results across engines by normalized URL."""
    seen = {}
    for engine, results in engine_results.items():
        for r in results:
            key = normalize_url(r.get("url", ""))
            if not key:
                continue
            if key not in seen:
                seen[key] = {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "engines": [engine],
                }
            else:
                if engine not in seen[key]["engines"]:
                    seen[key]["engines"].append(engine)
    aggregated = sorted(seen.values(), key=lambda x: -len(x["engines"]))
    return aggregated[:max_results]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Reverse image search (OSINT, no-login engines)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--image", help="Path to a local image file")
    src.add_argument("--url", help="URL of an image to search")
    ap.add_argument("--engines", default="tineye,yandex,bing,google",
                    help="Comma-separated engines (default: all)")
    ap.add_argument("--output", default="reverse_image_report.json",
                    help="Output JSON report path")
    ap.add_argument("--timeout", type=int, default=20, help="Per-engine timeout (s)")
    ap.add_argument("--max-results", type=int, default=20, help="Max results per engine")
    args = ap.parse_args()

    if requests is None:
        log("WARNING: requests not installed; some engines may fail")
    if BeautifulSoup is None:
        log("WARNING: bs4 not installed; HTML parsing limited")

    selected = [e.strip().lower() for e in args.engines.split(",") if e.strip()]
    selected = [e for e in selected if e in ENGINES]
    if not selected:
        log(f"No valid engines. Available: {', '.join(ENGINES)}")
        sys.exit(1)

    log(f"Searching engines: {', '.join(selected)}")
    engine_results = {}
    for engine in selected:
        log(f"  -> {engine} ...")
        try:
            engine_results[engine] = ENGINES[engine](
                image_path=args.image, image_url=args.url,
                timeout=args.timeout, max_results=args.max_results,
            )
        except Exception as e:
            log(f"  {engine} failed: {e}")
            engine_results[engine] = []
        time.sleep(1)  # be polite between engines

    aggregated = aggregate(engine_results, max_results=args.max_results)

    report = {
        "query": args.image or args.url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engines": engine_results,
        "aggregated": aggregated,
        "summary": {
            "per_engine": {k: len(v) for k, v in engine_results.items()},
            "total_unique": len(aggregated),
        },
    }

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n=== REVERSE IMAGE SEARCH REPORT ===")
    print(f"Query: {report['query']}")
    print(f"Per-engine hits: {report['summary']['per_engine']}")
    print(f"Total unique: {report['summary']['total_unique']}")
    print("\n--- Aggregated results ---")
    for i, r in enumerate(aggregated, 1):
        print(f"{i}. [{','.join(r['engines'])}] {r['title'][:70]}")
        print(f"   {r['url']}")
    print(f"\nFull report: {args.output}")


if __name__ == "__main__":
    main()
