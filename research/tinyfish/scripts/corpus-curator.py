#!/usr/bin/env python3
"""
corpus-curator.py — Tiny Fish search+fetch pipeline with dedup, cleaning, and manifest.

Usage: python3 -u corpus-curator.py
Config: TINYFISH_API_KEY env var, SEARCH_BASE/FETCH_BASE constants.

Steps:
1. Pick search queries (broad to narrow, site: filters help)
2. For each query, call search API → collect URLs
3. Fetch each URL one-at-a-time (rate-limited)
4. Clean content (remove footers, skip short/binary)
5. Deduplicate by content hash
6. Save manifest with categories
"""

import os, sys, json, hashlib, re, time, urllib.parse, subprocess
from pathlib import Path

# === CONFIG ===
SEARCH_BASE = os.getenv("SEARCH_BASE", "https://api.search.tinyfish.ai")
FETCH_BASE = os.getenv("FETCH_BASE", "https://api.fetch.tinyfish.ai")
KEY = os.environ["TINYFISH_API_KEY"]
CORPUS_DIR = Path(os.environ.get("CORPUS_DIR", "/tmp/corpus/v3"))
MIN_CHARS = 100  # minimum content length to keep
RATE_LIMIT_DELAY = 1.0  # seconds between fetches
MAX_URLS_PER_QUERY = 10

SKIPPED_EXTENSIONS = ('.pdf', '.png', '.jpg', '.jpeg', '.gif', '.zip', '.tar', '.gz')

# === SEARCH QUERIES ===
# Add your queries here. Use site: filters to narrow scope.
# Each query returns up to MAX_URLS_PER_QUERY URLs.
SEARCH_QUERIES = [
    # Example: "AWS service docs"
    "AWS EC2 documentation site:docs.aws.amazon.com",
    "AWS Lambda documentation site:docs.aws.amazon.com",
    # Add more...
]

# === FUNCTIONS ===

def search(query):
    """Search Tiny Fish and return list of URLs"""
    url = f"{SEARCH_BASE}?query={urllib.parse.quote(query)}"
    cmd = ["curl", "-s", url, "-H", f"X-API-Key: {KEY}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        return []
    try:
        data = json.loads(r.stdout)
        return [r["url"] for r in data.get("results", [])[:MAX_URLS_PER_QUERY]]
    except (json.JSONDecodeError, KeyError):
        return []

def fetch(url):
    """Fetch single URL via Tiny Fish fetch API"""
    # Skip PDFs and binary
    if url.lower().endswith(SKIPPED_EXTENSIONS):
        return None

    data = json.dumps({"urls": [url], "format": "markdown"})
    cmd = ["curl", "-s", "-X", "POST", FETCH_BASE,
           "-H", f"X-API-Key: {KEY}", "-H", "Content-Type: application/json", "-d", data]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return None
    try:
        res = json.loads(r.stdout)
        if res.get("results"):
            return res["results"][0].get("text")
        return None
    except json.JSONDecodeError:
        return None

def clean_content(text, source_url, query):
    """Clean fetched content: remove AWS footers, dedup lines"""
    if not text or len(text) < MIN_CHARS:
        return None

    # Remove "Was this page helpful?" footer blocks
    text = re.sub(r'Was this page helpful\?.*?(?=##|$)', '', text, flags=re.DOTALL)

    # Remove repeated navigation breadcrumbs (3+ consecutive same-like lines)
    lines = text.split('\n')
    cleaned = []
    consecutive = 0
    prev_stripped = ""
    for line in lines:
        stripped = line.strip()
        if stripped == prev_stripped and len(stripped) > 10:
            consecutive += 1
            if consecutive < 3:
                cleaned.append(line)
        else:
            consecutive = 0
            cleaned.append(line)
        prev_stripped = stripped

    text = '\n'.join(cleaned).strip()

    # Add header
    now = time.strftime("%Y-%m-%d")
    header = f"""# {source_url.split('/')[-1].replace('-', ' ').replace('.html', '').title()}

---
Source: {source_url}
Fetched: {now}
Query: {query}
---

"""
    return header + text

def content_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

def categorize(url, title):
    """Simple category assignment"""
    u = url.lower()
    t = title.lower()
    if "wellarchitected" in u or "well-architected" in u:
        return "well-architected"
    if any(s in u for s in ["ec2", "lambda", "s3", "dynamodb", "iam", "ecs", "eks"]):
        return "aws-services"
    if any(s in t for s in ["architecture", "reference", "pattern"]):
        return "architecture-center"
    if any(s in u for s in ["pricing", "cost", "savings"]):
        return "pricing-cost"
    return "other"

# === MAIN ===
def main():
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    # Load previously collected URLs
    collected_file = CORPUS_DIR / "collected_urls.json"
    collected_urls = set()
    if collected_file.exists():
        with open(collected_file) as f:
            collected_urls = set(json.load(f))

    all_docs = []
    seen_hashes = set()
    total_fetched = 0
    queries_done = 0

    print(f"Starting corpus collection ({len(SEARCH_QUERIES)} queries, {len(collected_urls)} existing)")
    sys.stdout.flush()
    print("=" * 70)
    sys.stdout.flush()

    for query in SEARCH_QUERIES:
        queries_done += 1
        urls = search(query)
        print(f"[{queries_done}/{len(SEARCH_QUERIES)}] Searching: {query}")
        sys.stdout.flush()

        for url in urls:
            if url in collected_urls:
                continue

            try:
                print(f"  Fetching: {url[:80]}...")
                sys.stdout.flush()
                content = fetch(url)

                if content and content.get("text", "").strip():
                    text = clean_content(content["text"], url, query)
                    if text and len(text) >= MIN_CHARS:
                        h = content_hash(text)
                        if h not in seen_hashes:
                            seen_hashes.add(h)
                            collected_urls.add(url)
                            total_fetched += 1

                            # Save to file
                            fname = h + ".md"
                            fpath = CORPUS_DIR / fname
                            fpath.write_text(text)

                            title = content.get("title", url.split("/")[-1])
                            cat = categorize(url, title)
                            all_docs.append({
                                "file": fname, "title": title,
                                "size": len(text), "source": url, "category": cat
                            })

                            print(f"  ✓ {len(text)} chars")
                            sys.stdout.flush()

                            if total_fetched % 50 == 0:
                                print(f"  [Progress: {total_fetched} unique docs collected]")
                                sys.stdout.flush()
                elif content and not content.get("text", "").strip():
                    print(f"  ✗ Empty/short content")
                    sys.stdout.flush()
                else:
                    print(f"  ✗ Fetch failed")
                    sys.stdout.flush()

            except Exception as e:
                print(f"  ✗ Error: {e}")
                sys.stdout.flush()

            time.sleep(RATE_LIMIT_DELAY)

    # Save manifest
    manifest = {
        "fetched_at": time.strftime("%Y-%m-%d"),
        "total_docs": len(all_docs),
        "total_size_chars": sum(d["size"] for d in all_docs),
        "total_size_mb": round(sum(d["size"] for d in all_docs) / 1_000_000, 2),
        "categories": dict(sorted(
            {d["category"]: sum(1 for x in all_docs if x["category"] == d["category"])
             for d in all_docs}.items(),
            key=lambda x: -x[1]
        )),
        "files": all_docs
    }
    (CORPUS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))

    cat_index = {}
    for d in all_docs:
        cat_index.setdefault(d["category"], []).append({
            "file": d["file"], "title": d["title"], "size": d["size"]
        })
    (CORPUS_DIR / "category_index.json").write_text(json.dumps(cat_index, indent=2))
    (CORPUS_DIR / "collected_urls.json").write_text(json.dumps(sorted(collected_urls), indent=2))

    print(f"\n{'='*70}")
    print(f"COMPLETE: {total_fetched} unique documents collected")
    print(f"Total corpus size: {sum(d['size'] for d in all_docs):,} characters")
    print(f"Saved to: {CORPUS_DIR}")
    sys.stdout.flush()

if __name__ == "__main__":
    main()
