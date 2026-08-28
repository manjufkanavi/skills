#!/usr/bin/env python3
"""Regenerate HTML slideshow from research_data.json with same content as markdown report."""
import json
import re
from datetime import datetime
from pathlib import Path

# Read research data
data_path = Path("/Users/manjunathkanavi/.nanobot/workspace/skills/deep-research/research_data.json")
with open(data_path) as f:
    data = json.load(f)

topic = data["topic"]
all_items = [(item["title"], item["content"], item["url"]) for item in data["all_items"]]

# Read the markdown report to extract the exact content used
md_path = Path("/Users/manjunathkanavi/.nanobot/workspace/personal_bot/deep-research/reports/loop-engineering-cicd-adaptation.md")
md_content = md_path.read_text()

# Extract section content from markdown report
sections = {}
current_section = None
current_lines = []
for line in md_content.split("\n"):
    if line.startswith("## "):
        if current_section:
            sections[current_section] = "\n".join(current_lines).strip()
        current_section = line[3:].strip()
        current_lines = []
    elif current_section:
        current_lines.append(line)
if current_section:
    sections[current_section] = "\n".join(current_lines).strip()

# Build slides from the same sections as the markdown report
slides = []
slides.append({
    "title": "Loop Engineering",
    "subtitle": f"Deep Research Report: {topic}",
    "body": f"Sources: {len(data['all_items'])} | Queries: {data['total_queries']} | Rounds: {data['rounds']}",
    "type": "title"
})

# Map markdown sections to slides
section_map = {
    "What Is Loop Engineering?": "definition",
    "From CI/CD to Loop-Driven CI/CD: The Paradigm Shift": "evolution",
    "How Loop-Driven CI/CD Works": "mechanics",
    "Common Problems & Fixes": "challenges",
    "Real-World Applications": "applications",
    "Future Outlook": "future",
}

for md_section, theme_key in section_map.items():
    if md_section in sections:
        # Extract key sentences from the section
        text = sections[md_section]
        sentences = re.split(r'(?<=[.!?])\s+', text)
        bullets = []
        for sent in sentences:
            sent = sent.strip()
            if 60 < len(sent) < 300 and sent not in bullets:
                bullets.append(sent[:250])
                if len(bullets) >= 5:
                    break
        if bullets:
            slides.append({
                "title": md_section,
                "bullets": bullets,
                "type": "content"
            })

# Add summary slide
slides.append({
    "title": "Key Takeaways",
    "bullets": [
        "Loop engineering replaces static prompts with iterative, self-correcting agent loops",
        "CI/CD pipelines must shift from linear gates to continuous feedback sources",
        "Common problems: infinite loops, context exhaustion, token cost, non-determinism",
        "Fixes: iteration budgets, context summarization, cost tiering, sandboxed execution",
        "Human-in-the-loop remains essential for production safety and governance"
    ],
    "type": "content"
})

# Build HTML
slide_htmls = []
for i, slide in enumerate(slides):
    if slide["type"] == "title":
        slide_htmls.append(f"""<section class="slide title-slide">
            <h1>{slide["title"]}</h1>
            <h2>{slide["subtitle"]}</h2>
            <p class="meta">{slide["body"]}</p>
        </section>""")
    else:
        bullets_html = ""
        for bullet in slide.get("bullets", []):
            bullets_html += f'<li>{bullet}</li>'
        slide_htmls.append(f"""<section class="slide">
            <h2>{slide["title"]}</h2>
            <ul>{bullets_html}</ul>
        </section>""")

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
  .slide li::before {{ content: '▸'; position: absolute; left: 0; color: #764ba2; font-weight: bold; }}
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
    <button id="prevBtn" onclick="prevSlide()">← Prev</button>
    <div class="progress" id="progressBar"></div>
    <span class="slide-counter" id="slideCounter">1 / {len(slides)}</span>
    <button id="nextBtn" onclick="nextSlide()">Next →</button>
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
  // Build progress dots
  for (let i = 0; i < total; i++) {{
    const dot = document.createElement('div');
    dot.className = 'progress-dot';
    dot.onclick = () => goToSlide(i);
    dot.title = `Slide ${i+1}`;
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

# Save HTML
report_dir = Path("/Users/manjunathkanavi/.nanobot/workspace/personal_bot/deep-research/reports")
report_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
slide_path = report_dir / f"loop-engineering-cicd-adaptation-{timestamp}.html"
slide_path.write_text(html, encoding="utf-8")
print(f"Saved: {slide_path}")
print(f"Size: {len(html)} chars")
print(f"Slides: {len(slides)}")
