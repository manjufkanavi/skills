#!/usr/bin/env python3
"""Adapted deep-research runner: underserved Android app ideas (2026).

Serialized TinyFish search+fetch per references/runner-adaptation.md
(never parallel; 0.8s between searches, 1s between fetches, 60s wait on 403).
Research-site phase intentionally skipped — topic is app-market research, not academic.
"""
import os, json, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

KEY = os.environ.get("TINYFISH_API_KEY", "sk-tin...dIsE")
SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"

TOPIC = ("underserved android app ideas that can reach millions of downloads, "
         "solving real problems, with no strong competitors in the market")
SLUG = "android-app-ideas-market-gaps"
MAX_PAGES = 30

QUERIES = [
    "underserved mobile app categories 2026 market gaps",
    "mobile app ideas 2026 no good competitors",
    "fastest growing app categories google play store 2025 2026",
    "why mobile apps fail user pain points retention 2026",
    "app store reviews common complaints unmet user needs",
    "mobile app market discovery problem users cant find good apps 2026",
    "solo developer app millions downloads case study indie hit",
    "mobile app ideas elderly seniors accessibility unmet needs",
    "India mobile app opportunities 2026 emerging market gaps",
    "mobile health apps unmet needs 2026 chronic care adherence",
    "AI mobile apps opportunities 2026 gap in market",
    "fintech app gaps 2026 emerging markets underbanked users",
    "local services small business app gaps 2026",
    "subscription app fatigue what users want in 2026",
    "niche app ideas 2026 underserved audiences",
]

def search(q):
    url = SEARCH_URL + "?query=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={"X-API-Key": KEY})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode()).get("results", [])
        except Exception as e:
            if attempt == 0 and "403" in str(e):
                print(f"  403 rate limit, waiting 60s ({q[:40]})", flush=True)
                time.sleep(60)
                continue
            print(f"  search fail: {e}", flush=True)
            return []
    return []

def fetch(u):
    data = json.dumps({"urls": [u], "format": "markdown"}).encode()
    req = urllib.request.Request(FETCH_URL, data=data, headers={
        "X-API-Key": KEY, "Content-Type": "application/json"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read().decode())
                pr = res.get("results") or []
                p = pr[0] if pr else {}
                return (p.get("text") or p.get("content") or ""), (p.get("title") or "")
        except Exception as e:
            if attempt == 0 and "403" in str(e):
                print(f"  403 rate limit, waiting 60s ({u[:50]})", flush=True)
                time.sleep(60)
                continue
            print(f"  fetch fail: {e}", flush=True)
            return None, ""
    return None, ""

def main():
    base = Path(__file__).resolve().parent.parent
    raw_dir = base / "data" / "raw" / SLUG
    raw_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print(f"Deep research: {TOPIC}", flush=True)
    print(f"Phase 1: {len(QUERIES)} serialized searches, target {MAX_PAGES} pages", flush=True)

    urls, seen = [], set()
    for i, q in enumerate(QUERIES, 1):
        t1 = time.time()
        res = search(q)
        new = [r.get("url") for r in res if r.get("url") and r["url"] not in seen]
        for u in new:
            seen.add(u)
        urls.extend(new)
        print(f"[search {i:2d}/{len(QUERIES)}] {q[:58]!r} -> {len(res)} ({len(new)} new) {time.time()-t1:.1f}s", flush=True)
        time.sleep(0.8)

    target = min(MAX_PAGES, len(urls))
    print(f"Unique URLs: {len(urls)} — fetching top {target} serially", flush=True)
    pages = []
    for j, u in enumerate(urls[:target], 1):
        t1 = time.time()
        content, title = fetch(u)
        if content and len(content.strip()) > 200:
            pages.append({"title": title or u, "content": content[:60000], "url": u})
            print(f"[fetch {j:2d}/{target}] ok {len(content):6d}c {time.time()-t1:.1f}s {u[:70]}", flush=True)
        else:
            print(f"[fetch {j:2d}/{target}] skip (empty/short) {u[:70]}", flush=True)
        time.sleep(1.0)

    (raw_dir / "pages.json").write_text(json.dumps(pages, indent=2, ensure_ascii=False), encoding="utf-8")
    (raw_dir / "pdfs.json").write_text("[]", encoding="utf-8")
    (raw_dir / "research.json").write_text(
        json.dumps({"note": "academic research-site phase skipped — app-market topic, not academic"}),
        encoding="utf-8")

    index_path = base / "data" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    index[SLUG] = {
        "raw_path": str(raw_dir),
        "synthesized_path": str(base / "data" / "synthesized" / SLUG),
        "pages_count": len(pages),
        "pdfs_count": 0,
        "research_count": 0,
        "total_queries": len(QUERIES),
        "rounds": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"DONE in {time.time()-t0:.0f}s — {len(pages)} pages saved to {raw_dir}", flush=True)

if __name__ == "__main__":
    main()
