#!/usr/bin/env python3
"""Generate HTML slideshow from research_data.json for mobile phones topic."""
import json
import re
from datetime import datetime
from pathlib import Path

data_path = Path("/Users/manjunathkanavi/.nanobot/workspace/personal_bot/skills/deep-research/research_data.json")
with open(data_path) as f:
    data = json.load(f)

topic = data["topic"]
date = datetime.now().strftime("%Y-%m-%d")

# Read the markdown report to extract the exact content used
md_path = Path(f"/Users/manjunathkanavi/.nanobot/workspace/personal_bot/skills/deep-research/reports/{topic.replace(' ', '-').lower()}/{date}/report.md")
md_content = md_path.read_text()

# Extract section content from markdown report - handle both ## and ### headers
sections = {}
current_section = None
current_lines = []
for line in md_content.split("\n"):
    if line.startswith("## "):
        if current_section:
            sections[current_section] = "\n".join(current_lines).strip()
        current_section = line.lstrip('#').strip()
        current_lines = []
    elif current_section:
        current_lines.append(line)
if current_section:
    sections[current_section] = "\n".join(current_lines).strip()

print(f"Found sections: {list(sections.keys())}")

# Build slides from the same sections as the markdown report
slides = []
slides.append({
    "title": "Evolution of Mobile Phones",
    "subtitle": "Deep Research Report",
    "body": f"Sources: {len(data['all_items'])} | Queries: {data['total_queries']} | Rounds: {data['rounds']}",
    "type": "title"
})

# Map section names to slide titles
section_map = {
    "Executive Summary": "Executive Summary",
    "1. Historical Evolution: From Bricks to Smartphones": "Historical Evolution",
    "2. Technical Mechanics: How Mobile Communication Works": "Technical Mechanics",
    "3. Challenges and Concerns": "Challenges & Concerns",
    "4. Applications and Impact": "Applications & Impact",
    "5. Future Trajectory": "Future Trajectory",
    "6. Must-Have Skills for Understanding Mobile Evolution": "Must-Have Skills",
    "7. Must-Have MCPs (Model Context Protocols)": "Must-Have MCPs",
    "8. Best Practices": "Best Practices",
    "9. New Trends (2024-2026)": "New Trends",
}

for md_section, slide_title in section_map.items():
    # Try exact match first, then partial match
    text = sections.get(md_section, "")
    if not text:
        # Try partial match
        for key in sections:
            if md_section in key or key in md_section:
                text = sections[key]
                break
    if text:
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'#{1,6}\s*', '', text)
        text = re.sub(r'\|.*?\|', '', text)  # Remove table rows
        # Split into lines, filter for meaningful content
        lines = [l.strip() for l in text.split('\n') if l.strip() and not l.strip().startswith('---')]
        bullets = []
        for line in lines:
            if 30 < len(line) < 300 and line not in bullets:
                bullets.append(line[:280])
                if len(bullets) >= 6:
                    break
        if bullets:
            slides.append({
                "title": slide_title,
                "bullets": bullets,
                "type": "content"
            })

# Add summary slide
slides.append({
    "title": "Key Takeaways",
    "bullets": [
        "Mobile phones evolved from 1kg 'brick' phones (1983) to AI-powered smartphones in under 40 years",
        "7 billion+ people now own mobile phones — more than have access to clean water or electricity",
        "Each generation (1G→5G) brought exponential improvements in speed, capability, and connectivity",
        "Mobile phones are catalysts for economic empowerment, especially in developing countries",
        "Future trends: 6G, AI-first devices, foldable displays, satellite connectivity, AR/VR integration",
        "Critical challenges: health effects, digital divide, e-waste, privacy, and security"
    ],
    "type": "content"
})

# Build HTML with dark/light theme
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
<title>{topic.replace(' ', '-')} — Research Slides</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ height: 100%; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; overflow: hidden; }}
  body {{ background: #0a0a0f; color: #e0e0e0; }}
  body.light {{ background: #f5f5f5; color: #1a1a1a; }}
  .presentation {{ height: 100vh; display: flex; flex-direction: column; }}
  .slides-container {{ flex: 1; position: relative; overflow: hidden; }}
  .slide {{ position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 60px 80px; opacity: 0; transform: translateX(60px) scale(0.98); transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1); pointer-events: none; }}
  .slide.active {{ opacity: 1; transform: translateX(0) scale(1); pointer-events: auto; }}
  .slide.prev {{ opacity: 0; transform: translateX(-60px) scale(0.98); }}
  .title-slide h1 {{ font-size: 3.5rem; font-weight: 800; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 16px; text-align: center; }}
  .title-slide h2 {{ font-size: 1.5rem; font-weight: 400; color: #888; margin-bottom: 24px; text-align: center; }}
  .title-slide .meta {{ font-size: 1rem; color: #555; }}
  body.light .title-slide h2 {{ color: #666; }}
  body.light .title-slide .meta {{ color: #888; }}
  .slide h2 {{ font-size: 2.2rem; font-weight: 700; color: #667eea; margin-bottom: 32px; text-align: center; }}
  .slide ul {{ list-style: none; max-width: 800px; width: 100%; }}
  .slide li {{ font-size: 1.25rem; line-height: 1.8; padding: 12px 0 12px 28px; position: relative; color: #ccc; }}
  .slide li::before {{ content: '▸'; position: absolute; left: 0; color: #764ba2; font-weight: bold; }}
  body.light .slide li {{ color: #333; }}
  body.light .slide li::before {{ color: #764ba2; }}
  .controls {{ display: flex; justify-content: center; align-items: center; gap: 20px; padding: 20px; background: rgba(10,10,15,0.95); border-top: 1px solid #1a1a2e; }}
  body.light .controls {{ background: rgba(245,245,245,0.95); border-top-color: #ddd; }}
  .controls button {{ background: linear-gradient(135deg, #667eea, #764ba2); border: none; color: white; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-size: 1rem; font-weight: 600; transition: transform 0.2s; }}
  .controls button:hover {{ transform: scale(1.05); }}
  .controls button:disabled {{ opacity: 0.3; cursor: default; transform: none; }}
  .progress {{ display: flex; gap: 6px; }}
  .progress-dot {{ width: 10px; height: 10px; border-radius: 50%; background: #333; transition: all 0.3s; cursor: pointer; }}
  .progress-dot.active {{ background: #667eea; transform: scale(1.3); }}
  .slide-counter {{ font-size: 0.9rem; color: #555; min-width: 60px; text-align: center; }}
  .theme-toggle {{ position: fixed; top: 20px; right: 20px; z-index: 100; background: rgba(100,100,100,0.3); border: 1px solid #333; color: #ccc; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 0.85rem; }}
  body.light .theme-toggle {{ background: rgba(100,100,100,0.1); border-color: #ccc; color: #333; }}
  @media (max-width: 768px) {{
    .title-slide h1 {{ font-size: 2rem; }}
    .title-slide h2 {{ font-size: 1.1rem; }}
    .slide h2 {{ font-size: 1.5rem; }}
    .slide li {{ font-size: 1rem; }}
    .slide {{ padding: 30px 20px; }}
    .controls {{ gap: 10px; padding: 12px; }}
    .controls button {{ padding: 8px 16px; font-size: 0.9rem; }}
  }}
</style>
</head>
<body>
<button class="theme-toggle" onclick="toggleTheme()">🌙 Dark</button>
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
  function toggleTheme() {{
    document.body.classList.toggle('light');
    const btn = document.querySelector('.theme-toggle');
    btn.textContent = document.body.classList.contains('light') ? '☀️ Light' : '🌙 Dark';
  }}
  update();
</script>
</body>
</html>"""

# Save HTML
report_dir = Path("/Users/manjunathkanavi/.nanobot/workspace/personal_bot/skills/deep-research/reports")
report_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
slide_path = report_dir / f"evolution-of-mobile-phones-{timestamp}.html"
slide_path.write_text(html, encoding="utf-8")
print(f"Saved: {slide_path}")
print(f"Size: {len(html)} chars")
print(f"Slides: {len(slides)}")
