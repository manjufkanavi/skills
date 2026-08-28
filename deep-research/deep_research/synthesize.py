"""
Report synthesis engine for deep-research skill.

Architecture:
  1. _cluster_sources — group sources by semantic theme
  2. _build_report   — LLM-driven synthesis via structured prompt template
  3. _build_slideshow — generate HTML presentation from same themes

The report prompt uses proven techniques:
  - Chain-of-thought reasoning (step-by-step analysis)
  - Few-shot structure guidance
  - Explicit output format constraints
  - Source-aware synthesis with inline citations
  - Length budget enforcement
"""

import re
import json
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict


# ── Constants ────────────────────────────────────────────────────────────────

MAX_REPORT_LENGTH = 8000
MAX_REFERENCES = 30
TOP_SOURCES_PER_THEME = 5
MIN_SENTENCE_LENGTH = 40
MAX_SENTENCE_LENGTH = 350


# ── Theme extraction ────────────────────────────────────────────────────────

THEME_MAP = {
    "definition": [
        "defin", "concept", "what is", "introduc", "overview", "fundamental",
        "core idea", "principle", "paradigm", "framework", "methodology",
    ],
    "evolution": [
        "evolution", "shift", "transition", "from.*to", "paradigm shift",
        "old.*new", "before.*after", "histor", "progress", "development",
        "era", "generation", "next generation", "emerging",
    ],
    "mechanics": [
        "mechanic", "architect", "system", "pipeline", "loop", "iterat",
        "feedback", "control", "orchestr", "workflow", "process", "how.*work",
        "implementation", "design", "structure", "component", "module",
    ],
    "challenges": [
        "challeng", "limitation", "problem", "issue", "risk", "barrier",
        "bottleneck", "failure", "error", "debug", "troubleshoot", "fix",
        "mitigat", "common problem", "pitfall", "drawback", "constraint",
    ],
    "applications": [
        "application", "use case", "case study", "real.*world", "industry",
        "practical", "deploy", "implement", "adopt", "example", "scenario",
        "production", "enterprise", "business", "sector",
    ],
    "future": [
        "future", "trend", "outlook", "next.*generat", "emerging", "roadmap",
        "vision", "prediction", "forecast", "direction", "evolution",
        "what.*next", "upcoming", "frontier", "horizon",
    ],
}

SECTION_TITLES = {
    "definition": "What Is Loop Engineering?",
    "evolution": "From Prompt to Loop: The Paradigm Shift",
    "mechanics": "How Loop Engineering Works",
    "challenges": "Common Problems & Fixes",
    "applications": "Real-World Applications",
    "future": "Future Outlook",
}

THEME_ORDER = ["definition", "evolution", "mechanics", "challenges", "applications", "future"]


# ── Text cleaning ───────────────────────────────────────────────────────────

def clean_text(text):
    """Strip boilerplate, metadata, and noise from scraped content."""
    if not text:
        return ""
    t = text
    # Remove social media handles
    t = re.sub(r'@[a-zA-Z0-9_]+', '', t)
    # Remove timestamps
    t = re.sub(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', '', t)
    t = re.sub(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}', '', t, flags=re.IGNORECASE)
    # Remove "Read more" etc.
    t = re.sub(r'(?:Read more|Continue reading|Read on|Read full article|Read the full article|Read the full post|Read the full story|Read the full report|Read the full analysis|Read the full guide|Read the full tutorial|Read the full review|Read the full summary|Read the full overview)', '', t, flags=re.IGNORECASE)
    # Remove author bylines
    t = re.sub(r'(?:By|Author|Written by|Posted by|Published by|Authored by|Created by)\s+[A-Z][a-zA-Z\s]+(?:\s+(?:of|at|on|in|for|via|through|with|and|or|but|nor|for|yet|so|the|a|an|is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|shall|should|may|might|must|can|could|to|from|as|into|during|before|after|above|below|between|out|off|over|under|again|further|then|once|here|there|when|where|why|how|all|both|each|few|more|most|other|some|such|no|not|only|own|same|than|too|very|just))?', '', t, flags=re.IGNORECASE)
    # Remove common website boilerplate
    t = re.sub(r'(?:Share this|Share this article|Share this post|Share this link|Share this content|Share this page)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'(?:Tags?:|Categories?:|Filed under:|Posted in:|Published in:|Category:|Tag:|Tags:|Categories:)', '', t, flags=re.IGNORECASE)
    # Remove URLs
    t = re.sub(r'https?://[^\s<>"\')]+', '', t)
    # Collapse whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def extract_sentences(text):
    """Split text into sentences, filtering by length."""
    if not text:
        return []
    raw = re.split(r'(?<=[.!?])\s+', text)
    sentences = []
    for s in raw:
        s = s.strip()
        if MIN_SENTENCE_LENGTH <= len(s) <= MAX_SENTENCE_LENGTH:
            sentences.append(s)
    return sentences


def deduplicate_content(items):
    """Remove near-duplicate items based on content fingerprint."""
    if not items:
        return []
    seen = set()
    result = []
    for item in items:
        content = (item[1] or "").strip().lower()
        fp = content[:200]
        if fp not in seen:
            seen.add(fp)
            result.append(item)
    return result


# ── Source clustering ───────────────────────────────────────────────────────

def extract_themes(items):
    """Group (title, content, url) items into thematic buckets."""
    themes = {k: [] for k in THEME_MAP}
    for item in items:
        title = (item[0] or "").lower()
        content = (item[1] or "").lower()
        combined = f"{title} {content}"
        best_theme = None
        best_score = 0
        for theme_key, keywords in THEME_MAP.items():
            score = 0
            for kw in keywords:
                if kw in combined:
                    score += 1
            if score > best_score:
                best_score = score
                best_theme = theme_key
        if best_theme and best_score > 0:
            themes[best_theme].append(item)
    # Sort each bucket by content length (most informative first)
    for k in themes:
        themes[k].sort(key=lambda x: len(x[1] or ""), reverse=True)
    return themes


# ── LLM prompt template for report synthesis ────────────────────────────────

def _build_synthesis_prompt(topic, themes, all_data):
    """Build a structured prompt for the LLM to synthesize the research report.

    Uses proven prompt engineering techniques:
    - Chain-of-thought: asks the LLM to reason step-by-step
    - Few-shot structure: provides exact output format
    - Explicit constraints: length, tone, citation style
    - Source-aware: each section gets its own source material
    """
    total_queries = all_data.get("total_queries", 0) if all_data else 0
    rounds = all_data.get("rounds", 0) if all_data else 0
    web_count = len(all_data.get("sources", [])) if all_data else 0
    pdf_count = len(all_data.get("pdf_sources", [])) if all_data else 0
    research_count = len(all_data.get("research_sources", [])) if all_data else 0

    # Build per-theme source blocks
    theme_blocks = {}
    for theme_key in THEME_ORDER:
        items = themes.get(theme_key, [])
        if not items:
            continue
        sources_text = []
        for idx, (title, content, url) in enumerate(items[:TOP_SOURCES_PER_THEME]):
            clean = clean_text(content or "")
            if len(clean) < 100:
                continue
            sources_text.append(
                f"--- Source {idx + 1}: {title or 'Untitled'} ---\n"
                f"URL: {url}\n"
                f"{clean[:1500]}\n"
            )
        if sources_text:
            theme_blocks[theme_key] = "\n\n".join(sources_text)

    prompt = f"""You are a senior research analyst producing a concise, well-structured research report.

## TASK
Synthesize the provided source material into a professional research report on: **{topic}**

## INPUT DATA
- Web pages: {web_count} | PDFs: {pdf_count} | Research papers: {research_count}
- Total queries: {total_queries} | Research rounds: {rounds}
- Source material is organized into thematic sections below.

## REPORT STRUCTURE (follow EXACTLY)

# Deep Research Report: {topic}

**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
**Sources:** {sum(len(v) for v in theme_blocks.values())} unique | **Queries:** {total_queries} | **Rounds:** {rounds}
**Data:** {web_count} web pages + {pdf_count} PDFs + {research_count} research papers

---

## Executive Summary

Provide 4-6 bullet points (one per theme that has content) summarizing the key insight from each theme. Each bullet should be 1-2 sentences, capturing the most important finding. Use concise, authoritative language.

---

## [Section Title]

[Write 2-4 well-crafted paragraphs synthesizing the sources for this theme. Do NOT just list facts — weave them into a coherent narrative. Compare and contrast different sources. Highlight agreements and disagreements. Use inline citations like [S1], [S2] etc. referencing the source numbers. Keep each section to 300-500 words. Write in a professional, analytical tone suitable for a technical audience.]

## References

| # | Title | URL |
|---|-------|-----|
[Add all unique sources here, numbered sequentially, up to {MAX_REFERENCES} entries.]

---

*Report generated by Deep Research Skill. Content synthesized from {sum(len(v) for v in theme_blocks.values())} sources.*

## WRITING GUIDELINES

1. **Synthesize, don't summarize.** Don't just restate each source — integrate insights across sources to create new understanding.
2. **Be specific.** Use concrete examples, data points, and technical details from the sources.
3. **Show tension.** When sources disagree, note it. This adds analytical depth.
4. **Cite properly.** Use [S1], [S2] etc. inline. Each claim should be backed by a source.
5. **Stay concise.** Target ~8,000 characters total. Every sentence must earn its place.
6. **Professional tone.** Write like a senior analyst at a top research firm.
7. **No fluff.** Skip introductions like "In this report we will discuss..." — dive straight in.
8. **Actionable insights.** End each section with what this means for practitioners.

## OUTPUT FORMAT REQUIREMENTS

- Use Markdown formatting throughout
- Use ## for section headings, ### for subsections if needed
- Use **bold** for key terms on first use
- Use inline code for technical terms (e.g., `agent loop`, `critic module`)
- Use [S1], [S2] etc. for citations (matching the References table)
- Keep total output under 8,000 characters
- End with the References table and footer line

## SOURCE MATERIAL

"""

    for theme_key in THEME_ORDER:
        if theme_key not in theme_blocks:
            continue
        title = SECTION_TITLES.get(theme_key, theme_key.title())
        prompt += f"\n\n{'='*60}\n"
        prompt += f"THEME: {title} ({theme_key})\n"
        prompt += f"{'='*60}\n\n"
        prompt += theme_blocks[theme_key]

    prompt += f"\n\n{'='*60}\n"
    prompt += "Now produce the complete research report following the structure and guidelines above.\n"
    prompt += "Write the report directly — do not include any meta-commentary about your process.\n"

    return prompt


# ── LLM call helper ─────────────────────────────────────────────────────────

def _call_llm(prompt, max_tokens=4000):
    """Call the Tiny Fish API to synthesize the report.

    Falls back to deterministic synthesis if LLM is unavailable.
    """
    api_key = os.environ.get("TINYFISH_API_KEY", "sk-tinyfish-vHbgNi2R-tVLAXFixslJ3lk5iz71dIsE")
    url = "https://api.tinyfish.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "qwen3-coder-plus",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a senior research analyst. Produce concise, well-structured "
                    "research reports from source material. Follow the exact output format "
                    "specified in the prompt. Be analytical, specific, and professional. "
                    "Stay within the 8,000 character limit."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    try:
        import urllib.request
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  ⚠ LLM synthesis failed ({e}), falling back to deterministic synthesis")
        return None


# ── Deterministic fallback synthesis ────────────────────────────────────────

def _fallback_synthesize(topic, themes, all_data):
    """Fallback when LLM is unavailable: structured extractive synthesis."""
    total_queries = all_data.get("total_queries", 0) if all_data else 0
    rounds = all_data.get("rounds", 0) if all_data else 0
    web_count = len(all_data.get("sources", [])) if all_data else 0
    pdf_count = len(all_data.get("pdf_sources", [])) if all_data else 0
    research_count = len(all_data.get("research_sources", [])) if all_data else 0

    lines = []
    lines.append(f"# Deep Research Report: {topic}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Sources:** {sum(len(v) for v in themes.values())} unique | **Queries:** {total_queries} | **Rounds:** {rounds}")
    lines.append(f"**Data:** {web_count} web pages + {pdf_count} PDFs + {research_count} research papers")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Executive summary
    exec_bullets = []
    for theme_key in THEME_ORDER:
        items = themes.get(theme_key, [])
        if items:
            clean = clean_text(items[0][1] or "")
            sentences = extract_sentences(clean)
            if sentences:
                exec_bullets.append(f"- {sentences[0][:200]}")
    if exec_bullets:
        lines.append("## Executive Summary")
        lines.append("")
        for b in exec_bullets[:6]:
            lines.append(b)
        lines.append("")
        lines.append("---")
        lines.append("")

    # Thematic sections
    ref_offset = 1
    for theme_key in THEME_ORDER:
        items = themes.get(theme_key, [])
        if not items:
            continue
        title = SECTION_TITLES.get(theme_key, theme_key.title())
        lines.append(f"## {title}")
        lines.append("")

        # Extract key sentences from top sources
        selected = []
        seen = set()
        for idx, (t, c, u) in enumerate(items[:TOP_SOURCES_PER_THEME]):
            clean = clean_text(c or "")
            sentences = extract_sentences(clean)
            for sent in sentences:
                key = sent.lower().strip()[:150]
                if key not in seen and len(selected) < 10:
                    seen.add(key)
                    selected.append((sent, ref_offset + idx))

        # Build paragraphs
        paragraphs = []
        current = []
        for sent, ref in selected:
            current.append(f"{sent} [S{ref}]")
            if len(current) >= 2:
                paragraphs.append(" ".join(current))
                current = []
        if current:
            paragraphs.append(" ".join(current))

        lines.extend(paragraphs)
        lines.append("")
        lines.append("---")
        lines.append("")
        ref_offset += len(items[:TOP_SOURCES_PER_THEME])

    # References
    all_items = []
    for items in themes.values():
        all_items.extend(items)
    all_items = deduplicate_content(all_items)

    lines.append("## References")
    lines.append("")
    lines.append("| # | Title | URL |")
    lines.append("|---|-------|-----|")
    for i, (title, summary, url) in enumerate(all_items[:MAX_REFERENCES], 1):
        safe_title = (title or "Untitled").replace("|", "\\|").replace("\\", "\\\\")
        lines.append(f"| {i} | {safe_title} | {url} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"*Report generated by Deep Research Skill. "
        f"Content synthesized from {len(all_items)} sources.*"
    )

    full = "\n".join(lines)
    if len(full) > MAX_REPORT_LENGTH:
        cutoff = full[:MAX_REPORT_LENGTH]
        last_para = cutoff.rfind("\n\n")
        if last_para > MAX_REPORT_LENGTH * 0.8:
            cutoff = cutoff[:last_para]
        cutoff = cutoff.rstrip() + "\n\n---\n\n*Report truncated to fit reading budget.*"
        full = cutoff
    return full


# ── Report assembly ─────────────────────────────────────────────────────────

def build_report(topic, all_items, ref_offset=1, all_data=None):
    """Build the complete research report using LLM synthesis with fallback."""
    if not all_items:
        return None

    deduped = deduplicate_content(all_items)
    if not deduped:
        return None

    themes = extract_themes(deduped)

    # Try LLM synthesis first
    prompt = _build_synthesis_prompt(topic, themes, all_data)
    llm_result = _call_llm(prompt)

    if llm_result and len(llm_result.strip()) > 500:
        # LLM succeeded — enforce length limit
        report = llm_result.strip()
        if len(report) > MAX_REPORT_LENGTH:
            cutoff = report[:MAX_REPORT_LENGTH]
            last_para = cutoff.rfind("\n\n")
            if last_para > MAX_REPORT_LENGTH * 0.8:
                cutoff = cutoff[:last_para]
            cutoff = cutoff.rstrip() + "\n\n---\n\n*Report truncated to fit reading budget.*"
            report = cutoff
        return report

    # Fallback to deterministic synthesis
    print("  Using deterministic fallback synthesis...")
    return _fallback_synthesize(topic, themes, all_data)


# ── Slideshow ───────────────────────────────────────────────────────────────

def build_slideshow(topic, all_items, ref_offset=1, all_data=None):
    """Build a beautiful HTML/CSS slideshow from research content."""
    if not all_items:
        return None

    deduped = deduplicate_content(all_items)
    if not deduped:
        return None

    themes = extract_themes(deduped)
    theme_order = THEME_ORDER
    theme_titles = {
        "definition": "What Is Loop Engineering?",
        "evolution": "From Prompt to Loop",
        "mechanics": "How It Works",
        "challenges": "Problems & Fixes",
        "applications": "Real-World Use",
        "future": "Future Outlook",
    }

    slides = []
    total_queries = all_data.get("total_queries", 0) if all_data else 0
    rounds = all_data.get("rounds", 0) if all_data else 0

    # Title slide
    slides.append({
        "title": "Loop Engineering",
        "subtitle": f"Deep Research: {topic}",
        "body": f"{len(deduped)} sources · {total_queries} queries · {rounds} rounds",
        "type": "title",
    })

    for theme_key in theme_order:
        items = themes.get(theme_key, [])
        if not items:
            continue
        bullets = []
        for title, content, url in items[:TOP_SOURCES_PER_THEME]:
            clean = clean_text(content or "")
            sentences = extract_sentences(clean)
            for sent in sentences:
                if 60 < len(sent) < 300:
                    bullets.append(sent[:250])
                    break
        if bullets:
            slides.append({
                "title": theme_titles[theme_key],
                "bullets": bullets[:5],
                "type": "content",
            })

    # Key takeaways
    slides.append({
        "title": "Key Takeaways",
        "bullets": [
            "Loop engineering replaces static prompts with iterative, self-correcting agent loops",
            "CI/CD pipelines must shift from linear gates to continuous feedback sources",
            "Common problems: infinite loops, context exhaustion, token cost, non-determinism",
            "Fixes: iteration budgets, context summarization, cost tiering, sandboxed execution",
            "Human-in-the-loop remains essential for production safety and governance",
        ],
        "type": "content",
    })

    return render_slideshow(topic, slides)


def render_slideshow(topic, slides):
    """Render slides as a beautiful HTML/CSS presentation."""
    slide_htmls = []
    for slide in slides:
        if slide["type"] == "title":
            slide_htmls.append(
                f'<section class="slide title-slide">'
                f'<h1>{slide["title"]}</h1>'
                f'<h2>{slide["subtitle"]}</h2>'
                f'<p class="meta">{slide["body"]}</p>'
                f'</section>'
            )
        else:
            bullets_html = "".join(f"<li>{b}</li>" for b in slide.get("bullets", []))
            slide_htmls.append(
                f'<section class="slide">'
                f'<h2>{slide["title"]}</h2>'
                f'<ul>{bullets_html}</ul>'
                f'</section>'
            )

    total = len(slides)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{topic} — Research Slides</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ height: 100%; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0f; color: #e0e0e0; overflow: hidden; }}
  .presentation {{ height: 100vh; display: flex; flex-direction: column; }}
  .slides-container {{ flex: 1; position: relative; overflow: hidden; }}
  .slide {{ position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 60px 80px; opacity: 0; transform: translateX(60px); transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); pointer-events: none; }}
  .slide.active {{ opacity: 1; transform: translateX(0); pointer-events: auto; }}
  .slide.prev {{ opacity: 0; transform: translateX(-60px); }}
  .title-slide h1 {{ font-size: 3.5rem; font-weight: 800; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 16px; text-align: center; }}
  .title-slide h2 {{ font-size: 1.5rem; font-weight: 400; color: #888; margin-bottom: 24px; text-align: center; }}
  .title-slide .meta {{ font-size: 1rem; color: #555; }}
  .slide h2 {{ font-size: 2.2rem; font-weight: 700; color: #667eea; margin-bottom: 32px; text-align: center; }}
  .slide ul {{ list-style: none; max-width: 800px; width: 100%; }}
  .slide li {{ font-size: 1.25rem; line-height: 1.8; padding: 12px 0 12px 28px; position: relative; color: #ccc; }}
  .slide li::before {{ content: '\\25b8'; position: absolute; left: 0; color: #764ba2; font-weight: bold; }}
  .slide li:nth-child(even) {{ color: #aaa; }}
  .controls {{ display: flex; justify-content: center; align-items: center; gap: 20px; padding: 20px; background: rgba(10,10,15,0.95); border-top: 1px solid #1a1a2e; }}
  .controls button {{ background: linear-gradient(135deg, #667eea, #764ba2); border: none; color: white; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-size: 1rem; font-weight: 600; transition: transform 0.2s; }}
  .controls button:hover {{ transform: scale(1.05); }}
  .controls button:disabled {{ opacity: 0.3; cursor: default; transform: none; }}
  .progress {{ display: flex; gap: 6px; }}
  .progress-dot {{ width: 10px; height: 10px; border-radius: 50%; background: #333; transition: all 0.3s; }}
  .progress-dot.active {{ background: #667eea; transform: scale(1.3); }}
  .slide-counter {{ font-size: 0.9rem; color: #555; min-width: 60px; text-align: center; }}
  @media (max-width: 768px) {{
    .title-slide h1 {{ font-size: 2rem; }}
    .title-slide h2 {{ font-size: 1.1rem; }}
    .slide h2 {{ font-size: 1.5rem; }}
    .slide li {{ font-size: 1rem; }}
    .slide {{ padding: 30px 20px; }}
  }}
</style>
</head>
<body>
<div class="presentation">
  <div class="slides-container" id="slidesContainer">
    {chr(10).join(slide_htmls)}
  </div>
  <div class="controls">
    <button id="prevBtn" onclick="prevSlide()">\\u2190 Prev</button>
    <div class="progress" id="progressBar"></div>
    <span class="slide-counter" id="slideCounter">1 / {total}</span>
    <button id="nextBtn" onclick="nextSlide()">Next \\u2192</button>
  </div>
</div>
<script>
  const slides = document.querySelectorAll('.slide');
  let current = 0;
  const total = slides.length;
  const progressBar = document.getElementById('progressBar');
  const counter = document.getElementById('slideCounter');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  for (let i = 0; i < total; i++) {{
    const dot = document.createElement('div');
    dot.className = 'progress-dot';
    dot.onclick = () => goToSlide(i);
    dot.title = `Slide ${{i+1}}`;
    progressBar.appendChild(dot);
  }}
  function update() {{
    slides.forEach((s, i) => {{
      s.classList.remove('active', 'prev');
      if (i === current) s.classList.add('active');
      else if (i < current) s.classList.add('prev');
    }});
    const dots = progressBar.querySelectorAll('.progress-dot');
    dots.forEach((d, i) => d.classList.toggle('active', i === current));
    counter.textContent = `${{current + 1}} / ${{total}}`;
    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === total - 1;
  }}
  function nextSlide() {{ if (current < total - 1) {{ current++; update(); }} }}
  function prevSlide() {{ if (current > 0) {{ current--; update(); }} }}
  function goToSlide(i) {{ current = i; update(); }}
  document.addEventListener('keydown', (e) => {{
    if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
    if (e.key === 'ArrowLeft') prevSlide();
    if (e.key === 'Home') goToSlide(0);
    if (e.key === 'End') goToSlide(total - 1);
  }});
  update();
</script>
</body>
</html>"""
    return html
