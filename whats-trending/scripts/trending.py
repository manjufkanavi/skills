#!/usr/bin/env python3
"""Fetch trending topics from Google Trends (IN), Google News RSS (Global & Karnataka)."""

import json
import re
import sys
import argparse
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import unescape

API_KEY = "sk-tinyfish-vHbgNi2R-tVLAXFixslJ3lk5iz71dIsE"
TINYFISH_URL = "https://api.search.tinyfish.ai"

GOOGLE_TRENDS_IN = "https://trends.google.com/trending?geo=IN"
GOOGLE_TRENDS_GLOBAL = "https://trends.google.com/trending?geo=GLOBAL"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q=trending&hl=en-US&gl=US&ceid=US:en"
GOOGLE_NEWS_RSS_TOP = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
KARNATAKA_NEWS_RSS = "https://news.google.com/rss/search?q=karnataka+Bengaluru&hl=en-IN&gl=IN&ceid=IN:en"
INDIA_NEWS_RSS = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

# Minimum number of trends required per category before we consider it a success.
MIN_TRENDS = 10

# Fallback search queries (used when Google Trends / RSS return too few results).
# These are news-focused queries so the fallback returns real headlines, not junk.
INDIA_FALLBACK_QUERIES = [
    "India top news today",
    "India trending news July 2026",
    "India breaking news",
    "India business technology news",
    "India politics economy news",
    "India cricket sports news today",
    "India stock market news today",
    "India weather news today",
    "India government policy news today",
    "India education health news today",
    "India infrastructure development news",
    "India startup funding news today",
    "India election news today",
    "India crime news today",
    "India science space news today",
    "India entertainment bollywood news today",
]
GLOBAL_FALLBACK_QUERIES = [
    "world top news today",
    "global trending news",
    "world breaking news",
    "international news headlines",
    "world business technology news",
]

OUTPUT_FILES = {
    "india": "india_trends.json",
    "karnataka": "karnataka_trends.json",
    "karnataka_dork": "karnataka_dork_trends.json",
    "global": "world_trends.json",
}

LABELS = {
    "india": "India",
    "karnataka": "Karnataka",
    "karnataka_dork": "Karnataka (Google Dork)",
    "global": "Global",
}

# ---- Curated news-site lists for Google-dork Karnataka trending ----
# Top Karnataka news channel/paper websites
KARNATAKA_NEWS_SITES = [
    "deccanherald.com",
    "thehindu.com",
    "timesofindia.indiatimes.com",
    "newindianexpress.com",
    "indianexpress.com",
    "thehansindia.com",
    "bangaloremirror.com",
    "vijaykarnataka.com",
    "prajavani.net",
    "udayavani.com",
]

# Top India news channel/paper websites
INDIA_NEWS_SITES = [
    "ndtv.com",
    "timesofindia.indiatimes.com",
    "thehindu.com",
    "indianexpress.com",
    "hindustantimes.com",
    "news18.com",
    "theprint.in",
    "economictimes.indiatimes.com",
    "mint.com",
    "republicworld.com",
]

# Generic (non-site-scoped) dork queries targeting recent Karnataka news
KARNATAKA_DORK_QUERIES = [
    "karnataka news",
    "bengaluru news",
    "karnataka headlines",
    "bengaluru OR mysuru OR hubballi news",
    "karnataka government",
    "karnataka politics",
]

# City keywords to scope site: dorks toward Karnataka local news
KARNATAKA_CITY_KEYWORDS = ["karnataka", "bengaluru", "mysuru", "hubballi", "mangaluru"]


def _dork_after_date(days_back: int = 7) -> str:
    """Return an ISO date string `days_back` ago for Google's `after:` operator."""
    return (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")


def build_karnataka_dork_queries() -> list[str]:
    """Build the full set of Google-dork queries for Karnataka trending news.

    Combines:
      1. Generic `karnataka news after:<date>` queries (auto-computed 7-day window).
      2. `site:<domain> <city> after:<date>` dorks against the curated Karnataka
         and India news-site lists, so results are guaranteed news articles.
    """
    after = _dork_after_date(7)
    queries = [f"{q} after:{after}" for q in KARNATAKA_DORK_QUERIES]
    # Site-scoped dorks: each curated site × a couple of city keywords
    for domain in KARNATAKA_NEWS_SITES + INDIA_NEWS_SITES:
        for kw in KARNATAKA_CITY_KEYWORDS[:2]:  # karnataka + bengaluru
            queries.append(f"site:{domain} {kw} after:{after}")
    return queries

# News domains to prefer when filtering dork results
NEWS_DOMAINS = [
    "thehindu.com", "deccanherald.com", "timesofindia.indiatimes.com",
    "indianexpress.com", "newindianexpress.com", "thehansindia.com",
    "hindustantimes.com", "ndtv.com", "news18.com", "theprint.in",
    "economictimes.indiatimes.com", "moneycontrol.com", "mint.com",
    "bangaloremirror.com", "vijaykarnataka.com", "prajavani.net",
    "kannadaprabha.com", "udayavani.com", "tv9kannada.com",
    "asianetnews.com", "etvbharat.com", "zeenews.india.com", "oneindia.com",
    "daijiworld.com", "mangaloretoday.com", "coastalnews.in",
]


def fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch a URL and return the text content."""
    req = urllib.request.Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_via_jina(url: str) -> str:
    """Fetch a URL via Jina Reader API (renders JS-heavy pages)."""
    reader_url = f"https://r.jina.ai/{url}"
    req = urllib.request.Request(reader_url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ⚠ Jina Reader fetch failed: {e}", file=sys.stderr)
        return ""


def parse_google_trends(html: str) -> list[dict]:
    """Parse trending topics from Google Trends page HTML/text."""
    trends = []
    seen = set()

    # Pattern 1: Jina/markdown table format
    row_pattern = re.compile(
        r'\|\s*\[x\]\s*\|\s*(.+?)\s+(\d+[KMB+]?\s*searches)\s*·',
        re.IGNORECASE
    )
    for m in row_pattern.finditer(html):
        raw_title = m.group(1).strip()
        search_vol = m.group(2).strip()
        title = re.sub(r'\s+', ' ', raw_title).strip()
        title = re.sub(r'\s*_trending\w*$', '', title)
        vol_num = search_vol.split()[0] if search_vol else ""

        key = title.lower().strip()
        if key and key not in seen and len(title) > 2:
            seen.add(key)
            trends.append({
                "rank": len(trends) + 1,
                "title": title,
                "search_volume": vol_num,
                "source": "Google Trends",
                "url": f"https://trends.google.com/trends/explore?q={urllib.parse.quote(title)}&date=now+1-d&hl=en-US",
            })
            if len(trends) >= 10:
                break

    # Pattern 2: Fallback - plain text lines with search volume
    if len(trends) < 10:
        line_pattern = re.compile(
            r'([A-Z][A-Za-z0-9\s\-\.]+?)\s+(\d+[KMB]?\+?)\s*searches',
            re.IGNORECASE
        )
        for m in line_pattern.finditer(html):
            title = m.group(1).strip()
            search_vol = m.group(2).strip()
            key = title.lower().strip()
            if key and key not in seen and len(title) > 3:
                seen.add(key)
                trends.append({
                    "rank": len(trends) + 1,
                    "title": title,
                    "search_volume": f"{search_vol}+ searches",
                    "source": "Google Trends",
                    "url": f"https://trends.google.com/trends/explore?q={urllib.parse.quote(title)}&date=now+1-d&hl=en-US",
                })
                if len(trends) >= 10:
                    break

    return trends[:10]


def fetch_google_trends() -> list[dict]:
    """Fetch trending topics from Google Trends IN page, topped up to 10."""
    print(f"  Fetching Google Trends (geo=IN)...", file=sys.stderr)

    trends = []
    # Try direct fetch first
    try:
        html = fetch_url(GOOGLE_TRENDS_IN, timeout=20)
        trends = parse_google_trends(html)
    except Exception as e:
        print(f"  ⚠ Direct fetch failed: {e}", file=sys.stderr)

    # Fallback: use Jina Reader API
    if len(trends) < 5:
        print(f"  Trying Jina Reader fallback...", file=sys.stderr)
        html = fetch_via_jina(GOOGLE_TRENDS_IN)
        if html:
            trends = parse_google_trends(html)

    # Top up to 10 via TinyFish news search
    return top_up_to_ten(trends, INDIA_FALLBACK_QUERIES, "India")


def parse_google_news_rss(xml_text: str) -> list[dict]:
    """Parse Google News RSS feed and return top 10 articles."""
    root = ET.fromstring(xml_text)
    trends = []
    seen = set()

    for item in root.iter("item"):
        title_el = item.find("title")
        source_el = item.find("source")
        pubdate_el = item.find("pubDate")
        link_el = item.find("link")

        title = unescape(title_el.text.strip()) if title_el is not None and title_el.text else ""
        source = unescape(source_el.text.strip()) if source_el is not None and source_el.text else ""
        pubdate = pubdate_el.text.strip() if pubdate_el is not None and pubdate_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else ""

        # Clean up title - remove trailing source attribution
        title = re.sub(r'\s*-\s*' + re.escape(source) + r'\s*$', '', title).strip()

        key = title.lower().strip()
        if title and key not in seen:
            seen.add(key)
            trends.append({
                "rank": len(trends) + 1,
                "title": title,
                "snippet": f"{source} · {pubdate}",
                "source": source,
                "url": link,
                "pubdate": pubdate,
            })
            if len(trends) >= 10:
                break

    return trends


def fetch_google_news_rss(url: str) -> list[dict]:
    """Fetch trending stories from a Google News RSS feed."""
    print(f"  Fetching Google News RSS...", file=sys.stderr)
    try:
        xml_text = fetch_url(url, timeout=20)
        return parse_google_news_rss(xml_text)
    except Exception as e:
        print(f"  ⚠ RSS fetch/parse failed: {e}", file=sys.stderr)
        return []


def fetch_global_trends() -> list[dict]:
    """Fetch global trending topics, topped up to 10.

    Tries Google Trends GLOBAL first, then Google News RSS top stories,
    then TinyFish news search fallback.
    """
    print(f"  Fetching Google Trends (geo=GLOBAL)...", file=sys.stderr)
    trends = []
    try:
        html = fetch_url(GOOGLE_TRENDS_GLOBAL, timeout=20)
        trends = parse_google_trends(html)
    except Exception as e:
        print(f"  ⚠ Global Trends direct fetch failed: {e}", file=sys.stderr)

    if len(trends) < MIN_TRENDS:
        print(f"  Fetching Google News RSS (global top stories)...", file=sys.stderr)
        rss_trends = fetch_google_news_rss(GOOGLE_NEWS_RSS_TOP)
        seen = {_normalize_title(t.get("title", "")) for t in trends}
        for t in rss_trends:
            if len(trends) >= MIN_TRENDS:
                break
            key = _normalize_title(t.get("title", ""))
            if key in seen:
                continue
            seen.add(key)
            t["rank"] = len(trends) + 1
            trends.append(t)

    return top_up_to_ten(trends, GLOBAL_FALLBACK_QUERIES, "Global")


def fetch_karnataka_trends() -> list[dict]:
    """Fetch Karnataka trending news via Google News RSS, topped up to 10."""
    print(f"  Fetching Google News RSS for Karnataka...", file=sys.stderr)
    trends = []
    try:
        xml_text = fetch_url(KARNATAKA_NEWS_RSS, timeout=20)
        trends = parse_google_news_rss(xml_text)
    except Exception as e:
        print(f"  ⚠ Karnataka RSS fetch/parse failed: {e}", file=sys.stderr)

    # Top up to 10 via TinyFish news search
    return top_up_to_ten(trends, INDIA_FALLBACK_QUERIES, "Karnataka")


def tinyfish_search(query: str, timeout: int = 20) -> list[dict]:
    """Search via TinyFish API and return raw results."""
    search_url = f"{TINYFISH_URL}?query={urllib.parse.quote(query)}"
    req = urllib.request.Request(search_url, headers={"X-API-Key": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return data.get("results", [])
    except Exception as e:
        print(f"  ⚠ TinyFish search failed for '{query}': {e}", file=sys.stderr)
        return []


def _looks_like_landing_page(title: str) -> bool:
    """Return True if a title looks like a homepage/section landing page, not a headline."""
    t = title.strip().lower()
    # Bare site names / generic "Latest News" style titles
    landing = [
        "google news", "the times of india", "times of india", "indian express",
        "india today", "hindustan times", "the hindu", "ndtv", "bbc", "cnn",
        "reuters", "the print", "news18", "mint", "economic times",
        "deccan herald", "new indian express", "republic world",
    ]
    if t in landing:
        return True
    # Titles that START with a site name followed by a colon/dash (e.g.
    # "The Times of India: TOI - Breaking News...", "India Today: Latest News...")
    for site in landing:
        if t.startswith(site + ":") or t.startswith(site + " -"):
            return True
    # Generic section titles
    if re.match(r'^(latest news|breaking news|india news|world news|top stories|headlines)', t):
        return True
    if t.endswith("latest news") or t.endswith("breaking news"):
        return True
    # "Top news of the day", "Today's Top News", "Today's Morning Top News Headlines",
    # "LIVE: Today Headlines", "Top 5 ... News" — generic roundups, not specific stories
    if re.match(r'^(top news|today.?s (top|morning|evening) news|live:? today|top \d+ )', t):
        return True
    # "2026 in India", "July - The Economic Times" — calendar/section pages
    if re.match(r'^\d{4} in ', t):
        return True
    if re.match(r'^(january|february|march|april|may|june|july|august|september|october|november|december) - ', t):
        return True
    # Section landing pages: "International News, Latest News Today, World News Headlines",
    # "Technology News Today, Latest Tech News", "AI, Startups, IT Industry & Cybersecurity Updates"
    if re.search(r'(news today|news headlines|news updates|latest news|breaking news|tech news|technology news)', t):
        return True
    # "US News", "Indian economy", "Tech | CNN Business", "Economy news, Latest Economic News, GDP, World..."
    # — bare section names / landing pages
    if re.match(r'^(us news|world news|india news|international news|business news|economy news|tech news|technology news|sports news|entertainment news|science news|health news)$', t):
        return True
    if re.match(r'^(us|world|india|international|business|economy|tech|technology|sports|entertainment|science|health) \| ', t):
        return True
    if re.match(r'^(us|world|india|international|business|economy|tech|technology|sports|entertainment|science|health) news', t):
        return True
    # "Indian economy", "US economy", "China economy" — bare topic landing pages
    if re.match(r'^(indian|us|china|global|world) economy$', t):
        return True
    # "TechCircle: India's leading Tech business information website." — site tagline
    if re.search(r'(leading .* website|official website|homepage|home page)', t):
        return True
    # "Live Cricket Scores, Cricket News, Analysis, Results & More", "Cricinfo | Live Cricket Scores...",
    # "India Cricket Team Scores, Matches, Schedule, News, Players", "Stock Market Live News Update"
    # — generic live-score / section landing pages
    if re.match(r'^(live cricket scores|live scores|cricket scores|india cricket team scores|stock market live)', t):
        return True
    if re.search(r'(live cricket scores|cricket news, analysis|scores, matches, schedule|scores, ipl scores)', t):
        return True
    # "AI, Startups, IT Industry & Cybersecurity Updates | ET Tech" — section landing page
    if re.search(r'(updates \| | \| .* updates$)', t):
        return True
    # "Recent Economic News, Latest Indian Economy News" — generic roundup
    if re.match(r'^(recent|latest|top|today) (economic|economy|business|tech|technology|sports|entertainment|science|health) news', t):
        return True
    # Stock market / share market live pages — not news stories
    if re.search(r'(share market|stock market|live indices|gainers|losers|nse|bse|sensex|nifty)', t):
        return True
    # Weather pages / weather department homepages
    if re.search(r'(weather|मौसम|meteorological department)', t):
        return True
    # YouTube videos / video platforms — not news headlines
    if re.search(r'(youtube|video|film)', t):
        return True
    # "Pulse by Zerodha - Latest financial and market news from all major..." — aggregator landing
    if re.search(r'(latest financial and market news|news from all major)', t):
        return True
    return False


def top_up_to_ten(trends: list[dict], queries: list[str], label: str) -> list[dict]:
    """Top up a trends list to at least MIN_TRENDS using TinyFish search fallback.

    Runs each fallback query, filters to news domains, dedupes by normalized title,
    and appends until we reach MIN_TRENDS. Returns the (possibly extended) list.
    """
    if len(trends) >= MIN_TRENDS:
        return trends
    print(f"  ⚠ Only {len(trends)} {label} trends — topping up via TinyFish search...", file=sys.stderr)
    seen_titles = {_normalize_title(t.get("title", "")) for t in trends}
    for query in queries:
        if len(trends) >= MIN_TRENDS:
            break
        for r in tinyfish_search(query):
            if len(trends) >= MIN_TRENDS:
                break
            title = (r.get("title") or "").strip()
            if not title:
                continue
            # Skip homepage / section landing pages (e.g. "The Times of India",
            # "Google News", "India Today") — these are not real headlines.
            if _looks_like_landing_page(title):
                continue
            key = _normalize_title(title)
            if key in seen_titles:
                continue
            seen_titles.add(key)
            trends.append({
                "rank": len(trends) + 1,
                "title": title,
                "snippet": (r.get("snippet") or "").strip(),
                "source": (r.get("site_name") or "").strip(),
                "url": r.get("url", ""),
                "date": r.get("date", ""),
            })
    return trends[:MIN_TRENDS]


def _is_news_result(r: dict) -> bool:
    """Return True if a TinyFish result looks like a news article."""
    url = (r.get("url") or "").lower()
    title = (r.get("title") or "").lower()
    # Must be from a known news domain
    if not any(d in url for d in NEWS_DOMAINS):
        return False
    # Skip obvious non-news pages
    if any(x in url for x in ["/video", "/photos", "/gallery", "/live"]):
        return False
    # Skip section/tag/landing pages (not individual articles)
    if any(x in url for x in ["/tags/", "/news/bengaluru-news", "/cities/bengaluru",
                               "/news/national/karnataka", "/news/", "/karnataka/",
                               "/karnataka-news", "/education/", "/top-",
                               "/about/", "/states/karnataka"]):
        return False
    # Skip homepage / section landing pages
    if url.rstrip("/") in ["https://www.deccanherald.com", "https://www.thehindu.com"]:
        return False
    # Skip generic section titles that aren't real headlines
    generic = ["news", "latest", "breaking news", "updates", "headlines",
               "karnataka", "top engineering colleges", "education"]
    if title in generic or title.endswith(" news") or title.endswith(" updates"):
        return False
    return True


def _is_recent(r: dict, max_age_days: int = 7) -> bool:
    """Return True if the result has a date within max_age_days."""
    date_str = (r.get("date") or "").strip()
    if not date_str:
        return True  # no date → keep (can't verify)
    low = date_str.lower()
    # Relative dates like '2 days ago', '4 hours ago', '20 hours ago' → recent
    if re.search(r'(hour|day)s? ago', low):
        return True
    try:
        # Absolute dates: '2026-07-28', ISO, 'Apr 29, 2021', 'Jul 18, 2026'
        d = None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z",
                    "%b %d, %Y", "%B %d, %Y"):
            try:
                d = datetime.strptime(date_str[:20], fmt)
                break
            except ValueError:
                continue
        if d is None:
            return True  # unparseable date → keep
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - d
        return age <= timedelta(days=max_age_days)
    except Exception:
        return True  # unparseable date → keep


def _normalize_title(title: str) -> str:
    """Normalize a title for dedup: lowercase, strip punctuation/whitespace."""
    t = title.lower().strip()
    t = re.sub(r'[^a-z0-9\u0c80-\u0cff ]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def fetch_karnataka_dork_trends() -> list[dict]:
    """Fetch Karnataka trending news via Google dork queries through TinyFish.

    Strategy:
      1. Run several Google-dork-style queries (news + after:date) via TinyFish.
      2. Filter results to news domains only.
      3. Filter to articles <1 week old (by date field when present).
      4. Deduplicate by normalized title.
      5. Return top 10.
    """
    print(f"  Fetching Karnataka via Google dork + TinyFish...", file=sys.stderr)

    all_results = []
    seen_urls = set()

    queries = build_karnataka_dork_queries()
    print(f"  Running {len(queries)} dork queries...", file=sys.stderr)

    for query in queries:
        results = tinyfish_search(query)
        for r in results:
            url = r.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            all_results.append(r)

    print(f"  Got {len(all_results)} raw results from dork queries", file=sys.stderr)

    # Filter: news domains + recent (<1 week)
    news_results = [r for r in all_results if _is_news_result(r) and _is_recent(r)]
    print(f"  {len(news_results)} are news articles <1 week old", file=sys.stderr)

    # Deduplicate by normalized title
    trends = []
    seen_titles = set()
    for r in news_results:
        title = (r.get("title") or "").strip()
        if not title:
            continue
        key = _normalize_title(title)
        if key in seen_titles:
            continue
        seen_titles.add(key)
        trends.append({
            "rank": len(trends) + 1,
            "title": title,
            "snippet": (r.get("snippet") or "").strip(),
            "source": (r.get("site_name") or "").strip(),
            "url": r.get("url", ""),
            "date": r.get("date", ""),
        })
        if len(trends) >= 10:
            break

    return trends[:10]


def save_trends(category: str, trends: list[dict], output_dir: Path):
    """Save trends to a JSON file."""
    output = {
        "category": category,
        "label": LABELS.get(category, category),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_results": len(trends),
        "trends": trends,
    }
    filename = OUTPUT_FILES.get(category, f"{category}_trends.json")
    path = output_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"  ✅ {filename} ({len(trends)} trends)")
    return path


def main():
    parser = argparse.ArgumentParser(description="Fetch trending topics")
    parser.add_argument(
        "--output", "-o",
        default="./trending_output",
        help="Output directory for JSON files",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🔍 Fetching trending topics...\n")

    # 1. India — Google Trends IN
    print("  [India] Google Trends IN...")
    india_trends = fetch_google_trends()
    save_trends("india", india_trends, output_dir)

    # 2. Karnataka — Google News RSS (Karnataka keyword)
    print("  [Karnataka] Google News RSS...")
    ka_trends = fetch_karnataka_trends()
    save_trends("karnataka", ka_trends, output_dir)

    # 2b. Karnataka — Google dork + TinyFish (news <1 week old, deduped)
    print("  [Karnataka Dork] Google dork + TinyFish...")
    ka_dork_trends = fetch_karnataka_dork_trends()
    save_trends("karnataka_dork", ka_dork_trends, output_dir)

    # 3. Global — Google Trends GLOBAL + Google News RSS + TinyFish top-up
    print("  [Global] Google Trends + News RSS...")
    global_trends = fetch_global_trends()
    save_trends("global", global_trends, output_dir)

    print(f"\n📁 All files saved in: {output_dir.resolve()}")
    for filename in OUTPUT_FILES.values():
        p = output_dir / filename
        if p.exists():
            print(f"   • {p}")


if __name__ == "__main__":
    main()
