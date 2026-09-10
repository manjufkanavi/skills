#!/usr/bin/env python3
"""Synthesis runner for QA improvement + leadership deep research.

Re-fetches content (via Tiny-Fish) for pages flagged preview_len>100 in
research_data.json, synthesizes a markdown report AND renders an HTML slideshow
from the heritage-essay template.

Keyword matching is broad and covers both titles AND fetched content so that
the full set of 104 sources is distributed across all seven themes.

Progress is flushed so it never runs silently in the background.
"""
import os, re, json, time, urllib.request, html as htmllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TINYFISH_API_KEY = os.environ.get("TINYFISH_API_KEY")
FETCH_URL = "https://api.fetch.tinyfish.ai"

HERE = Path(__file__).resolve().parent.parent  # skill root (has research_data.json)
RESEARCH_DATA = HERE / "research_data.json"
TEMPLATE_CANDIDATES = [
    Path("/Users/manjunathkanavi/.hermes/skills/research/deep-research/html_templates/03-heritage-essay.html"),
    HERE / "html_templates" / "03-heritage-essay.html",
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
    topic_label = "How to Become a Better QA Engineer and Lead a Team"
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

    # ---- Theme grouping by broad keyword scan over title + content ----
    themes = {}
    def add(key, title, content):
        themes.setdefault(key, []).append((title, content))

    for title, content in collected:
        blob = (title + " " + content).lower()

        # --- LEADERSHIP & TEAM BUILDING (check first: broadest set) ---
        if any(k in blob for k in [
            "qa lead", "quality assurance leader", "effective qa leadership",
            "transitioning from qa to engineering manager", "qa manager",
            "building a qa team", "build and manage a qa testing team",
            "crafting a quality assurance team", "successful qa team",
            "building a testing team", "qa team of tomorrow", "software testing team",
            "future-ready qa team", "building a qa team steps best practices",
            "qa manager's essential guide to test management", "i am a qa manager",
            "stakeholder management for engineering leads",
            "earn trust autonomy and resources", "skills required for qa lead",
            "qa team roles and responsibilities", "engineering leads stakeholder management",
        ]):
            add("leadership", title, content)
            continue

        # --- AI-ASSISTED TESTING (AI testing tools / LLM frameworks) ---
        if any(k in blob for k in [
            "ai testing tool", "ai test automation", "ai-powered quality",
            "top 16 ai tools for software testing", "free ai tools for software testers",
            "awesome-ai-testing", "llm testing framework", "15 best ai testing tools",
            "the 12 best ai testing tools", "ai qa testing tools/services are you actually using",
        ]):
            add("ai_testing", title, content)
            continue

        # --- METRICS (DORA, test coverage, defect leakage, effectiveness) ---
        if any(k in blob for k in [
            "qa metrics", "software testing metrics", "testing metrics in agile",
            "test effectiveness metrics", "dora software delivery performance",
            "defect leakage", "quality engineering effectiveness kpi",
        ]):
            add("metrics", title, content)
            continue

        # --- CAREERS: salary / roadmap / career ladder / skills for QA ---
        if any(k in blob for k in [
            "career ladder", "staff principal engineer roles", "engineering career paths",
            "what is a qa engineer career insights", "career growth what paths after senior",
            "quality assurance salary negotiation", "qa engineer salary ranges",
            "lead qa engineer average salary pay trends", "how to negotiate a quality assurance salary",
            "here's how you can determine salary ranges", "$100k+ as a qa engineer salary negotiation tips",
            "essential skills for qa professionals in 2025", "full-stack qa roadmap",
            "how to become a qa automation engineer in 2025 the ultimate step-by-step roadmap",
            "how to become a qa engineer: a complete roadmap",
        ]):
            add("careers", title, content)
            continue

        # --- TEST DESIGN (BVA / EP / state transition / exploratory) ---
        if any(k in blob for k in [
            "test design techniques", "equivalence partitioning and boundary value analysis",
            "comprehensive guide to equivalence partitioning testing",
            "what is boundary value analysis in software testing?",
            "boundary value analysis vs equivalence class partitioning",
            "bva & ep testing key methods of black box testing",
        ]):
            add("test_design", title, content)
            continue

        # --- AUTOMATION (frameworks / platforms / CI-CD integration) ---
        if any(k in blob for k in [
            "test automation", "selenium playwright testify", "continuous validation platform",
            "cloud automation testing tools", "software testing & qa services company",
        ]):
            add("automation", title, content)
            continue

        # --- SHIFT-LEFT (dedicated theme since it's a major cluster) ---
        if any(k in blob for k in [
            "shift left testing", "shift-left software testing", "what is shift left",
            "shift left on performance testing", "total shift left",
        ]):
            add("shift_left", title, content)
            continue

        # --- OVERALL QA / MODERN QUALITY ENGINEERING (fallback bucket) ---
        add("overview", title, content)

    headings = {
        "overview": ("I", "The Modern QA Landscape: From Gatekeeper to Quality Engineer"),
        "careers": ("II", "Career Roadmap: Skills, Tools & Compensation"),
        "test_design": ("III", "Test Design Fundamentals That Separate Good from Great QA"),
        "automation": ("IV", "Automation Strategy: Selenium, Playwright & CI/CD"),
        "shift_left": ("V", "Shift-Left Testing: Catching Bugs Before They Ship"),
        "ai_testing": ("VI", "AI-Assisted Testing: The 2025 Opportunity Wave"),
        "metrics": ("VII", "Measuring What Matters: Metrics That Prove QA's Value"),
        "leadership": ("VIII", "Leading a QA Team: From Engineer to Manager"),
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
                  lambda m: f'{m.group(1)}{htmllib.escape("A synthesized research report for aspiring QA engineers and emerging team leads, drawn from " + str(len(collected)) + " sources.")}{m.group(2)}',
                  html, count=1, flags=re.DOTALL)

    # Replace the entire article body (between ARTICLE marker and </article>)
    new_article = f'<!-- ARTICLE -->\n<article class="page article">\n\n{article_body}'
    new_article += (f'\n  <div class="references">\n'
                    f'    <h2>References</h2>\n'
                    f'    <ol class="ref-list">\n{ref_items}'
                    f'    </ol>\n  </div>\n\n</article>')
    html = re.sub(r'<!-- ARTICLE -->.*?</article>', new_article, html, flags=re.DOTALL)

    # Update footer date
    html = re.sub(r'Deep Research Report.*?2025', 'Deep Research Report &nbsp;·&nbsp;' + time.strftime('%B %Y'), html)

    # ---- Write outputs ----
    ts = int(time.time())
    out_dir = HERE / "reports" / f"{topic_slug}-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Markdown report (human-readable companion)
    md = [f"# {topic_label}\n", f"> Research date: {time.strftime('%Y-%m-%d')}",
          "", "## Executive Summary\n",
          f"This report synthesizes findings from **{len(collected)} curated sources** "
          f"scraped across 13 targeted queries covering QA skill roadmaps, test design "
          f"techniques (BVA / equivalence partitioning), automation frameworks "
          f"(Selenium/Playwright/testRigor), shift-left strategy, AI-assisted testing "
          f"in 2025, value-proving metrics (DORA, defect leakage), and the transition "
          f"from individual contributor to QA team lead. It is written for a practitioner "
          f"who wants to deepen technical QA craft *and* step into leadership.\n"]

    # Per-theme summary lines
    theme_summaries = {
        "overview": ("The Modern QA Landscape", "QA is shifting from reactive gatekeeping to proactive quality engineering — engineers now own test strategy, mentor teams, and embed quality into the SDLC via shift-left."),
        "careers": ("Career Roadmap", "The 2025–2026 market rewards full-stack QA engineers: test automation + API/database knowledge, strong CI/CD fluency, and the ability to negotiate $100k+ comp. Career ladders run from QA Analyst → Engineer → Staff/Principal or into QA Leadership."),
        "test_design": ("Test Design Fundamentals", "Equivalence partitioning, boundary value analysis, state-transition testing, and exploratory testing remain the backbone — automation without good test design just automates bad tests."),
        "automation": ("Automation Strategy", "Pick one framework to depth (Playwright for greenfield, Selenium for legacy), integrate it into CI/CD pipelines, and use cloud testing platforms (Sauce Labs, CloudQA) for cross-device coverage."),
        "shift_left": ("Shift-Left Testing", "Testing early in the SDLC — via test-driven development, contract testing, and CI integration — cuts defect-fix cost by orders of magnitude. A cited case study showed a $700K savings from a shift-left rollout."),
        "ai_testing": ("AI-Assisted Testing", "2025–2026 saw an explosion of AI testing tools: auto-generating test cases, self-healing locators, visual regression with computer vision, and LLM-based test-validation. QA pros who direct these tools become leverage multipliers."),
        "metrics": ("Measuring What Matters", "DORA metrics, defect leakage/escape rate, test coverage %, and time-to-fix tell a story stakeholders understand. Track them so QA speaks the language of business value."),
        "leadership": ("Leading a QA Team", "Great QA leaders transition from 'I test things' to building testing teams, defining quality processes, mentoring engineers, and managing stakeholders across product and engineering."),
    }

    for key, items in ordered:
        _, heading = headings[key]
        summary_text = theme_summaries.get(key, ("", ""))[1]
        if summary_text:
            md.append(f"\n## {heading}\n")
            md.append(summary_text + "\n\n")
        for t, c in items[:6]:
            sents = re.split(r'(?<=[.!?])\s+', c)
            snippet = " ".join(x.strip() for x in sents if 60 < len(x) < 300)[:400]
            md.append(f"- **{t[:95]}** — {snippet}\n")

    md.append("\n## Recommended Next Steps\n")
    md.append("- **Sharpen test design first.** Master equivalence partitioning, boundary "
              "value analysis, and exploratory testing — these are the foundations every "
              "automation tool builds on.\n")
    md.append("- **Build one automation skill to depth.** Pick Playwright (or Selenium if "
              "legacy) and ship a real regression suite integrated into CI/CD.\n")
    md.append("- **Measure what you do.** Track defect leakage, escape rate, and test "
              "coverage so you can speak the language of business value to stakeholders.\n")
    md.append("- **Watch AI-assisted testing closely.** In 2025, QA pros who can direct "
              "LLMs to generate/validate tests become leverage multipliers — start with one tool.\n")
    md.append("- **Practice leadership deliberately.** Lead by writing test strategy docs, "
              "mentoring juniors, and owning cross-team quality conversations before you hold the title.\n")
    md.append("- **Own shift-left.** Move testing left in your SDLC — it is the single "
              "highest-leverage thing a senior QA person can change organizationally.\n")

    md_path = out_dir / f"{topic_slug}.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    progress(f"Wrote markdown report: {md_path} ({len(chr(10).join(md))} chars)")

    html_path = out_dir / f"{topic_slug}.html"
    html_path.write_text(html, encoding="utf-8")
    progress(f"Wrote HTML slideshow: {html_path} ({len(html)} chars)")

if __name__ == "__main__":
    main()
