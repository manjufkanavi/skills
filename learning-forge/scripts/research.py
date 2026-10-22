#!/usr/bin/env python3
"""Focused education research collector for learning-forge.

NOT the generic 80-page market brief. This collects a tight, authority-weighted
source set for ONE topic with education-specific queries, then the agent (you)
reads pages.json and authors pedagogy.json (see references/01-research.md and
references/02-pedagogy.md).

Design rules:
- SERIALIZED network calls only (TinyFish rate-limits parallel requests).
- 0.8s pause between searches, 1.0s between fetches; on HTTP 403 wait 60s, retry once.
- Authority scoring: official docs 3 > recognized experts 2 > community 1 > marketing 0.
- Stops at --max-pages (default 25). Coverage checklist is checked at the end.

Output: <out>/pages.json  (list of {url, title, content, authority, domain})
Exit codes: 0 ok, 2 no API key (pages.json still written with what we have).
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"

# Education query templates — each targets a different pedagogical need.
QUERY_TEMPLATES = [
    "{t} explained simply for beginners",
    "how {t} works under the hood",
    "{t} common misconceptions mistakes beginners make",
    "{t} worked example tutorial",
    "best analogy to understand {t}",
    "{t} history why it was invented",
    "{t} expert debate controversy",
    "{t} real world use cases production",
]

# Domain authority scoring (checked in order; first match wins).
AUTHORITY = [
    (3, [".org/", "docs.python.org", "peps.python.org", "python.org", "docs."],
        "official/standard docs"),
    (3, ["developer.mozilla.org", "docs.github.com", "kotlinlang.org", "go.dev",
         "nodejs.org", "rust-lang.org", "react.dev", "vuejs.org", "angular.dev",
         "tensorflow.org", "pytorch.org", "huggingface.co/docs", "w3.org"], "vendor official docs"),
    (2, ["realpython.com", "jasonfried.tech", "paulgraham.com", "norvig.com", "lwn.net",
         "martinfowler.com", "blog.golang.org", "css-tricks.com", "smashingmagazine.com",
         "diveinto", "two-scoops", "fluentpython", "automatetheboringstuff",
         "arxiv.org", "nature.com", "science.org", "acm.org", "ieee.org",
         "stackoverflow.com/questions"], "recognized expert / Q&A"),
    (1, ["medium.com", "dev.to", "hashnode", "github.com", "youtube.com",
         "freeCodeCamp", "freecodecamp.org", "geeksforgeeks", "tutorialspoint",
         "dzone.com", "hackernoon.com"], "community/tutorial"),
    (0, ["amazon.com", "shopify", "clickfunnels", "semrush", "hubspot",
         "get." , "try." , "buy."], "marketing — skipped unless nothing else"),
]

CLEAN_PATTERNS = [
    r'About Press Copyright Contact us Creators.*?Google LLC',
    r'Checking your browser.*?reCAPTCHA',
    r'\d+\s*views\s*(ago|•)', r'\d+\s*subscribers', r'Member-only story\s+',
    r'\d+\s*min read', r'• Follow ---', r'Sign up Log in',
    r'(Subscribe|Follow|Sign up)\s+(to|for|on)\b.{0,80}newsletter',
    r'Cookie settings.{0,200}?(Cookie settings|Accept all)',
]

def progress(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def api_get(url):
    key = os.environ.get("TINYFISH_API_KEY")
    if not key: return None
    req = urllib.request.Request(url, headers={"X-API-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            progress("  403 rate-limit; waiting 60s then one retry")
            time.sleep(60)
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode())
            except Exception as e2:
                progress(f"  retry failed: {e2}"); return None
        progress(f"  HTTP {e.code}"); return None
    except Exception as e:
        progress(f"  {e}"); return None

def api_fetch(urls):
    key = os.environ.get("TINYFISH_API_KEY")
    if not key: return None
    data = json.dumps({"urls": urls, "format": "markdown"}).encode()
    req = urllib.request.Request(FETCH_URL, data=data,
        headers={"X-API-Key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode()).get("results", [])
    except urllib.error.HTTPError as e:
        if e.code == 403:
            progress("  403 on fetch; waiting 60s then one retry")
            time.sleep(60)
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read().decode()).get("results", [])
            except Exception as e2:
                progress(f"  retry failed: {e2}"); return None
        progress(f"  HTTP {e.code}"); return None
    except Exception as e:
        progress(f"  {e}"); return None

def score_authority(url, title=""):
    blob = (url + " " + title).lower()
    for score, pats, label in AUTHORITY:
        for p in pats:
            if p.lower() in blob:
                return score, label
    return 2, "default (assumed credible)"

def clean(text):
    if not text: return ""
    t = re.sub(r'<[^>]+>', '', text)
    for pat in CLEAN_PATTERNS:
        t = re.sub(pat, '', t, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r'\s+', ' ', t).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--max-pages", type=int, default=25)
    ap.add_argument("--max-queries", type=int, default=len(QUERY_TEMPLATES))
    ap.add_argument("--max-chars", type=int, default=60000,
                    help="per-page content cap in pages.json (keep files tractable)")
    ap.add_argument("--out", required=True, help="output dir for pages.json")
    a = ap.parse_args()

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("TINYFISH_API_KEY"):
        progress("WARNING: TINYFISH_API_KEY not set — writing empty pages.json. "
                 "Agent: use your own web_search/web_extract tools and write pages.json "
                 "in the same shape (see references/01-research.md).")
        (out / "pages.json").write_text("[]")
        sys.exit(2)

    topic = a.topic
    queries = [q.format(t=topic) for q in QUERY_TEMPLATES[:a.max_queries]]
    seen, cand = set(), []          # url -> meta
    for qi, q in enumerate(queries, 1):
        progress(f"search {qi}/{len(queries)}: {q}")
        data = api_get(f"{SEARCH_URL}?query={urllib.parse.quote(q)}&max_results=10")
        for r in (data or {}).get("results", []):
            u = r.get("url") or r.get("link") or ""
            if u and u not in seen:
                seen.add(u)
                cand.append({"url": u, "title": r.get("title", ""),
                              "desc": r.get("description", ""),
                              "authority": score_authority(u, r.get("title", ""))[0],
                              "domain": urllib.parse.urlparse(u).netloc})
        time.sleep(0.8)
    progress(f"{len(cand)} unique candidate URLs; ranking by authority")
    cand.sort(key=lambda c: -c["authority"])
    top = [c for c in cand if c["authority"] > 0][: a.max_pages * 2]

    pages, used = [], set()
    for c in top:
        if len(pages) >= a.max_pages: break
        time.sleep(1.0)
        res = api_fetch([c["url"]])
        if not res: continue
        p = res[0]
        content = clean(p.get("text") or p.get("content") or "")
        if len(content) < 150:          # boilerplate/JS shell — skip
            continue
        used.add(c["url"])
        pages.append({"url": c["url"], "title": p.get("title") or c["title"],
                      "domain": c["domain"], "authority": c["authority"],
                      "content": content[: a.max_chars]})
        progress(f"  fetched {len(pages)}: {c['domain']} ({len(content)} chars)")
    if not pages:
        progress("ERROR: no usable pages fetched. Agent: do the research with your "
                 "own web tools and write pages.json manually.")
        (out / "pages.json").write_text("[]")
        sys.exit(2)

    (out / "pages.json").write_text(json.dumps(pages, indent=1, ensure_ascii=False))
    doms = {}
    for p in pages: doms[p["domain"]] = doms.get(p["domain"], 0) + 1
    doms = dict(sorted(doms.items(), key=lambda kv: -kv[1]))
    progress(f"DONE: {len(pages)} pages from {len(doms)} domains: {doms}")
    # Coverage checklist — warn (never fail) on thin coverage.
    warn = []
    if sum(1 for p in pages if p["authority"] >= 3) < 3:
        warn.append("<3 official/authoritative sources")
    if len(doms) < 4:
        warn.append(f"<4 distinct domains ({doms})")
    if warn: progress("COVERAGE WARN: " + "; ".join(warn))

if __name__ == "__main__":
    main()
