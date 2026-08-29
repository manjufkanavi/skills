#!/usr/bin/env python3
"""Synthesis runner for curated deep research.

Re-fetches content (via Tiny-Fish) only for pages flagged preview_len>100 in
research_data.json, synthesizes a markdown report AND renders an HTML slideshow
from the heritage-essay template (structural replacement of masthead + article body).

Progress is flushed so it never runs silently in the background.
"""
import os, re, json, time, urllib.request, html as htmllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TINYFISH_API_KEY = os.environ.get("TINYFISH_API_KEY")
FETCH_URL = "https://api.fetch.tinyfish.ai"

HERE = Path(__file__).resolve().parent
RESEARCH_DATA = HERE.parent / "research_data.json"
# Prefer the git-tracked template; fall back to ~/.hermes/skills copy.
TEMPLATE_CANDIDATES = [
    Path("/Users/manjunathkanavi/.hermes/skills/research/deep-research/html_templates/03-heritage-essay.html"),
    HERE.parent / "html_templates" / "03-heritage-essay.html",
]

def progress(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def fetch(url):
    if not TINYFISH_API_KEY:
        return "", ""
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
        progress(f"  ✗ fetch failed {url[:50]}...: {e}")
        return "", ""

def clean(text):
    t = re.sub(r'<[^>]+>', '', text)
    for pat in [r'\d+\s*views\s*(ago|•)', r'\d+\s*subscribers',
                r'• Follow ---', r'Sign up Log in', r'\d+\s*min read']:
        t = re.sub(pat, '', t)
    return re.sub(r'\s+', ' ', t).strip()

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

def main():
    data = json.loads(RESEARCH_DATA.read_text())
    topic_label = "Lucrative AI Use Cases for a Self-Hosted Stack"
    topic_slug = slugify(topic_label)

    urls = [s["url"] for s in data["sources"] if s.get("preview_len", 0) > 100]
    progress(f"Re-fetching content for {len(urls)} qualifying pages")

    collected = []  # (title, clean_content)
    for i in range(0, len(urls), 10):
        batch = urls[i:i+10]
        with ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(fetch, batch))
        for url, (content, title) in zip(batch, results):
            c = clean(content)
            if len(c) > 150:
                collected.append((title[:200] or url, c))
        progress(f"  fetched {min(i+10, len(urls))}/{len(urls)} (articles: {len(collected)})")

    if not collected:
        progress("No usable content fetched. Aborting.")
        return

    # ---- Theme grouping by keyword scan ----
    themes = {}
    def add(key, title, content):
        themes.setdefault(key, []).append((title, content))

    for title, content in collected:
        blob = (title + " " + content).lower()
        if any(k in blob for k in ["voice agent", "transcrip", "ocr", "document imag",
                                     "speech to text", "invoice", "receipt"]):
            add("voice_ocr", title, content)
        elif any(k in blob for k in ["local llm", "self-hosted", "privacy-first",
                                       "on-device", "offline"]):
            add("local_llm", title, content)
        elif any(k in blob for k in ["compliance", "soc2", "gdpr", "vulnerab",
                                       "security scan"]):
            add("compliance_security", title, content)
        elif any(k in blob for k in ["n8n", "workflow automation agency",
                                       "automation resell"]):
            add("automation_agency", title, content)
        elif any(k in blob for k in ["developer tool", "dev workflow"]):
            add("dev_tools", title, content)
        elif any(k in blob for k in ["micro saas", "saas idea", "niche"]):
            add("saas_niches", title, content)
        else:
            add("overview", title, content)

    headings = {
        "overview": ("I", "Market Signals & Opportunity Landscape"),
        "voice_ocr": ("II", "Voice + OCR Document Automation"),
        "local_llm": ("III", "Privacy-First & Self-Hosted AI Products"),
        "saas_niches": ("IV", "Profitable Micro-SaaS Niches 2026"),
        "automation_agency": ("V", "n8n Workflow-Automation Agency Model"),
        "compliance_security": ("VI", "Compliance & Vulnerability-Reporting SaaS"),
        "dev_tools": ("VII", "Developer-Tooling Opportunities"),
    }

    # ---- Build article sections for HTML (ordered, only non-empty) ----
    ordered = [(k, themes[k]) for k in headings if themes.get(k)]

    article_parts = []
    ref_items = ""
    for idx, (key, items) in enumerate(ordered, 1):
        num, heading = headings[key]
        bullets = "".join(
            f"<li>{htmllib.escape(t[:85])}<br><small>{htmllib.escape(c[:130])}…</small></li>"
            for t, c in items[:5]
        )
        article_parts.append(
            f'  <section class="article-section">\n'
            f'    <span class="section-number">{num}</span>\n'
            f'    <h2>{htmllib.escape(heading)}</h2>\n'
            f'    <ul style="margin-left:1.25rem;line-height:1.9;">{bullets}</ul>\n'
            f'  </section>\n\n'
            f'  <div class="separator"></div>\n\n'
        )
        # references: pull titles with their URLs for the top items per theme
        for t, c in items[:3]:
            ref_items += f'      <li>{htmllib.escape(t[:70])}</li>\n'

    article_body = "\n".join(article_parts)
    if not ref_items:  # fallback refs from all collected titles
        for t, c in collected[:30]:
            ref_items += f'      <li>{htmllib.escape(t[:70])}</li>\n'

    # ---- Load template & do structural replacement ----
    tmpl_path = next((p for p in TEMPLATE_CANDIDATES if p.exists()), None)
    if not tmpl_path:
        progress("Template not found; skipping HTML render.")
        return

    html = tmpl_path.read_text(encoding="utf-8")

    # Replace masthead title
    html = re.sub(r'<h1>.*?</h1>', f'<h1>{htmllib.escape(topic_label)}</h1>', html, flags=re.DOTALL)
    # Replace masthead subtitle
    html = re.sub(r'(<p class="masthead-sub">).*?(</p>)',
                  lambda m: f'{m.group(1)}{htmllib.escape("A synthesized opportunity map for a Linux (32 GB) + Mac Studio local-LLM stack, drawn from " + str(len(collected)) + " sources.")}{m.group(2)}',
                  html, count=1, flags=re.DOTALL)

    # Replace the entire article body (between ARTICLE marker and </article>)
    new_article = f'<!-- ARTICLE -->\n<article class="page article">\n\n{article_body}'
    new_article += (f'\n  <div class="references">\n'
                    f'    <h2>References</h2>\n'
                    f'    <ol class="ref-list">\n{ref_items}'
                    f'    </ol>\n  </div>\n\n</article>')
    html = re.sub(r'<!-- ARTICLE -->.*?</article>', new_article, html, flags=re.DOTALL)

    # Update footer date
    html = re.sub(r'Deep Research Report.*?2026', 'Deep Research Report &nbsp;·&nbsp;' + time.strftime('%B %Y'), html)

    # ---- Write outputs ----
    ts = int(time.time())
    out_dir = HERE / "reports" / f"{topic_slug}-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Markdown report (human-readable companion)
    md = [f"# {topic_label}\n", f"> Research date: {time.strftime('%Y-%m-%d')}",
          "", "## Executive Summary\n",
          f"This report synthesizes findings from **{len(collected)} curated sources** "
          f"scraped across 13 targeted queries covering profitable AI micro-SaaS niches, "
          f"privacy-first/self-hosted AI products, local-LLM cost economics, voice/OCR document "
          f"automation, n8n-based agency models, compliance automation, and developer-tooling "
          f"opportunities — evaluated against a Linux (32 GB RAM) + Mac Studio (~30B local LLM) "
          f"+ domain stack.\n"]
    for key, items in ordered:
        _, heading = headings[key]
        md.append(f"\n## {heading}\n")
        for t, c in items[:6]:
            sents = re.split(r'(?<=[.!?])\s+', c)
            snippet = " ".join(x.strip() for x in sents if 60 < len(x) < 280)[:300]
            md.append(f"- **{t[:90]}** — {snippet}\n")
    md.append("\n## Recommended Next Steps\n")
    md.append("- Prioritize niches where your 10yr SWE experience is a moat (dev-tooling, "
              "compliance automation).\n")
    md.append("- Use the Mac Studio's 30B local LLM for **privacy-first / on-device** products "
              "that cannot send data to third-party APIs.\n")
    md.append("- Use the Linux box + n8n as a **resellable automation backbone** sold per-client "
              "(retainer, not one-off).\n")
    md.append("- Validate demand before building (IdeaProof / micro-SaaS validator approach).\n")

    md_path = out_dir / f"{topic_slug}.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    progress(f"Wrote markdown report: {md_path} ({len(chr(10).join(md))} chars)")

    html_path = out_dir / f"{topic_slug}.html"
    html_path.write_text(html, encoding="utf-8")
    progress(f"Wrote HTML slideshow: {html_path} ({len(html)} chars)")

if __name__ == "__main__":
    main()
