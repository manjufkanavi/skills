#!/usr/bin/env python3
"""
kannada-reel — 60-second vertical Kannada trending reel orchestrator.

Pipeline:
  Trends → Deep Research → Kannada Script → TTS Audio → Cinematographer (12 prompts)
  → 12×5s Video Clips (FastMetal-QAD) → Stitch & Sync → Telegram

Usage:
  python3 main.py --stage all --topic "Topic"
  python3 main.py --stage trends
  python3 main.py --stage research --topic "Topic"
  python3 main.py --stage script --research-dir "reports/slug-ts/" --topic "ಟಾಪಿಕ್"
  python3 main.py --stage tts --script-file "script.md" --output "narration.wav"
  python3 main.py --stage cinematographer --script-file "script.md" --topic "ಟಾಪಿಕ್"
  python3 main.py --stage video --prompts-file "prompts.md" --output-dir "clips/"
  python3 main.py --stage stitch --clips-dir "clips/" --audio "narration.wav" --output "final_reel.mp4"
  python3 main.py --stage telegram --video "final_reel.mp4"
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ─── Paths ───────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).resolve().parent
WORKSPACE = SKILL_DIR.parent.parent.parent  # personal_bot root
SKILLS_DIR = WORKSPACE / "skills"

# Fallback: sub-skills may live in personal_bot repo or ~/.hermes/skills/
PERSONAL_BOT_SKILLS = Path.home() / ".nanobot" / "workspace" / "git_clone_dir" / "personal_bot" / "skills"
HERMES_SKILLS = Path.home() / ".hermes" / "skills"

# Sub-skill paths — try SKILLS_DIR, then personal_bot repo, then ~/.hermes/skills/
def _skill_path(*parts):
    for base in [SKILLS_DIR, PERSONAL_BOT_SKILLS, HERMES_SKILLS]:
        candidate = base.joinpath(*parts)
        if candidate.exists():
            return candidate
    # Return first candidate so error is clear
    return SKILLS_DIR.joinpath(*parts)

TRENDING_SCRIPT = _skill_path("whats-trending", "scripts", "trending.py")
DEEP_RESEARCH_SCRIPT = _skill_path("deep-research", "deep_research.py")
KANNADA_TTS_SCRIPT = _skill_path("kannada-tts", "scripts", "synthesize.py")
VIDEO_GEN_SCRIPT = _skill_path("creative", "video-generation", "scripts", "generate_video.py")

# Output directories
CLIPS_DIR = SKILL_DIR / "clips"
OUTPUTS_DIR = SKILL_DIR / "outputs"
REELS_DIR = OUTPUTS_DIR / "reels"  # NEW: one isolated directory per reel

# Default Telegram target (override with --telegram-target)
DEFAULT_TELEGRAM_TARGET = "telegram:Konnichiwa Arigato (dm)"

CLIPS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
REELS_DIR.mkdir(parents=True, exist_ok=True)

# Constants
NUM_CLIPS = 12
CLIP_DURATION = 5  # seconds per clip
TOTAL_DURATION = NUM_CLIPS * CLIP_DURATION  # 60s
TARGET_WORDS = 70  # ~60s at 1.15 words/sec Kannada pace


# ─── Progress Bar ────────────────────────────────────────────────────

def progress_bar(current, total, prefix="", width=30):
    """Print a progress bar."""
    pct = current / total
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    sys.stdout.write(f"\r  {prefix}[{bar}] {current}/{total} ({pct:.0%})  ")
    if current >= total:
        sys.stdout.write("\n")
    sys.stdout.flush()


# ─── Stage 1: Trends ─────────────────────────────────────────────────

def stage_trends(trends_dir: str) -> dict:
    """Fetch trending topics and return a summary dict."""
    trends_path = Path(trends_dir)
    trends_path.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("  STAGE 1: Fetching Trending Topics")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, str(TRENDING_SCRIPT), "--output", str(trends_path)],
        capture_output=True, text=True, timeout=60,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"  ⚠ trends script error: {result.stderr}", file=sys.stderr)
        return {}

    summary = {}
    for cat_file in ["world_trends.json", "india_trends.json",
                     "karnataka_trends.json", "karnataka_dork_trends.json"]:
        fp = trends_path / cat_file
        if fp.exists():
            data = json.loads(fp.read_text(encoding="utf-8"))
            label = data.get("label", cat_file.replace("_trends.json", "").title())
            trends = data.get("trends", [])
            items = []
            for t in trends[:10]:
                items.append({
                    "title": t.get("title", ""),
                    "snippet": t.get("snippet", ""),
                })
            summary[label] = items

    return summary


def print_trends_summary(summary: dict):
    """Pretty-print trending summary for user."""
    print("\n" + "=" * 60)
    print("  📊 TRENDING TOPICS SUMMARY")
    print("=" * 60)
    for category, items in summary.items():
        print(f"\n  [{category}]")
        for i, item in enumerate(items, 1):
            snippet = item["snippet"][:80] + "…" if len(item["snippet"]) > 80 else item["snippet"]
            print(f"    {i}. {item['title']}")
            if snippet:
                print(f"       {snippet}")
    print("\n" + "=" * 60)


# ─── Stage 2: Deep Research ──────────────────────────────────────────

def stage_research(topic: str) -> str:
    """Run deep research on topic and return report directory path."""
    print("\n" + "=" * 60)
    print("  STAGE 2: Deep Research")
    print(f"  Topic: {topic}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, str(DEEP_RESEARCH_SCRIPT), topic],
        capture_output=True, text=True, timeout=600,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"  ⚠ Deep research error: {result.stderr}", file=sys.stderr)
        return ""

    # Deep-research saves synthesized data to skills/deep-research/data/synthesized/<topic>/
    syn_base = PERSONAL_BOT_SKILLS / "deep-research" / "data" / "synthesized"
    if syn_base.exists():
        subdirs = sorted(
            [d for d in syn_base.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime, reverse=True
        )
        if subdirs:
            latest = subdirs[0]
            print(f"\n  ✅ Research data saved in: {latest}")
            return str(latest)

    # Fallback: check personal_bot/deep-research/reports for HTML slideshows
    reports_dir = WORKSPACE / "personal_bot" / "deep-research" / "reports"
    if reports_dir.exists():
        html_files = sorted(
            reports_dir.glob("*.html"),
            key=lambda f: f.stat().st_mtime, reverse=True
        )
        if html_files:
            latest = html_files[0]
            print(f"\n  ✅ Research slideshow saved in: {latest}")
            return str(latest)

    print("  ⚠ No research output found", file=sys.stderr)
    return ""


# ─── Stage 3: Kannada Script (60s target) ────────────────────────────

def stage_script(research_dir: str, output_dir: str, kannada_title: str = "") -> str:
    """Write a 60s Kannada reel script (~65-75 words) via agy CLI."""
    print("\n" + "=" * 60)
    print("  STAGE 3: Kannada Script (60s target)")
    print("=" * 60)

    research_path = Path(research_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Find report content
    report_text = ""
    report_name = ""

    rd_json = research_path / "report_data.json"
    if rd_json.exists():
        try:
            data = json.loads(rd_json.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                report_text = json.dumps(data, ensure_ascii=False, indent=2)
                report_name = "report_data.json"
        except Exception:
            pass

    if not report_text:
        md_files = sorted(research_path.glob("*.md"))
        if md_files:
            report_text = md_files[0].read_text(encoding="utf-8")
            report_name = md_files[0].name

    if not report_text:
        json_files = sorted(research_path.glob("*.json"))
        if json_files:
            report_text = json_files[0].read_text(encoding="utf-8")
            report_name = json_files[0].name

    if not report_text:
        print("  ⚠ No report content found in research directory", file=sys.stderr)
        return ""

    print(f"  📄 Report: {report_name} ({len(report_text)} chars)")

    # Truncate for agy
    if len(report_text) > 6000:
        print("  ⚠ Report is long; truncating to first 5000 chars")
        report_text = report_text[:5000] + "\n\n[...truncated...]"

    if not kannada_title:
        kannada_title = "ಟ್ರೆಂಡಿಂಗ್ ವಿಷಯ"

    agy_prompt = f"""<think>
You are a Kannada reel scriptwriter for short-form video (60 seconds).
You write energetic, punchy Kannada scripts for Instagram Reels / YouTube Shorts.
Your tone is fast, conversational, and engaging — like a young news influencer.

Write a KANNADA REEL SCRIPT about: {kannada_title}

This is for a 60-second reel with 12 video clips (5 seconds each).
The visuals are B-ROLL — relevant footage matching what the narrator says.
Keep it TIGHT and structured for visual cuts.

STRUCTURE:

**1. HOOK (clips 1-2, ~10s):**
Start with "ಹೇ ಹೇ!" or "ಏನ್ ಗೊತ್ತಾ?" — a catchy, energetic opener that grabs attention
in the first 2 seconds. Make it topic-specific, not generic.

**2. MAIN POINTS (clips 3-10, ~40s):**
- 8 quick points, one per 5-second clip
- Each point is 1 short sentence
- Use Gen-Z Kannada: "ಅದ್ಭುತ", "ಖುಷಿ", "ನೋಡಿ", "ಅಲ್ವಾ?"
- Fast, punchy delivery — write for the ear
- Each point should map to a distinct visual scene (B-roll, not a talking head)

**3. SIGN-OFF (clips 11-12, ~10s):**
Quick wrap-up + "ಫಾಲೋ ಮಾಡಿ!" or similar CTA.

SOURCE MATERIAL:
---
{report_text}
---

IMPORTANT RULES:
- TOTAL: ~65-75 words ONLY (this is a 60-second reel!)
- Spoken-word style, not written article
- Energetic tone, conversational Kannada
- Each point should be visually describable as B-roll footage
- Output ONLY the Kannada script — no explanations, no metadata, no numbering
"""

    translated = ""
    try:
        proc = subprocess.run(
            ["agy", "--model", "gemini-3.1-pro-high", "--effort", "high", "--print", agy_prompt],
            capture_output=True, text=False, timeout=300,
        )
        translated = proc.stdout.decode("utf-8").strip() if proc.stdout else ""
        if not translated:
            translated = proc.stderr.decode("utf-8").strip() if proc.stderr else ""
            if not translated or "error" in translated.lower():
                print("  ⚠ agy returned empty, using fallback...")
                translated = _fallback_script(report_text, kannada_title)

    except FileNotFoundError:
        print("  ⚠ agy CLI not found, using fallback...")
        translated = _fallback_script(report_text, kannada_title)
    except subprocess.TimeoutExpired:
        print("  ⚠ agy timed out, using fallback...")
        translated = _fallback_script(report_text, kannada_title)

    if not translated:
        print("  ❌ Script generation failed entirely", file=sys.stderr)
        return ""

    translated = translated.strip()
    # Strip code fences if present
    if translated.startswith("```"):
        translated = re.sub(r"^```[a-zA-Z]*\n?", "", translated)
        translated = re.sub(r"\n?```$", "", translated)

    # Save
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = out_path / f"reel_script_{ts}.md"
    out_file.write_text(translated, encoding="utf-8")

    word_count = len(translated.split())
    print(f"\n  ✅ Kannada script saved: {out_file}")
    print(f"     ({len(translated)} chars, ~{word_count} words)")
    if word_count > 90:
        print("  ⚠ Script is longer than ideal for a 60s reel (target 65-75 words)")
    return str(out_file)


def _fallback_script(report_text: str, kannada_title: str) -> str:
    """Fallback script generation using google-genai directly."""
    try:
        from google import genai
        client = genai.Client()
        prompt = f"""Write a short (~65-75 words) energetic Kannada reel script about: {kannada_title}
Hook → 8 quick points → sign-off. Spoken-word style, Gen-Z Kannada. Output only the script.

Source: {report_text[:3000]}"""
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return resp.text.strip()
    except Exception as e:
        print(f"  ⚠ Fallback script also failed: {e}", file=sys.stderr)
        return ""


# ─── Stage 4: TTS Audio (kannada-tts skill) ──────────────────────────

def stage_tts(script_file: str, output: str, speaker: str = "female", device: str = "mps") -> str:
    """Generate Kannada TTS audio using kannada-tts skill."""
    print("\n" + "=" * 60)
    print("  STAGE 4: TTS Audio (kannada-tts)")
    print("=" * 60)

    if not os.path.isfile(script_file):
        print(f"  ❌ Script file not found: {script_file}", file=sys.stderr)
        return ""

    script_text = Path(script_file).read_text(encoding="utf-8")
    print(f"  📄 Script: {len(script_text.split())} words")

    # Run kannada-tts (use venv Python for Coqui TTS)
    tts_venv = PERSONAL_BOT_SKILLS / "kannada-tts" / "venv" / "bin" / "python"
    if tts_venv.exists():
        tts_python = str(tts_venv)
    else:
        tts_python = sys.executable
    cmd = [
        tts_python, str(KANNADA_TTS_SCRIPT),
        "--text-file", script_file,
        "--speaker", speaker,
        "--output", output,
        "--device", device,
    ]

    print(f"  🎙️  Running TTS: {' '.join(cmd)}")
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    elapsed = time.time() - start_time

    if result.returncode != 0:
        print(f"  ⚠ TTS error: {result.stderr}", file=sys.stderr)
        return ""

    if os.path.isfile(output):
        size_mb = os.path.getsize(output) / (1024 * 1024)
        print(f"\n  ✅ TTS audio saved: {output} ({size_mb:.1f} MB, {elapsed:.1f}s)")
        return output
    else:
        print("  ❌ TTS output file not found", file=sys.stderr)
        return ""


# ─── Stage 5: Cinematographer (12 Visual Prompts) ────────────────────

def stage_cinematographer(script_file: str, output_dir: str, topic: str = "") -> str:
    """Generate 12 visually continuous video prompts via agy CLI."""
    print("\n" + "=" * 60)
    print("  STAGE 5: Cinematographer (12 Visual Prompts)")
    print("=" * 60)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    script_text = Path(script_file).read_text(encoding="utf-8")
    print(f"  📄 Script: {len(script_text.split())} words")

    if not topic:
        topic = "trending topic"

    agy_prompt = f"""<think>
You are a cinematographer creating a 60-second vertical (9:16) social media reel.
The reel has exactly 12 segments of 5 seconds each.
You must create 12 B-ROLL visual prompts that maintain STRICT VISUAL CONTINUITY.

CRITICAL: These are B-ROLL clips — NOT a talking head. Each clip shows RELEVANT SCENES
that match what the narrator is saying. The viewer sees the story through visuals,
not a presenter.

CRITICAL CONTINUITY RULES:
1. SAME STYLE: Consistent cinematic look — professional film quality throughout
2. SAME COLOR GRADING: Warm tones, vibrant colors, consistent grading
3. SAME LIGHTING: Golden-hour / natural daylight throughout
4. SAME ASPECT: Vertical 9:16, modern social-media reel aesthetic
5. PROGRESSIVE SHOTS: Wide → Medium → Close-up → Medium → Wide (cycle through)
6. TOPIC-RELEVANT: Each scene shows what the script line describes — NOT a person talking
7. NO TALKING HEADS: No presenters, no podcaster, no talking faces

SCRIPT (each line = one 5s clip):
{script_text}

TOPIC: {topic}

Create exactly 12 visual prompts, one per line, numbered 1-12.
Each prompt describes a distinct B-ROLL scene matching the script line.
Be specific about what the viewer sees — locations, objects, actions, people in context.

Output ONLY the 12 prompts, one per line, no extra text.
"""

    prompts_text = ""
    try:
        proc = subprocess.run(
            ["agy", "--model", "gemini-3.1-pro-high", "--effort", "high", "--print", agy_prompt],
            capture_output=True, text=False, timeout=300,
        )
        prompts_text = proc.stdout.decode("utf-8").strip() if proc.stdout else ""
        if not prompts_text:
            prompts_text = proc.stderr.decode("utf-8").strip() if proc.stderr else ""
            if not prompts_text or "error" in prompts_text.lower():
                raise ValueError("agy returned empty")
    except Exception as e:
        print(f"  ⚠ agy cinematographer failed ({e}), using fallback prompts")
        prompts_text = _fallback_prompts(topic)

    # Parse into list
    lines = [l.strip() for l in prompts_text.split("\n") if l.strip()]
    prompts = []
    for line in lines:
        line = re.sub(r"^\d+[\.\\)]\s*", "", line).strip()
        if line and not line.startswith("```"):
            prompts.append(line)

    # Ensure exactly 12
    while len(prompts) < 12:
        prompts.append(f"Teenage podcaster continuing the story about {topic}, vertical 9:16, energetic reel style")
    prompts = prompts[:12]

    # Save
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = out_path / f"reel_prompts_{ts}.md"
    out_file.write_text("\n".join(prompts), encoding="utf-8")

    print(f"\n  ✅ Cinematographer prompts saved: {out_file}")
    for i, p in enumerate(prompts, 1):
        print(f"     {i}. {p[:80]}...")
    return str(out_file)


def _fallback_prompts(topic: str) -> str:
    """Fallback 12 B-roll prompts with visual continuity."""
    base_style = "vertical 9:16, cinematic, golden-hour natural lighting, warm vibrant colors, professional film quality, social-media reel aesthetic"
    return "\n".join([
        f"Establishing wide shot of the location related to '{topic}', aerial perspective showing the full scene, {base_style}",
        f"Medium shot of people involved in the story about '{topic}', natural candid moment, {base_style}",
        f"Close-up of key objects or details related to '{topic}', shallow depth of field, {base_style}",
        f"Medium shot showing action or development related to '{topic}', dynamic composition, {base_style}",
        f"Close-up revealing an important fact about '{topic}', dramatic lighting, {base_style}",
        f"Medium shot of the ongoing situation about '{topic}', natural daylight, {base_style}",
        f"Wide shot showing the scale or impact of '{topic}', expansive composition, {base_style}",
        f"Close-up of relevant details about '{topic}', focused framing, {base_style}",
        f"Medium shot showing people reacting to '{topic}', authentic moment, {base_style}",
        f"Close-up building tension about '{topic}', intense lighting, {base_style}",
        f"Medium shot wrapping up the story about '{topic}', confident composition, {base_style}",
        f"Wide shot concluding with a call to action about '{topic}', inviting composition, {base_style}",
    ])


# ─── Stage 6: Video Generation (FastMetal-QAD) ───────────────────────

def stage_video(prompts_file: str, output_dir: str, model: str = "1.3b") -> bool:
    """Generate 12 × 5s video clips using FastMetal-QAD."""
    print("\n" + "=" * 60)
    print("  STAGE 6: Video Generation (FastMetal-QAD)")
    print(f"  Model: {model} | Clips: {NUM_CLIPS} × {CLIP_DURATION}s")
    print("=" * 60)

    if not os.path.isfile(prompts_file):
        print(f"  ❌ Prompts file not found: {prompts_file}", file=sys.stderr)
        return False

    prompts_text = Path(prompts_file).read_text(encoding="utf-8")
    prompts = [l.strip() for l in prompts_text.split("\n") if l.strip()]
    prompts = [re.sub(r"^\d+[\.\\)]\s*", "", p).strip() for p in prompts]
    prompts = [p for p in prompts if p and not p.startswith("```")]

    # Ensure exactly 12
    while len(prompts) < NUM_CLIPS:
        prompts.append(f"Visual scene continuing the story, vertical 9:16, modern reel style")
    prompts = prompts[:NUM_CLIPS]

    print(f"\n  🎬 {len(prompts)} prompts loaded")

    # Generate clips
    clips_dir = Path(output_dir)
    clips_dir.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    for i, prompt in enumerate(prompts, 1):
        progress_bar(i - 1, NUM_CLIPS, "Generating")
        print(f"\n  🎥 Clip {i}/{NUM_CLIPS}: {prompt[:60]}...")

        clip_path = clips_dir / f"clip_{i:02d}.mp4"

        # Check if already exists (resume support) — only skip if it's a
        # valid, non-empty clip. A 0-byte or tiny clip from a crashed run is
        # regenerated rather than silently reused. Because each reel now gets
        # its own fresh directory, this only ever resumes within the current
        # reel (crash recovery), never across reels or past sessions.
        if clip_path.exists() and os.path.getsize(clip_path) > 1024:
            print(f"  ⏭️  Clip {i} already exists, skipping")
            clip_paths.append(str(clip_path))
            continue

        # Use video-gen venv Python (has MLX + FastVideo)
        venv_python = Path.home() / ".hermes" / "git_clone_dir" / "personal_bot" / "skills" / "video-gen-venv" / "bin" / "python"
        if venv_python.exists():
            gen_python = str(venv_python)
        else:
            gen_python = sys.executable

        cmd = [
            gen_python, str(VIDEO_GEN_SCRIPT),
            "--prompt", prompt,
            "--model", model,
            "--output-dir", str(clips_dir),
            "--clip-index", str(i),
        ]

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        elapsed = time.time() - start_time

        if result.returncode != 0:
            print(f"  ⚠ Clip {i} generation failed: {result.stderr[:200]}", file=sys.stderr)
            # Try with a simpler prompt
            print(f"  🔄 Retrying with simplified prompt...")
            simple_prompt = f"Modern social media reel style, vertical 9:16, {prompt[:100]}"
            cmd = [
                gen_python, str(VIDEO_GEN_SCRIPT),
                "--prompt", simple_prompt,
                "--model", model,
                "--output-dir", str(clips_dir),
                "--clip-index", str(i),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                print(f"  ❌ Clip {i} generation failed even with simplified prompt", file=sys.stderr)
                return False

        # Find the generated clip
        if clip_path.exists():
            clip_paths.append(str(clip_path))
            print(f"  ✅ Clip {i} saved: {clip_path} ({elapsed:.1f}s)")
        else:
            # Try to find any new mp4 in the directory
            new_clips = sorted(clips_dir.glob("clip_*.mp4"))
            if new_clips:
                latest = new_clips[-1]
                clip_paths.append(str(latest))
                print(f"  ✅ Clip {i} saved: {latest} ({elapsed:.1f}s)")
            else:
                print(f"  ❌ Clip {i} output not found", file=sys.stderr)
                return False

    # Final progress
    progress_bar(NUM_CLIPS, NUM_CLIPS, "Generating")
    print(f"\n  ✅ All {len(clip_paths)} clips generated in {clips_dir}")
    return True


# ─── Stage 7: Stitch & Sync (ffmpeg) ─────────────────────────────────

def stage_stitch(clips_dir: str, audio: str, output: str) -> bool:
    """Concatenate clips with crossfade, sync audio, trim to 60s."""
    print("\n" + "=" * 60)
    print("  STAGE 7: Stitch & Sync (ffmpeg)")
    print("=" * 60)

    clips_path = Path(clips_dir)
    if not clips_path.exists():
        print(f"  ❌ Clips directory not found: {clips_dir}", file=sys.stderr)
        return False

    # Get sorted clip files
    clip_files = sorted(clips_path.glob("clip_*.mp4"))
    if not clip_files:
        print("  ❌ No clip files found", file=sys.stderr)
        return False

    print(f"  📹 Found {len(clip_files)} clips")

    # Step 1: Create concat list with absolute paths
    concat_list = clips_path / "concat_list.txt"
    with open(concat_list, "w") as f:
        for cf in clip_files:
            f.write(f"file '{cf.resolve()}'\n")

    # Step 2: Concatenate clips via demuxer
    stitched = clips_path / "stitched.mp4"
    print("  🎞️  Concatenating clips...")

    # Simple concat via demuxer (re-encode for compatibility)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-r", "16",
        "-pix_fmt", "yuv420p",
        str(stitched),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  ❌ Concat failed: {result.stderr[:200]}", file=sys.stderr)
        return False

    print(f"  ✅ Clips concatenated: {stitched}")

    # Step 3: Sync audio with video
    print("  🎵 Syncing audio with video...")
    if os.path.isfile(audio):
        cmd = [
            "ffmpeg", "-y",
            "-i", str(stitched),
            "-i", audio,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.isfile(output):
            print(f"  ✅ Audio synced: {output}")
        else:
            print(f"  ⚠ Audio sync failed, using video only: {result.stderr[:200]}", file=sys.stderr)
            # Fallback: just copy stitched
            subprocess.run(["cp", str(stitched), output], check=False)
    else:
        print(f"  ⚠ Audio file not found: {audio}, using video only")
        subprocess.run(["cp", str(stitched), output], check=False)

    # Step 4: Trim to exact 60s if needed
    if os.path.isfile(output):
        size_mb = os.path.getsize(output) / (1024 * 1024)
        print(f"\n  ✅ Reel assembled: {output} ({size_mb:.1f} MB)")

        # Check duration
        dur_result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", output],
            capture_output=True, text=True, timeout=30,
        )
        if dur_result.returncode == 0:
            duration = float(dur_result.stdout.strip())
            print(f"  ⏱️  Duration: {duration:.1f}s")
            if duration > TOTAL_DURATION + 1:
                print(f"  ✂️  Trimming to {TOTAL_DURATION}s...")
                trim_cmd = [
                    "ffmpeg", "-y", "-i", output,
                    "-t", str(TOTAL_DURATION),
                    "-c", "copy",
                    output,
                ]
                subprocess.run(trim_cmd, capture_output=True, text=True, timeout=60)
                print(f"  ✅ Trimmed to {TOTAL_DURATION}s")

        return True
    else:
        print("  ❌ Output reel not found", file=sys.stderr)
        return False


# ─── Stage 8: Send to Telegram ───────────────────────────────────────

def stage_telegram(video: str, target: str = DEFAULT_TELEGRAM_TARGET) -> bool:
    """Send the final reel to Telegram — MANDATORY.

    Returns True only if the video was actually delivered. On any failure,
    writes a DELIVERY.txt next to the reel containing the exact
    send_message command and the absolute file path, so the video can be
    delivered manually. Never silently "succeeds" while the video is missing.
    """
    print("\n" + "=" * 60)
    print("  STAGE 8: Send to Telegram (MANDATORY)")
    print("=" * 60)

    if not os.path.isfile(video):
        print(f"  ❌ Video file not found: {video}", file=sys.stderr)
        return False

    size_mb = os.path.getsize(video) / (1024 * 1024)
    print(f"  📹 Video: {video} ({size_mb:.1f} MB)")

    delivered = False
    try:
        from hermes_tools import send_message
        print(f"\n  📤 Sending to Telegram ({target})...")
        send_message(
            target=target,
            message=f"🎬 **Kannada Reel Ready!**\n\n📹 Duration: ~60s | Size: {size_mb:.1f} MB",
            media=[video],
        )
        delivered = True
        print("  ✅ Delivered to Telegram!")
    except ImportError:
        print("  ⚠ hermes_tools not available in this context")
    except Exception as e:
        print(f"  ⚠ Telegram send failed: {e}")

    if not delivered:
        # MANDATORY fallback: record exact delivery instructions next to the reel.
        reel_dir = Path(video).parent
        delivery_file = reel_dir / "DELIVERY.txt"
        delivery_file.write_text(
            f"MANDATORY: Deliver this video to Telegram.\n"
            f"VIDEO:{video}\n"
            f"SIZE:{size_mb:.1f}MB\n"
            f"TARGET:{target}\n\n"
            f"Run in the agent session:\n"
            f"send_message(target='{target}', media=['{video}'])\n",
            encoding="utf-8",
        )
        print(f"  📝 Wrote delivery instructions to {delivery_file}")
        print(f"  📱 MANUAL SEND REQUIRED: send_message(target='{target}', media=['{video}'])")
    return delivered


def _slugify(text: str) -> str:
    """Convert topic string to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")


def _new_reel_dir(topic: str) -> Path:
    """Create and return a fresh, isolated directory for one reel run.

    Path: reels/<topic-slug>-<timestamp-with-fmicroseconds>/

    Every new reel gets its own directory so its clips, script, prompts,
    audio, and final MP4 never collide with — or get reused from — other
    reels or past sessions. This is the fix for stale-clip reuse: because
    each reel starts in an empty directory, all 12 clips are generated
    fresh for the current topic instead of reusing old ones.
    """
    slug = _slugify(topic) or "topic"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    reel_dir = REELS_DIR / f"{slug}-{ts}"
    # Guard against same-second collisions.
    n = 1
    candidate = reel_dir
    while candidate.exists():
        candidate = REELS_DIR / f"{slug}-{ts}-{n}"
        n += 1
    reel_dir = candidate
    reel_dir.mkdir(parents=True, exist_ok=True)
    (reel_dir / "clips").mkdir(parents=True, exist_ok=True)
    (reel_dir / "script").mkdir(parents=True, exist_ok=True)
    (reel_dir / "prompts").mkdir(parents=True, exist_ok=True)
    return reel_dir


def stage_all(topic: str, output: str = None, speaker: str = "female", device: str = "mps",
              model: str = "1.3b", telegram_target: str = DEFAULT_TELEGRAM_TARGET):
    """Run all 8 stages sequentially into a fresh, isolated per-reel directory."""
    print("\n" + "=" * 60)
    print("  KANNADA-REEL — FULL PIPELINE (60s)")
    print(f"  Topic: {topic}")
    print(f"  Model: {model} | Speaker: {speaker} | Device: {device}")
    print("=" * 60)

    # Stage 1: Trends — fetch and let user pick
    print("\n  📌 Stage 1: Fetching Trending Topics")
    trends_dir = SKILL_DIR / "trending_data"
    summary = stage_trends(str(trends_dir))
    if summary:
        print_trends_summary(summary)
        print("\n  Pick a topic number (or press Enter to use current):")
        print(f"    Current: {topic}")
        try:
            choice = input("  → ").strip()
            if choice:
                # Try to match by number
                if choice.isdigit():
                    idx = int(choice) - 1
                    categories = list(summary.keys())
                    cat_idx = 0
                    for cat in categories:
                        items = summary[cat]
                        if idx < len(items):
                            topic = items[idx]["title"]
                            print(f"  ✅ Selected: {topic}")
                            break
                        idx -= len(items)
                else:
                    topic = choice
                    print(f"  ✅ Using custom topic: {topic}")
        except (EOFError, KeyboardInterrupt):
            print("  ⏭️  Using pre-selected topic")

    # Create a fresh, isolated per-reel directory.
    # Each reel gets its own directory (reels/<slug>-<timestamp>/) so its clips,
    # script, prompts, audio, and final MP4 never collide with — or get reused
    # from — other reels or past sessions. This is what prevents stale clips
    # from a previous session from being silently reused for a new topic.
    reel_dir = _new_reel_dir(topic)
    clips_dir = reel_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    script_dir = reel_dir / "script"
    prompts_dir = reel_dir / "prompts"
    audio_file = reel_dir / "narration.wav"
    if output is None or output == str(OUTPUTS_DIR / "final_reel.mp4"):
        output = str(reel_dir / "final_reel.mp4")
    print(f"\n  📁 Fresh per-reel directory: {reel_dir}")

    # Stage 2: Research
    print("\n  📌 Stage 2: Deep Research")
    time.sleep(1)
    research_dir = stage_research(topic)
    if not research_dir:
        print("  ❌ Research failed, aborting.", file=sys.stderr)
        return False

    # Stage 3: Script
    print("\n  📌 Stage 3: Kannada Script")
    time.sleep(1)
    script_file = stage_script(research_dir, str(script_dir), topic)
    if not script_file:
        print("  ❌ Script generation failed, aborting.", file=sys.stderr)
        return False

    # Stage 4: TTS
    print("\n  📌 Stage 4: TTS Audio")
    time.sleep(1)
    audio_file = stage_tts(script_file, str(audio_file), speaker, device)
    if not audio_file:
        print("  ❌ TTS generation failed, aborting.", file=sys.stderr)
        return False

    # Stage 5: Cinematographer
    print("\n  📌 Stage 5: Cinematographer (12 Prompts)")
    time.sleep(1)
    prompts_file = stage_cinematographer(script_file, str(prompts_dir), topic)
    if not prompts_file:
        print("  ❌ Cinematographer failed, aborting.", file=sys.stderr)
        return False

    # Stage 6: Video Generation — fresh clips in this reel's own dir
    print("\n  📌 Stage 6: Video Generation (12 × 5s clips)")
    time.sleep(1)
    if not stage_video(prompts_file, str(clips_dir), model):
        print("  ❌ Video generation failed, aborting.", file=sys.stderr)
        return False

    # Stage 7: Stitch & Sync
    print("\n  📌 Stage 7: Stitch & Sync")
    time.sleep(1)
    if not stage_stitch(str(clips_dir), audio_file, output):
        print("  ❌ Stitching failed, aborting.", file=sys.stderr)
        return False

    # Stage 8: Telegram — MANDATORY send
    print("\n  📌 Stage 8: Send to Telegram (mandatory)")
    time.sleep(1)
    delivered = stage_telegram(output, telegram_target)

    print("\n" + "=" * 60)
    print("  ✅ KANNADA REEL COMPLETE!")
    print(f"  📹 Reel: {output}")
    if not delivered:
        print("  ⚠️  Telegram did not confirm delivery — see DELIVERY.txt in the reel dir.")
    print("=" * 60)
    return True


# ─── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Kannada Reel — 60s vertical trending reel orchestrator"
    )
    parser.add_argument(
        "--stage",
        choices=["trends", "research", "script", "tts", "cinematographer",
                 "video", "stitch", "telegram", "all"],
        default="trends",
        help="Pipeline stage to run",
    )
    parser.add_argument("--topic", default="", help="Topic (English or Kannada)")
    parser.add_argument("--research-dir", default="", help="Path to research report directory")
    parser.add_argument("--script-file", default="", help="Path to Kannada script file")
    parser.add_argument("--prompts-file", default="", help="Path to cinematographer prompts file")
    parser.add_argument("--clips-dir", "--output-dir", dest="clips_dir", default=str(CLIPS_DIR), help="Path to clips directory")
    parser.add_argument("--audio", default="", help="Path to TTS audio file")
    parser.add_argument("--video", default="", help="Path to video file (for telegram stage)")
    parser.add_argument("--output", default=str(OUTPUTS_DIR / "final_reel.mp4"), help="Output MP4 path")
    parser.add_argument("--speaker", default="female", choices=["female", "male"], help="TTS speaker")
    parser.add_argument("--device", default="mps", choices=["cpu", "cuda", "mps"], help="TTS device")
    parser.add_argument("--model", default="1.3b", choices=["1.3b", "5b"], help="FastMetal model")
    parser.add_argument("--trends-dir", default="trending_data", help="Directory for trending data")
    parser.add_argument("--telegram-target", default=DEFAULT_TELEGRAM_TARGET, help="Telegram target for the mandatory send")

    args = parser.parse_args()

    if args.stage == "trends":
        summary = stage_trends(args.trends_dir)
        print_trends_summary(summary)

    elif args.stage == "research":
        if not args.topic:
            print("  ❌ --topic required for research stage", file=sys.stderr)
            sys.exit(1)
        research_dir = stage_research(args.topic)
        if research_dir:
            print(f"\n  ✅ Research done: {research_dir}")
        else:
            sys.exit(1)

    elif args.stage == "script":
        if not args.research_dir:
            print("  ❌ --research-dir required for script stage", file=sys.stderr)
            sys.exit(1)
        out_dir = OUTPUTS_DIR / "script"
        script_file = stage_script(args.research_dir, str(out_dir), args.topic)
        if script_file:
            print(f"\n  ✅ Script saved: {script_file}")
        else:
            sys.exit(1)

    elif args.stage == "tts":
        if not args.script_file:
            print("  ❌ --script-file required for tts stage", file=sys.stderr)
            sys.exit(1)
        audio_file = stage_tts(args.script_file, args.output, args.speaker, args.device)
        if audio_file:
            print(f"\n  ✅ Audio saved: {audio_file}")
        else:
            sys.exit(1)

    elif args.stage == "cinematographer":
        if not args.script_file:
            print("  ❌ --script-file required for cinematographer stage", file=sys.stderr)
            sys.exit(1)
        prompts_dir = OUTPUTS_DIR / "prompts"
        prompts_file = stage_cinematographer(args.script_file, str(prompts_dir), args.topic)
        if prompts_file:
            print(f"\n  ✅ Prompts saved: {prompts_file}")
        else:
            sys.exit(1)

    elif args.stage == "video":
        if not args.prompts_file:
            print("  ❌ --prompts-file required for video stage", file=sys.stderr)
            sys.exit(1)
        success = stage_video(args.prompts_file, args.clips_dir, args.model)
        if not success:
            sys.exit(1)

    elif args.stage == "stitch":
        if not args.clips_dir or not args.audio:
            print("  ❌ --clips-dir and --audio required for stitch stage", file=sys.stderr)
            sys.exit(1)
        success = stage_stitch(args.clips_dir, args.audio, args.output)
        if not success:
            sys.exit(1)

    elif args.stage == "telegram":
        if not args.video:
            print("  ❌ --video required for telegram stage", file=sys.stderr)
            sys.exit(1)
        success = stage_telegram(args.video)
        if not success:
            sys.exit(1)

    elif args.stage == "all":
        if not args.topic:
            print("  ❌ --topic required for --all stage", file=sys.stderr)
            sys.exit(1)
        success = stage_all(args.topic, args.output, args.speaker, args.device, args.model, args.telegram_target)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
