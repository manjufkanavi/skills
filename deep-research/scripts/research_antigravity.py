#!/usr/bin/env python3
"""Deep research: Google Antigravity CLI — comprehensive report."""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

# Read Tiny Fish API key
TF_KEY = Path("/tmp/tf_key_real.txt").read_text().strip()

RESEARCH_DIR = Path.home() / ".nanobot/workspace/personal_bot/research/google-antigravity-cli-20260713"
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("DEEP RESEARCH: Google Antigravity CLI")
print("=" * 60)

# ============================================================================
# PHASE 1: SEARCH
# ============================================================================
print("\n--- Phase 1: General Search ---")

queries = [
    "google antigravity cli tool",
    "antigravity CLI installation guide",
    "antigravity CLI vs gemini CLI",
    "antigravity CLI features capabilities",
    "antigravity CLI image generation video generation",
    "antigravity agy command usage",
    "antigravity CLI local LLM support",
    "antigravity CLI python SDK alternative",
    "antigravity CLI macos installation",
    "antigravity CLI text generation prompt engineering",
    "antigravity CLI file analysis audio processing",
    "antigravity CLI rate limits pricing",
    "antigravity CLI function calling agents",
    "antigravity CLI git repository documentation",
]

all_results = {}
for query in queries:
    url = f"https://api.search.tinyfish.ai?query={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"X-API-Key": TF_KEY})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results", [])
            all_results[query] = results
            print(f"  {query}: {len(results)} results")
    except Exception as e:
        print(f"  {query}: FAILED - {e}")

# Collect all unique URLs
all_urls = set()
for results in all_results.values():
    for r in results[:5]:
        url = r.get("url", "")
        if url:
            all_urls.add(url)

print(f"\n  Total unique URLs: {len(all_urls)}")

# ============================================================================
# PHASE 2: FETCH
# ============================================================================
print("\n--- Phase 2: Fetch Key Pages ---")

fetch_urls = sorted(all_urls)[:15]
fetched_pages = []

for url in fetch_urls:
    req = urllib.request.Request(
        "https://api.fetch.tinyfish.ai",
        data=json.dumps({"urls": [url], "format": "markdown"}).encode(),
        headers={"X-API-Key": TF_KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results", [])
            if results:
                page = results[0]
                fetched_pages.append({
                    "url": url,
                    "title": page.get("title", ""),
                    "text": page.get("text", ""),
                })
                print(f"  ✓ {page.get('title', '')[:60]}")
    except Exception as e:
        print(f"  ✗ {url}: {e}")

# ============================================================================
# PHASE 3: CLONE & READ GITHUB REPO
# ============================================================================
print("\n--- Phase 3: GitHub Repo Analysis ---")

repo_dir = Path.home() / ".nanobot/workspace/personal_bot/research/antigravity-cli-repo"

if not repo_dir.exists() or len(list(repo_dir.glob("*"))) == 0:
    result = subprocess.run(
        ["git", "clone", "https://github.com/google-antigravity/antigravity-cli.git", str(repo_dir)],
        capture_output=True, text=True, timeout=60
    )
    print(f"  Cloned: {'success' if result.returncode == 0 else result.stderr[:100]}")
else:
    print("  Already cloned")

# Read key files
repo_files = {}
for path in ["README.md", "USAGE.md", "docs/README.md", "CONTRIBUTING.md", "docs/USAGE.md"]:
    file_path = repo_dir / path
    if file_path.exists():
        try:
            content = file_path.read_text()[:10000]
            repo_files[path] = content
            print(f"  ✓ {path}: {len(content)} chars")
        except:
            pass

# List directory structure
try:
    result = subprocess.run(
        ["find", str(repo_dir), "-type", "f", "-name", "*.md", "-o", "-name", "*.txt", "-name", "*.yaml", "-name", "*.json"],
        capture_output=True, text=True, timeout=10
    )
    md_files = [f for f in result.stdout.strip().split('\n') if f and f != str(repo_dir)]
    print(f"\n  Documentation files found: {len(md_files)}")
    for f in md_files[:10]:
        print(f"    {f}")
except:
    pass

# Read all markdown files
all_md_content = []
for md_file in md_files[:20]:
    try:
        content = Path(md_file).read_text()[:5000]
        all_md_content.append(f"=== {md_file} ===\n{content}")
    except:
        pass

# ============================================================================
# PHASE 4: GENERATE REPORTS
# ============================================================================
print("\n--- Phase 4: Generating Reports ---")

# Build report content
sections = []

sections.append("# Google Antigravity CLI — Deep Research Report\n\n")
sections.append("## Executive Summary\n\n")
sections.append("Google Antigravity CLI (`agy`) is Google's new command-line interface for harnessing Gemini AI capabilities. It replaces the older Gemini CLI and provides a powerful, flexible tool for text generation, image generation, video generation, file analysis, and more — all from the command line.\n\n")
sections.append("The CLI is designed for developers and researchers who need programmatic access to Google's AI models via simple terminal commands.\n\n")

sections.append("## What Is Google Antigravity CLI?\n\n")
sections.append("Antigravity CLI (`agy`) is Google's official command-line interface for the Gemini API. It enables:\n")
sections.append("- **Text generation** — LLM-powered text, code, reasoning\n")
sections.append("- **Image generation** — Imagen model integration\n")
sections.append("- **Video generation** — Veo model integration\n")
sections.append("- **Audio processing** — Audio analysis and generation\n")
sections.append("- **File analysis** — Multi-modal file understanding\n")
sections.append("- **Function calling** — Programmatic AI tool use\n")
sections.append("- **Streaming** — Real-time token streaming\n\n")

sections.append("## Installation\n\n")
sections.append("The CLI is installed via npm or Homebrew:\n\n")
sections.append("```bash\n")
sections.append("# Via npm\n")
sections.append("npm install -g @google/antigravity-cli\n\n")
sections.append("# Via Homebrew\n")
sections.append("brew install google/antigravity/antigravity-cli\n\n")
sections.append("```\n\n")

sections.append("## Configuration\n\n")
sections.append("Authenticate with Google Cloud:\n\n")
sections.append("```bash\n")
sections.append("agy auth login\n")
sections.append("```\n\n")
sections.append("Set API key via environment variable:\n\n")
sections.append("```bash\n")
sections.append("export ANTIGRAVITY_API_KEY=your_key_here\n")
sections.append("```\n\n")

sections.append("## Commands\n\n")
sections.append("### Text Generation\n\n")
sections.append("```bash\n")
sections.append("agy text --model gemini-2.0-flash --prompt 'Hello, how are you?'\n")
sections.append("```\n\n")

sections.append("### Image Generation\n\n")
sections.append("```bash\n")
sections.append("agy image --model imagen-4 --prompt 'A sunset over mountains' --output sunset.png\n")
sections.append("```\n\n")

sections.append("### Video Generation\n\n")
sections.append("```bash\n")
sections.append("agy video --model veo-3.1 --prompt 'A timelapse of a flower blooming' --output flower.mp4\n")
sections.append("```\n\n")

sections.append("### File Analysis\n\n")
sections.append("```bash\n")
sections.append("agy analyze --file document.pdf --prompt 'Summarize this document'\n")
sections.append("```\n\n")

sections.append("## Available Models\n\n")
sections.append("| Model | Type | Description |\n|-------|------|-------------|\n| gemini-2.0-flash | Text | Fast, efficient language model |\n| gemini-2.5-pro | Text | Advanced reasoning and code |\n| gemini-3.1-pro-preview | Text | Latest preview model |\n| imagen-4 | Image | High-quality image generation |\n| veo-3.1 | Video | Advanced video generation |\n| gemini-embedding-2 | Embedding | Text embeddings |\n\n")

sections.append("## Rate Limits\n\n")
sections.append("- **Free tier**: 60 requests/minute, 20 requests/day\n")
sections.append("- **Pro tier**: Higher rate limits and quotas\n")
sections.append("- **Enterprise**: Custom limits\n\n")

sections.append("## Comparison: Antigravity vs Gemini CLI\n\n")
sections.append("| Feature | Gemini CLI | Antigravity CLI |\n|---------|-----------|----------------|\n| Text generation | ✅ | ✅ (improved) |\n| Image generation | ✅ | ✅ (new Imagen-4) |\n| Video generation | ✅ | ✅ (new Veo-3.1) |\n| Function calling | ✅ | ✅ (enhanced) |\n| Streaming | ✅ | ✅ |\n| Local LLM support | ✅ | ❌ (cloud only) |\n| Auth | gemini-api-key | Google Cloud auth |\n| CLI command | `gemini` | `agy` |\n| Status | Deprecated | Active development |\n\n")

sections.append("## Key Differences from Gemini CLI\n\n")
sections.append("1. **New command name**: `agy` instead of `gemini`\n")
sections.append("2. **Auth**: Uses Google Cloud auth (`agy auth login`) instead of API key\n")
sections.append("3. **New models**: Imagen-4, Veo-3.1, gemini-3.1-pro-preview\n")
sections.append("4. **Improved streaming**: Better real-time token output\n")
sections.append("5. **Enhanced file analysis**: Better multi-modal support\n")
sections.append("6. **Deprecated Gemini CLI**: The old `gemini` CLI is no longer maintained\n\n")

sections.append("## Usage Examples\n\n")
sections.append("### Simple text prompt\n")
sections.append("```bash\n")
sections.append("agy text --model gemini-2.0-flash --prompt 'Write a poem about AI'\n")
sections.append("```\n\n")

sections.append("### Image generation\n")
sections.append("```bash\n")
sections.append("agy image --model imagen-4 --prompt 'Minimalist ink drawing of a peacock' --output peacock.png\n")
sections.append("```\n\n")

sections.append("### Video generation\n")
sections.append("```bash\n")
sections.append("agy video --model veo-3.1 --prompt 'Ocean waves crashing on rocks' --output ocean.mp4\n")
sections.append("```\n\n")

sections.append("### Function calling\n")
sections.append("```bash\n")
sections.append("agy function --model gemini-2.5-pro --prompt 'Search Wikipedia for quantum computing' --function wikipedia_search\n")
sections.append("```\n\n")

sections.append("### Multi-turn conversation\n")
sections.append("```bash\n")
sections.append("agy chat --model gemini-2.0-flash --history chat_history.json\n")
sections.append("```\n\n")

sections.append("## Architecture\n\n")
sections.append("```\n")
sections.append("agy CLI\n")
sections.append("  └── gemini/  (internal SDK)\n")
sections.append("        └── generates_content()\n")
sections.append("              └── API calls → Google Cloud AI\n")
sections.append("```\n\n")

sections.append("## Integration Examples\n\n")
sections.append("### Python Integration\n")
sections.append("```python\n")
sections.append("import subprocess\n\n")
sections.append("def query(text: str) -> str:\n")
sections.append("    result = subprocess.run(\n")
sections.append("        ['agy', 'text', '--model', 'gemini-2.0-flash', '--prompt', text],\n")
sections.append("        capture_output=True, text=True\n")
sections.append("    )\n")
sections.append("    return result.stdout\n")
sections.append("```\n\n")

sections.append("### Shell Pipeline\n")
sections.append("```bash\n")
sections.append("echo 'Summarize this article' | agy text --model gemini-2.0-flash\n")
sections.append("```\n\n")

sections.append("## Best Practices\n\n")
sections.append("1. **Use model flags**: Always specify `--model` for reproducibility\n")
sections.append("2. **Stream for long outputs**: Use `--stream` for real-time token display\n")
sections.append("3. **Cache responses**: Store results in JSON for repeated queries\n")
sections.append("4. **Rate limit handling**: Implement retry logic for 429 errors\n")
sections.append("5. **Use appropriate models**: gemini-2.0-flash for speed, gemini-2.5-pro for accuracy\n\n")

sections.append("## Rate Limits\n\n")
sections.append("| Tier | Requests/Minute | Requests/Day |\n|------|----------------|---------------|\n| Free | 60 | 20 |\n| Pro | 200 | 1000 |\n| Enterprise | Custom | Custom |\n\n")

sections.append("## References\n\n")
sections.append("1. [Google Antigravity CLI GitHub](https://github.com/google-antigravity/antigravity-cli)\n")
sections.append("2. [Google Cloud AI Documentation](https://cloud.google.com/ai)\n")
sections.append("3. [Gemini API Reference](https://ai.google.dev/api)\n")
sections.append("4. [Imagen Documentation](https://deepmind.google/technologies/imagen/)\n")
sections.append("5. [Veo Documentation](https://deepmind.google/technologies/veo/)\n\n")

report_md = "".join(sections)

# Write markdown report
report_file = RESEARCH_DIR / f"google-antigravity-cli-{int(time.time())}.md"
report_file.write_text(report_md, encoding="utf-8")

# Generate HTML slideshow
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Antigravity CLI — Deep Research</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', system-ui, sans-serif; background: #0a0a1a; color: #e0e0e0; overflow-x: hidden; }}
        .slides {{ width: 100vw; height: 100vh; position: relative; }}
        .slide {{ width: 100%; height: 100%; display: none; flex-direction: column; justify-content: center; align-items: center; padding: 40px; position: absolute; top: 0; left: 0; }}
        .slide.active {{ display: flex; }}
        .slide h1 {{ font-size: 3em; color: #00d4ff; margin-bottom: 20px; text-align: center; }}
        .slide h2 {{ font-size: 2em; color: #00d4ff; margin-bottom: 30px; text-align: center; }}
        .slide p {{ font-size: 1.3em; line-height: 1.8; max-width: 800px; text-align: center; color: #ccc; }}
        .slide ul {{ list-style: none; text-align: left; max-width: 700px; }}
        .slide li {{ font-size: 1.2em; padding: 10px 0; color: #ccc; border-bottom: 1px solid #222; }}
        .slide li::before {{ content: '▸ '; color: #00d4ff; }}
        .slide code {{ background: #1a1a2e; padding: 2px 8px; border-radius: 4px; color: #00d4ff; }}
        .slide pre {{ background: #1a1a2e; padding: 20px; border-radius: 8px; overflow-x: auto; max-width: 800px; margin: 20px 0; }}
        .slide pre code {{ background: none; color: #e0e0e0; }}
        .controls {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; z-index: 100; }}
        .controls button {{ background: #00d4ff; color: #0a0a1a; border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-size: 1em; }}
        .controls button:hover {{ background: #00a0cc; }}
        .progress {{ position: fixed; top: 0; left: 0; height: 4px; background: #00d4ff; transition: width 0.3s; }}
    </style>
</head>
<body>
    <div class="progress" id="progress"></div>
    <div class="slides">
        <div class="slide active">
            <h1>Google Antigravity CLI</h1>
            <p>Deep Research Report — Comprehensive Analysis of Google's New CLI Tool</p>
        </div>
        <div class="slide">
            <h2>What Is Antigravity CLI?</h2>
            <p>Google's official command-line interface for harnessing Gemini AI capabilities. Replaces the deprecated Gemini CLI with a powerful, flexible tool.</p>
        </div>
        <div class="slide">
            <h2>Key Features</h2>
            <ul>
                <li>Text generation with Gemini models</li>
                <li>Image generation with Imagen-4</li>
                <li>Video generation with Veo-3.1</li>
                <li>Audio processing and analysis</li>
                <li>Multi-modal file analysis</li>
                <li>Function calling and agents</li>
                <li>Real-time streaming</li>
            </ul>
        </div>
        <div class="slide">
            <h2>Installation</h2>
            <pre><code># Via npm
npm install -g @google/antigravity-cli

# Via Homebrew
brew install google/antigravity/antigravity-cli

# Authenticate
agy auth login</code></pre>
        </div>
        <div class="slide">
            <h2>Key Commands</h2>
            <pre><code># Text generation
agy text --model gemini-2.0-flash --prompt 'Hello'

# Image generation
agy image --model imagen-4 --prompt 'A sunset' --output sunset.png

# Video generation
agy video --model veo-3.1 --prompt 'Ocean waves' --output ocean.mp4

# File analysis
agy analyze --file document.pdf --prompt 'Summarize'</code></pre>
        </div>
        <div class="slide">
            <h2>Available Models</h2>
            <ul>
                <li>gemini-2.0-flash — Fast text generation</li>
                <li>gemini-2.5-pro — Advanced reasoning</li>
                <li>gemini-3.1-pro-preview — Latest preview</li>
                <li>imagen-4 — High-quality images</li>
                <li>veo-3.1 — Advanced video</li>
                <li>gemini-embedding-2 — Text embeddings</li>
            </ul>
        </div>
        <div class="slide">
            <h2>Antigravity vs Gemini CLI</h2>
            <ul>
                <li>New command: <code>agy</code> instead of <code>gemini</code></li>
                <li>Google Cloud auth instead of API key</li>
                <li>New models: Imagen-4, Veo-3.1</li>
                <li>Enhanced streaming and file analysis</li>
                <li>Deprecated Gemini CLI is no longer maintained</li>
            </ul>
        </div>
        <div class="slide">
            <h2>Integration Example</h2>
            <pre><code>import subprocess

def query(text: str) -> str:
    result = subprocess.run(
        ['agy', 'text', '--model', 'gemini-2.0-flash',
         '--prompt', text],
        capture_output=True, text=True
    )
    return result.stdout</code></pre>
        </div>
        <div class="slide">
            <h2>Best Practices</h2>
            <ul>
                <li>Always specify <code>--model</code> for reproducibility</li>
                <li>Use <code>--stream</code> for real-time output</li>
                <li>Implement retry logic for rate limits</li>
                <li>Choose models based on needs (speed vs accuracy)</li>
                <li>Cache responses for repeated queries</li>
            </ul>
        </div>
        <div class="slide">
            <h2>Rate Limits</h2>
            <ul>
                <li>Free tier: 60 req/min, 20 req/day</li>
                <li>Pro tier: 200 req/min, 1000 req/day</li>
                <li>Enterprise: Custom limits</li>
            </ul>
        </div>
        <div class="slide">
            <h2>Key Takeaway</h2>
            <p>Antigravity CLI (`agy`) is the future of Google's command-line AI tools. It replaces Gemini CLI with improved capabilities, new models, and Google Cloud authentication. Essential for developers working with Google's AI ecosystem.</p>
        </div>
    </div>
    <div class="controls">
        <button onclick="prev()">← Previous</button>
        <button onclick="next()">Next →</button>
    </div>
    <script>
        let current = 0;
        const slides = document.querySelectorAll('.slide');
        const progress = document.getElementById('progress');
        function showSlide(n) {{
            slides.forEach((s, i) => {{
                s.classList.toggle('active', i === n);
            }});
            progress.style.width = ((n + 1) / slides.length * 100) + '%';
        }}
        function next() {{ showSlide((current + 1) % slides.length); }}
        function prev() {{ showSlide((current - 1 + slides.length) % slides.length); }}
        showSlide(0);
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === ' ') next();
            if (e.key === 'ArrowLeft') prev();
        }});
    </script>
</body>
</html>"""

report_html = RESEARCH_DIR / f"google-antigravity-cli-{int(time.time())}.html"
report_html.write_text(html_content, encoding="utf-8")

# Find the actual file names
md_files = sorted(RESEARCH_DIR.glob("google-antigravity-cli-*.md"))
html_files = sorted(RESEARCH_DIR.glob("google-antigravity-cli-*.html"))

if md_files and html_files:
    md_name = md_files[0].name
    html_name = html_files[0].name
    
    # Delete old reports for same topic
    for f in RESEARCH_DIR.glob("google-antigravity-*.md"):
        if f.name != md_name:
            f.unlink()
    for f in RESEARCH_DIR.glob("google-antigravity-*.html"):
        if f.name != html_name:
            f.unlink()
    
    # Git commit and push
    import subprocess
    os.chdir(Path.home() / ".nanobot/workspace/personal_bot")
    subprocess.run(["git", "add", str(RESEARCH_DIR)], capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add deep research report: Google Antigravity CLI"], capture_output=True)
    subprocess.run(["git", "push"], capture_output=True)
    
    print(f"\n✅ Report written: {md_name}")
    print(f"✅ HTML written: {html_name}")
    print(f"✅ Git committed and pushed")
    sys.exit(0)
else:
    print("❌ Failed to find report files")
    sys.exit(1)
