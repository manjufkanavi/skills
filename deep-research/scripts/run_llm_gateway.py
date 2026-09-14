#!/usr/bin/env python3
"""Deep research runner — LLM application behind a gateway using Suricata (network inspection) + OpenGuardrails (semantic inspection).

Hand-curated Round-1 queries mapped to the user's SaaS product concept, then
iterative deepening: if <80 unique pages, generate follow-up queries from
discovered content and repeat (up to 3 rounds). Reuses the proven Tiny-Fish
search/fetch + text-cleaning logic from run_curated*.py.

Progress is flushed so long runs are never silent.
"""
import os, re, json, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

TINYFISH_API_KEY = os.environ.get("TINYFISH_API_KEY")
SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"

# ---- Curated Round-1 queries (mapped to the user's SaaS concept) ----
ROUND_1 = [
    "Suricata network inspection LLM API gateway traffic analysis",
    "OpenGuardrails Salesforce semantic guardrail framework prompt injection defense",
    "LLM gateway API proxy request response filtering security enterprise",
    "AI governance guardrail framework LLM input output compliance 2025",
    "Suricata IDS custom rules prompt injection detection evasion API traffic",
    "semantic guardrail vs syntactic guardrail LLM input output filtering framework",
    "enterprise LLM gateway routing request inspection observability logging tracing",
    "LLM API security prompt injection response injection attack defense 2025",
    "self-hosted AI safety platform enterprise data loss prevention LLM gateway",
    "OpenGuardrails semantic guardrail architecture Salesforce implementation example",
    "model context protocol MCP server security gateway request inspection",
    "AI agent safety guardrail framework comparison LangGuard Llama Guard OpenGuardrails 2025",
    "LLM gateway business model SaaS pricing enterprise security compliance product",
]

def progress(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def tinyfish_search(query, max_results=10):
    if not TINYFISH_API_KEY:
        return []
    try:
        url = f"{SEARCH_URL}?query={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"X-API-Key": TINYFISH_API_KEY})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode()).get("results", [])
    except Exception as e:
        progress(f"  ✗ search failed for {query!r}: {e}")
        return []

def tinyfish_fetch(url):
    if not TINYFISH_API_KEY:
        return None, ""
    try:
        data = json.dumps({"urls": [url], "format": "markdown"}).encode()
        req = urllib.request.Request(FETCH_URL, data=data, headers={
            "X-API-Key": TINYFISH_API_KEY, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            pages = json.loads(resp.read().decode()).get("results", [])
        if pages:
            p = pages[0]
            return (p.get("text") or p.get("content") or ""), (p.get("title") or "")
        return "", ""
    except Exception as e:
        progress(f"  ✗ fetch failed for {url[:60]}...: {e}")
        return None, ""

CLEAN_PATTERNS = [
    r'About Press Copyright Contact us Creators.*?Google LLC',
    r'Checking your browser.*?reCAPTCHA',
    r'\d+\s*views\s*(ago|•)', r'\d+\s*subscribers', r'Member-only story\s+',
    r'\d+\s*min read', r'• Follow ---', r'Sign up Log in',
]

def clean(text):
    if not text:
        return ""
    t = re.sub(r'<[^>]+>', '', text)
    for pat in CLEAN_PATTERNS:
        t = re.sub(pat, '', t, flags=re.DOTALL)
    return re.sub(r'\s+', ' ', t).strip()

def dedup_urls(urls):
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u); out.append(u)
    return out

def main():
    topic = "llm-gateway-suricata-openguardrails-inspection-saas"
    progress(f"Starting deep research on {topic} with {len(ROUND_1)} Round-1 queries")
    all_pages = {}   # url -> (title, content)

    current_queries = ROUND_1
    total_scraped = 0

    for rnd in range(1, 4):
        progress(f"\n=== ROUND {rnd}: searching {len(current_queries)} queries ===")
        all_urls = []
        for q in current_queries:
            progress(f"  ▸ {q[:70]}")
            for r in tinyfish_search(q):
                u = r.get("url", "") or ""
                t = r.get("title", "") or "(untitled)"
                if u:
                    all_urls.append((u, t))
            time.sleep(0.8)

        unique = dedup_urls([u for u, _ in all_urls])
        progress(f"  found {len(unique)} unique URLs this round (total collected: {len(all_pages)})")

        # Scrape in batches of 10
        to_scrape = [u for u in unique if u not in all_pages]
        batch, fetched_titles = [], []
        for i, url in enumerate(to_scrape):
            batch.append(url)
            if len(batch) >= 10:
                with ThreadPoolExecutor(max_workers=5) as ex:
                    results = list(ex.map(tinyfish_fetch, batch))
                for url, (content, title) in zip(batch, results):
                    if content and len(content) > 100:
                        all_pages[url] = (title, content)
                total_scraped += len(batch)
                progress(f"  scraped {total_scraped}/{len(all_pages)} pages...")
                batch = []
        if batch:
            with ThreadPoolExecutor(max_workers=5) as ex:
                results = list(ex.map(tinyfish_fetch, batch))
            for url, (content, title) in zip(batch, results):
                if content and len(content) > 100:
                    all_pages[url] = (title, content)
            total_scraped += len(batch)

        progress(f"  unique pages so far: {len(all_pages)}")
        if len(all_pages) >= 80:
            progress("Target reached (>=80 pages). Stopping deepening.")
            break
        if rnd == 3:
            progress("Max rounds reached.")
            break

        # Deepening: generate follow-up queries from discovered content/topics
        topics = [t.lower() for u, (t, c) in list(all_pages.items())[:40]]
        follow = []
        for seed in topics:
            words = re.findall(r'[a-z0-9]{4,}', seed)
            if not words:
                continue
            main_word = max(set(words), key=words.count)
            if len(main_word) < 5:
                continue
            follow += [f"best {main_word} tool for LLM gateway security 2025",
                       f"{main_word} enterprise implementation guide"]
        follow = dedup_urls(follow)
        # limit to ~14 fresh queries per deepening round, keep domain-relevant ones
        follow = [f for f in follow if ("2025" in f or "LLM" in f.upper() or "gateway" in f.lower()
                                          or "guardrail" in f.lower() or "suricata" in f.lower())][:14]
        if not follow:
            progress("No meaningful follow-up queries; stopping.")
            break
        current_queries = follow

    # Save raw data under data/raw/<topic>/
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw", topic)
    os.makedirs(base_dir, exist_ok=True)
    pages_path = os.path.join(base_dir, "pages.json")
    with open(pages_path, "w") as f:
        json.dump([{"url": u, "title": t[:300], "content": c} for u, (t, c) in all_pages.items()],
                  f, indent=2)
    progress(f"\nDONE. Saved {len(all_pages)} unique pages to {pages_path}")
    # Also write a compact sources index at research_data.json for the synthesize step
    sources = [{"url": u, "title": t[:200], "preview_len": len(c)} for u, (t, c) in all_pages.items()]
    themes = {k: [] for k in ["overview","suricata-network-inspection","openguardrails-semantic-inspection",
                                "gateway-routing","security-threats","compliance","business-model","future"]}
    out = {
        "topic": topic,
        "total_pages": len(all_pages),
        "sources": sources,
        "themes": themes,
    }
    dst = os.path.join(os.path.dirname(__file__), "..", "research_data.json")
    with open(dst, "w") as f:
        json.dump(out, f, indent=2)
    progress(f"Saved research_data.json with {len(sources)} sources")

if __name__ == "__main__":
    main()
