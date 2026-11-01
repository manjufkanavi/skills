#!/usr/bin/env python3
"""Deep research collector: LFM3-1.7B CPU inference (quant + engine selection).

Rate-limit-safe pattern (see references/runner-adaptation.md):
- searches serialized with ~0.8s pacing
- fetches serialized with ~1s pacing
- on HTTP 403: wait 60s, retry once
"""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone

TINYFISH_API_KEY = os.environ.get("TINYFISH_API_KEY", "sk-tin...dIsE")
SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"
SKILL_DIR = os.path.expanduser("~/.hermes/skills/deep-research")
SLUG = "lfm3-17b-cpu-inference"
RAW_DIR = os.path.join(SKILL_DIR, "data", "raw", SLUG)
os.makedirs(RAW_DIR, exist_ok=True)
PAGES_FILE = os.path.join(RAW_DIR, "pages.json")

QUERIES = [
    "LFM3-1.7B GGUF llama.cpp CPU inference",
    "LiquidAI LFM3 tri-hybrid architecture convolution attention",
    "llama.cpp lfm3 model support",
    "llama.cpp CPU inference best quantization Q4_K_M Q8_0",
    "llama.cpp llama-bench prompt processing benchmark",
    "llama.cpp CPU flash attention KV cache performance",
    "llama.cpp CPU threads tuning performance cores",
    "i7-6700K DDR4 dual channel memory bandwidth GB/s",
    "llama.cpp 64K context CPU KV cache memory usage",
    "LocalAI GGUF llama.cpp backend CPU",
    "sliding window attention inference efficiency edge LLM",
    "Liquid AI LFM3 gated convolution edge inference",
]

PRIORITY_URLS = [
    "https://huggingface.co/LiquidAI/LFM3-1.7B-Base",
    "https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF",
    "https://huggingface.co/saidutta69/LFM3-1.7B-Base-heretic",
    "https://docs.liquid.ai/lfm/models/lfm3-1.7b",
    "https://docs.liquid.ai/deployment/on-device/llama-cpp",
    "https://www.liquid.ai/blog/lfm3",
    "https://github.com/ggml-org/llama.cpp/pull/31252",
    "https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md",
    "https://github.com/ggml-org/llama.cpp",
    "https://github.com/mudler/localai",
    "https://localai.io/docs/",
    "https://github.com/ggml-org/llama.cpp/releases/tag/b12024",
]


def call_api(url, payload=None, retry_wait=60):
    headers = {"X-API-Key": TINYFISH_API_KEY}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt == 0:
                print(f"    403 rate-limit, waiting {retry_wait}s ...", flush=True)
                time.sleep(retry_wait)
                continue
            print(f"    HTTP {e.code}: {e.reason}", flush=True)
            return None
        except Exception as e:
            print(f"    error: {e}", flush=True)
            return None
    return None


def search(query):
    url = f"{SEARCH_URL}?query={urllib.parse.quote(query)}"
    res = call_api(url)
    if res is None:
        return []
    return res.get("results", []) or []


def fetch(url):
    res = call_api(FETCH_URL, {"urls": [url], "format": "markdown"})
    if res is None:
        return None, ""
    pages = res.get("results", [])
    if not pages:
        return None, ""
    return pages[0].get("text") or pages[0].get("content") or "", pages[0].get("title") or ""


def main():
    found_urls = []
    for q in QUERIES:
        print(f"SEARCH: {q}", flush=True)
        results = search(q)
        for r in results[:5]:
            u = r.get("url") or r.get("link") or ""
            if u and u not in found_urls:
                found_urls.append(u)
        time.sleep(0.8)
    print(f"\nSearch collected {len(found_urls)} unique URLs", flush=True)

    # merge: priority first, then search results
    to_fetch = list(PRIORITY_URLS)
    for u in found_urls:
        if u not in to_fetch:
            to_fetch.append(u)
    # skip localai.io/docs (JS-heavy) — keep github readme; drop noise
    to_fetch = [u for u in to_fetch if not u.startswith(("https://twitter.com", "https://x.com", "https://www.youtube.com"))]
    to_fetch = to_fetch[:40]  # cap fetch quota

    pages = []
    for i, u in enumerate(to_fetch):
        print(f"FETCH [{i+1}/{len(to_fetch)}]: {u}", flush=True)
        content, title = fetch(u)
        if content:
            pages.append({"url": u, "title": title or u, "content": content,
                          "chars": len(content),
                          "timestamp": datetime.now(timezone.utc).isoformat()})
            print(f"    ok: {len(content)} chars, title={(title or u)[:60]!r}", flush=True)
        else:
            print(f"    FAILED: {u}", flush=True)
        # checkpoint after every fetch so a crash doesn't lose work
        with open(PAGES_FILE, "w") as f:
            json.dump({"topic": SLUG, "collected_at": datetime.now(timezone.utc).isoformat(),
                       "queries": QUERIES, "pages": pages}, f)
        time.sleep(1.0)

    with open(PAGES_FILE, "w") as f:
        json.dump({"topic": SLUG, "collected_at": datetime.now(timezone.utc).isoformat(),
                   "queries": QUERIES, "pages": pages}, f, indent=1)
    print(f"\nSaved {len(pages)} pages -> {PAGES_FILE}", flush=True)
    for p in pages:
        print(f"  - {p['title'][:70]!r} ({p['chars']} chars) <- {p['url'][:60]}", flush=True)


if __name__ == "__main__":
    main()
