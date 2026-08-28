#!/usr/bin/env python3
"""
research_to_video.py — chain the deep-research skill into infographic-show.

Given a topic this script:
  1. Runs the deep-research skill's deep_research.py to collect data -> research_data.json
     (Phases 1-3: query, scrape, synthesize structured themes/items).
  2. Reads research_data.json (themes + all_items).
  3. Builds a scenes.json — one scene per well-being theme, where each scene's
     narration is derived from the research (the research summary IS the script).
  4. Invokes generate_video.py to rasterize + narrate + stitch the MP4.

Two modes:
  * Automated: synthesize narration straight from the research themes/items.
  * Crafted:   pass --script scenes_plan.json for higher-quality narration.

Usage:
  # Automated (works for ANY topic):
  python3 scripts/research_to_video.py "how to become a better person" --output show.mp4

  # Crafted narration for this topic (higher quality):
  python3 scripts/research_to_video.py "how to become a better person" \
      --script scenes_plan.json --output how_to_better.mp4

Dependencies: the deep-research skill, ffmpeg, and the infographic-show venv
(cairosvg; optionally kokoro_onnx + soundfile). Run with the skill's venv:

  ~/.venvs/infographic-show/bin/python scripts/research_to_video.py "..."
"""
import json, os, re, sys, subprocess, shutil, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Known locations of the deep-research skill's collector script (searched in order).
DEEP_SEARCH_CANDIDATES = [
    Path(os.path.expanduser("~/.hermes/skills/research/deep-research/deep_research.py")),
    Path(__file__).resolve().parent.parent.parent / "research" / "deep-research" / "deep_research.py",
    Path(os.path.expanduser("~/.nanobot/workspace/git_clone_dir/personal_bot/skills/deep-research/deep_research.py")),
]


def _find_deep_research():
    for c in DEEP_SEARCH_CANDIDATES:
        if c.is_file():
            return c
    raise FileNotFoundError("deep_research.py not found in any known location.")


def _clean(text):
    """Strip tags/whitespace and return a tidy string."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def _run_deep_research(topic, work_dir):
    """Copy deep_research.py into work_dir and run it so research_data.json lands there."""
    src = _find_deep_research()
    dest = work_dir / "deep_research.py"
    shutil.copy2(src, dest)
    log = (work_dir / "research_run.log").open("w")
    p = subprocess.run(
        [sys.executable, "-u", str(dest), topic],
        stdout=log, stderr=subprocess.STDOUT, timeout=900,
    )
    if p.returncode != 0:
        raise RuntimeError(f"deep_research.py exited {p.returncode}; see research_run.log")
    rd = work_dir / "research_data.json"
    if not rd.is_file():
        raise FileNotFoundError("deep_research.py did not produce research_data.json.")
    return json.loads(rd.read_text(encoding="utf-8"))


def _synth_narration(theme_key, items):
    """Synthesize narration from research items (fallback when no --script)."""
    labels = {
        "definition": "What it actually means",
        "evolution": "How it unfolds over time",
        "mechanics": "What makes it work",
        "challenges": "The things that mediate it",
        "applications": "How to apply it",
        "future": "Where it's heading",
        "expert_views": "What experts agree on",
    }
    label = labels.get(theme_key, theme_key.replace("_", " ").title())
    narration = ""
    if items:
        first = _clean(items[0].get("content", items[0].get("title", "")))
        parts = re.split(r"(?<=[.!?])\s+", first)
        narration = " ".join(parts[:2]).strip()
    if not narration:
        narration = f"Understanding {label.lower()} is a key part of becoming a better person."
    return label, narration


def build_card(title, subtitle, bullets, accent, idx, n):
    """Render a self-contained 1920x1080 SVG scene card (reuses the infographic-show look)."""
    accent = accent or "#7c3aed"

    def esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    items = ""
    y = 380
    for b in (bullets or []):
        items += (
            f'  <rect x="660" y="{y}" width="24" height="24" fill="{accent}" rx="12"/>\n'
            f'  <text x="705" y="{y + 19}" font-family="Helvetica" font-size="30" fill="#e9d5ff">'
            f"{esc(b)}</text>\n"
        )
        y += 92
    counter = f"{idx:02d} / {n:02d} / {n:02d}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" style="stop-color:#1a0a2e"/><stop offset="100%" style="stop-color:#3d1e6d"/>
  </linearGradient></defs>
  <rect width="1920" height="1080" fill="url(#bg)"/>
  <circle cx="220" cy="160" r="320" fill="{accent}" opacity="0.25"/>
  <circle cx="1700" cy="920" r="260" fill="{accent}" opacity="0.18"/>
  <rect x="80" y="46" width="90" height="5" fill="{accent}" rx="2"/>
  <text x="960" y="470" font-family="'Helvetica Neue',Helvetica,Arial" font-size="76" fill="#ffffff" font-weight="800" text-anchor="middle">{esc(title)}</text>
  <rect x="720" y="542" width="480" height="5" fill="{accent}" rx="2"/>
  <text x="960" y="624" font-family="'Helvetica Neue',Helvetica,Arial" font-size="34" fill="#c4b5fd" text-anchor="middle">{esc(subtitle)}</text>
  {items}
  <text x="1855" y="1050" font-family="Helvetica" font-size="22" fill="#c4b5fd" text-anchor="end">{counter}</text>
</svg>'''


def build_scenes_from_research(rd):
    """Build scenes.json by synthesizing narration from research themes."""
    themes = rd.get("themes", {})
    n = len(themes)
    scenes = []
    idx = 0
    for key, items in themes.items():
        label, narration = _synth_narration(key, items)
        bullets = [_clean(i.get("title", "")) or _clean(i.get("content", ""))[:80]
                   for i in items[:4]]
        svg = build_card(label, "Research summary", bullets, "#8b5cf6", idx + 1, n)
        scenes.append({"type": "svg", "title": label, "subtitle": "Research summary",
                       "svg": svg, "narration": narration})
        idx += 1
    return {"title": rd.get("topic", "Research show"), "theme": "purple",
            "scenes": scenes}


def build_scenes_from_plan(plan):
    """Build scenes.json from a hand-crafted plan (higher quality)."""
    n = len(plan.get("scenes", []))
    scenes = []
    for i, s in enumerate(plan.get("scenes", [])):
        svg = build_card(
            s.get("title", ""), s.get("subtitle", ""), s.get("bullets", []),
            s.get("accent", "#8b5cf6"), i + 1, n,
        )
        scenes.append({"type": "svg", "title": s.get("title", ""),
                       "subtitle": s.get("subtitle", ""), "svg": svg,
                       "narration": s.get("narration", "")})
    out = dict(plan)
    out["scenes"] = scenes
    return out


def main():
    import argparse
    p = argparse.ArgumentParser(description="Research a topic and generate a narrated infographic video.")
    p.add_argument("topic", help="The topic to research, e.g. 'how to become a better person'")
    p.add_argument("--output", "-o", default="infographic_show.mp4")
    p.add_argument("--script", "-c", help="Hand-crafted scenes_plan.json for high-quality narration")
    p.add_argument("--work-dir", "-w", help="Keep the working directory for debugging")
    a = p.parse_args()

    work_dir = Path(a.work_dir) if a.work_dir else Path(tempfile.mkdtemp(prefix="r2v_"))
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Researching: {a.topic}")
    rd = _run_deep_research(a.topic, work_dir)

    if a.script:
        plan = json.loads(Path(a.script).read_text(encoding="utf-8"))
        data = build_scenes_from_plan(plan)
        mode = "crafted"
    else:
        data = build_scenes_from_research(rd)
        mode = "auto"

    scenes_out = work_dir / "scenes.json"
    scenes_out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  Wrote {len(data['scenes'])} scenes ({mode}) -> {scenes_out}")

    # Invoke generate_video.py from the skill.
    gen = HERE / "generate_video.py"
    keep = bool(a.work_dir)
    render_dir = Path(a.work_dir) if keep else work_dir / "render"
    cmd = [sys.executable, gen, "-s", str(scenes_out), "-o", a.output,
           "--work-dir", str(render_dir)]
    r = subprocess.run(cmd)
    sys.exit(0 if r.returncode == 0 else 1)


if __name__ == "__main__":
    main()
