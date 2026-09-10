#!/usr/bin/env python3
"""Curated deep research runner — QA improvement + team leadership topic.

Uses hand-curated Round-1 queries mapped to the user's goal (become a better
QA engineer AND lead the team), then does iterative deepening: if <80 unique
pages, generate follow-up queries from discovered content and repeat (up to 3 rounds).

Progress is flushed so long runs are never silent.
"""
import os, re, json, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

TINYFISH_API_KEY = os.environ.get("TINYFISH_API_KEY")
SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"

# ---- Curated Round-1 queries (mapped to QA improvement + leadership) ----
ROUND_1 = [
    "how to become a better quality assurance engineer 2025 skills roadmap",
    "QA automation testing best practices Selenium Playwright Testify 2025",
    "test strategy design techniques equivalence partitioning boundary value analysis",
    "how to transition from QA engineer to QA lead team management skills",
    "leading a quality assurance team best practices testing manager guide",
    "quality engineering vs traditional QA differences mindset shift 2025",
    "QA engineer career path senior staff principal quality roles progression",
    "metrics for measuring software testing effectiveness DORA test coverage defect leakage",
    "how to build and scale a QA testing team hiring structure org design",
    "shift left testing strategy early bug detection CI CD pipeline integration",
    "AI assisted software testing tools LLM code generation QA 2025 opportunities",
    "quality assurance salary negotiation compensation benchmarking engineer lead",
    "communication and stakeholder management skills for QA leads engineers",
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
    progress(f"Starting curated deep research with {len(ROUND_1)} Round-1 queries")
    all_pages = {}   # url -> (title, content)

    rounds = [ROUND_1]
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
            follow += [f"best {main_word} tool for quality assurance 2025",
                       f"{main_word} best practices team lead"]
        follow = dedup_urls(follow)
        if not follow:
            progress("No meaningful follow-up queries; stopping.")
            break
        current_queries = follow

    # Save research_data.json (structured, topic-matched)
    sources = [{"url": u, "title": t[:200], "preview_len": len(c)} for u, (t, c) in all_pages.items()]
    themes = {k: [] for k in ["overview","automation","strategy","leadership","metrics","ai","careers"]}
    topic = "become-better-qa-engineer-and-lead-team"
    out = {
        "topic": topic,
        "total_pages": len(all_pages),
        "sources": sources,
        "themes": themes,
    }
    dst = os.path.join(os.path.dirname(__file__), "..", "research_data.json")
    dst = os.path.abspath(dst)
    with open(dst, "w") as f:
        json.dump(out, f, indent=2)
    progress(f"\nDONE. Saved {len(all_pages)} unique pages to {dst}")

if __name__ == "__main__":
    main()
