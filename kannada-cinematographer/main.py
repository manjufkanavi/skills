#!/usr/bin/env python3
"""
kannada-cinematographer — Agy-powered scene visualiser and image prompt generator.

Takes Kannada text (poem, story, vachana, tatvapada) and visualises it as a
short film — scene-by-scene cinematographic breakdown with ready-to-use
image generation prompts.

Usage:
    python3 main.py --text "ಎಲ್ಲಿರುವೆ ಮನುಜ, ನಿನ್ನ ಗುರಿಯೇನು?"
    python3 main.py --file path/to/poem.txt
    python3 main.py --source "ಶಿಶುನಾಳ ಶರೀಫರ ತಂಬೂರಿ ತತ್ವಪದ"
"""

import subprocess
import sys
import os
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

WORKSPACE = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
PROMPTS_DIR = WORKSPACE / "prompts"
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Default Role — Cinematographer
# ============================================================================

DEFAULT_ROLE = """ನಿಮ್ಮ ಪಾತ್ರ: ಪ್ರಖ್ಯಾತ ಚಲನಚಿತ್ರ ಸಿನಿಮಾಟೋಗ್ರಾಫರ್ ಮತ್ತು ದೃಶ್ಯ ನಿರ್ದೇಶಕ.

ನೀವು ಕನ್ನಡ ಸಾಹಿತ್ಯ ಮತ್ತು ಸಂಸ್ಕೃತಿಯನ್ನು ಆಳವಾಗಿ ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೀರಿ. ಕನ್ನಡ ಪದ್ಯ/ಕಥೆ/ವಚನಗಳನ್ನು ಓದಿ, ಅವುಗಳ ಭಾವ ಮತ್ತು ಸಂದೇಶವನ್ನು ದೃಶ್ಯಗಳಾಗಿ ಪರಿವರ್ತಿಸುವಲ್ಲಿ ನಿಪುಣರು.

ನಿಮ್ಮ ವಿಶ್ಲೇಷಣೆಯಲ್ಲಿ:
- ಕನ್ನಡ ಮೂಲ ಪಠ್ಯದ ಪ್ರತಿ ಮಹತ್ವದ ಭಾಗವನ್ನೂ ದೃಶ್ಯವಾಗಿ ಪರಿವರ್ತಿಸಿ
- ಪ್ರತಿ ದೃಶ್ಯಕ್ಕೂ ಸೂಕ್ತ ಕ್ಯಾಮೆರಾ ಕೋನ, ಬೆಳಕು, ಬಣ್ಣ ಸಂಯೋಜನೆ ನಿರ್ಧರಿಸಿ
- ಭಾವನೆಗಳನ್ನು ದೃಶ್ಯ ಭಾಷೆಯಲ್ಲಿ ಅಭಿವ್ಯಕ್ತಿಸಿ
- ಸಾಂಸ್ಕೃತಿಕ ನಿಖರತೆ ಕಾಪಾಡಿ — ಕರ್ನಾಟಕದ ಉಡುಗೆ, ವಾಸ್ತುಶಿಲ್ಪ, ಪ್ರಕೃತಿ, ಆಚರಣೆಗಳನ್ನು ನಿಖರವಾಗಿ ಚಿತ್ರಿಸಿ"""

# ============================================================================
# Visual style presets
# ============================================================================

STYLE_GUIDES = {
    "cinematic": """ವಿಷುಯಲ್ ಶೈಲಿ: ಸಿನಿಮ್ಯಾಟಿಕ್ — realistic camera work, professional film lighting, shallow depth of field, anamorphic lens feel, film grain, cinematic color grading.""",

    "theatrical": """ವಿಷುಯಲ್ ಶೈಲಿ: ನಾಟಕೀಯ — dramatic stage lighting, bold shadows, theatrical composition, high contrast, intense expressions, stage-like framing.""",

    "watercolor": """ವಿಷುಯಲ್ ಶೈಲಿ: ವಾಟರ್ಕಲರ್ — soft pastel watercolor painting style, flowing brush strokes, paper texture, gentle color transitions, ethereal quality.""",

    "anime": """ವಿಷುಯಲ್ ಶೈಲಿ: ಅನಿಮೆ — Japanese anime aesthetic, cel-shaded, vibrant colors, expressive eyes, stylized backgrounds, dynamic composition.""",

    "realistic": """ವಿಷುಯಲ್ ಶೈಲಿ: ರಿಯಲಿಸ್ಟಿಕ್ — photorealistic, ultra-detailed, natural lighting, true-to-life textures, documentary-style authenticity.""",

    "painterly": """ವಿಷುಯಲ್ ಶೈಲಿ: ಪೇಂಟರ್ಲಿ — oil painting style, impasto texture, rich brushwork, classical composition, warm color palette, fine art aesthetic.""",
}

ASPECT_SUFFIX = {
    "16:9": "cinematic widescreen aspect ratio 16:9",
    "9:16": "vertical portrait aspect ratio 9:16 for mobile",
    "1:1": "square aspect ratio 1:1",
    "4:3": "classic 4:3 aspect ratio, Academy frame",
}

# ============================================================================
# Helper: Run agy with stdin piping
# ============================================================================

def run_agy(prompt_text: str, timeout: int = 300, model: str = "gemini-3.1-pro-high", effort: str = "high") -> str:
    """Run agy with the given prompt via stdin piping."""
    cmd = ["agy", "--dangerously-skip-permissions", "-p", prompt_text, "--model", model]
    if model.startswith("gemini") or model.startswith("Gemini"):
        cmd.extend(["--effort", effort])
    proc = subprocess.run(
        cmd,
        capture_output=True, text=True, timeout=timeout
    )
    if proc.returncode != 0:
        raise RuntimeError(f"agy failed (exit {proc.returncode}): {proc.stderr[:500]}")
    return proc.stdout


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = re.sub(r'[^\w\s\-ಂಃಅ-ಹಾ-ೄೆ-ೌ್]', '', text)
    slug = re.sub(r'[\s_]+', '_', slug.strip())
    slug = slug.lower()[:120]
    if not slug:
        slug = "scene_prompts"
    return slug


def extract_json(text: str) -> dict | None:
    """Extract JSON object from agy response."""
    # Try to find JSON between triple backticks (most common with agy)
    code_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if code_match:
        candidate = code_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Try to find JSON between braces, handling nested structures
    brace_idx = text.find('{')
    if brace_idx >= 0:
        # Find matching closing brace
        depth = 0
        for i in range(brace_idx, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_idx:i+1])
                    except json.JSONDecodeError:
                        pass

    # Last resort: find largest JSON-like block
    json_matches = re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    candidates = []
    for match in json_matches:
        try:
            data = json.loads(match.group(0))
            candidates.append(data)
        except json.JSONDecodeError:
            continue

    if candidates:
        # Return the one with most keys (likely the main data)
        return max(candidates, key=lambda d: len(d.keys()))

    return None


# ============================================================================
# Prompt Evaluation
# ============================================================================

def evaluate_prompts_against_essay(essay_path, scenes, model="gemini-3.1-pro-high", effort="high"):
    """Evaluate image prompts against essay content and auto-correct mismatches."""
    import json as json_mod
    
    # Read essay content
    essay_text = essay_path.read_text(encoding="utf-8") if hasattr(essay_path, 'read_text') else str(essay_path)
    
    # For each scene, evaluate the image_prompt against the essay
    evaluation_prompt = f"""<think>
I am a Kannada literary-visual critic. I need to evaluate whether AI image generation prompts correctly represent the essay's narrative, cultural context, and emotional tone. I must check for:
1. Visual accuracy — does the prompt match what the essay describes?
2. Cultural authenticity — are the settings, clothing, architecture accurate for Karnataka?
3. Emotional resonance — does the visual mood match the essay's tone?
4. Plot consistency — does the scene follow the essay's narrative flow?
</think>

Role: ಪ್ರಖ್ಯಾತ ಕನ್ನಡ ಸಾಹಿತ್ಯ-ದೃಶ್ಯ ವಿಮರ್ಶಕ (Renowned Kannada Literary-Visual Critic)

Below is a Kannada essay and a set of proposed image generation prompts for a video adaptation.
Evaluate each prompt for consistency with the essay's plot, emotional tone, cultural accuracy, and narrative flow.

For each scene, output JSON evaluation:
{{
  "scene_number": N,
  "consistent": true/false,
  "issues": ["list of specific mismatches"],
  "corrected_prompt": "corrected image prompt fixing all issues"
}}

If all prompts are consistent, simply output {{"all_consistent": true}}.

ESSAY:
---
{essay_text[:3000]}
---

SCENES:
{json_mod.dumps([{{"scene_number": s.get("scene_number", i+1), "image_prompt": s.get("image_prompt", "")}} for i, s in enumerate(scenes)], ensure_ascii=False, indent=2)}
"""
    
    print("\n  ▶ Evaluating prompts against essay plot...")
    raw = run_agy(evaluation_prompt, timeout=300, model=model, effort=effort)
    
    # Try to parse JSON from response
    try:
        import re as re_mod
        import json as json_mod2
        code_match = re_mod.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re_mod.DOTALL)
        if code_match:
            result = json_mod2.loads(code_match.group(1).strip())
        else:
            result = json_mod2.loads(raw.strip())
        
        if isinstance(result, dict) and result.get("all_consistent"):
            print("  ✓ All prompts consistent with essay plot")
            return scenes
        
        if isinstance(result, dict) and "scenes" in result:
            # Apply corrections
            corrections = {s["scene_number"]: s for s in result["scenes"]}
            for scene in scenes:
                s_num = scene.get("scene_number", scenes.index(scene) + 1)
                if s_num in corrections and not corrections[s_num].get("consistent", True):
                    old_prompt = scene.get("image_prompt", "")[:60]
                    scene["image_prompt"] = corrections[s_num].get("corrected_prompt", scene["image_prompt"])
                    print(f"  🔄 Scene {s_num}: corrected prompt (was: {old_prompt}...)")
            return scenes
    except Exception as e:
        print(f"  ⚠ Prompt evaluation parsing issue: {e}")
        print("  Continuing with original prompts...")
    
    return scenes


# ============================================================================
# Scene generation
# ============================================================================

def build_scene_prompt(
    kannada_text: str,
    style: str = "cinematic",
    aspect: str = "16:9"
) -> str:
    """Build the full prompt for agy to analyse and generate scenes."""
    style_guide = STYLE_GUIDES.get(style, STYLE_GUIDES["cinematic"])
    aspect_guide = ASPECT_SUFFIX.get(aspect, ASPECT_SUFFIX["16:9"])

    prompt = f"""<think>
I am a renowned Kannada cinematographer and visual director. I need to analyse this Kannada text deeply and visualise it as a film. Let me think step by step:
1. What is the core emotional/spiritual message of this text?
2. What are the key visual moments that represent each part of the narrative?
3. For each scene, what camera angles, lighting, colors, and composition best convey the mood?
4. How can I make image prompts vivid, culturally accurate, and ready for Flux/Midjourney?
5. Ensuring the JSON output is clean, well-structured, and parsable.
</think>

{DEFAULT_ROLE}

{style_guide}

ಕೆಳಗಿನ ಕನ್ನಡ ಪಠ್ಯವನ್ನು ಓದಿ. ಇದನ್ನು ಒಂದು ಸಣ್ಣ ಚಲನಚಿತ್ರದಂತೆ ದೃಶ್ಯೀಕರಿಸಿ. ಪಠ್ಯದ ಪ್ರತಿ ಮಹತ್ವದ ಭಾಗವನ್ನೂ ಒಂದು ದೃಶ್ಯವಾಗಿ ಪರಿವರ್ತಿಸಿ.

ASPECT RATIO: {aspect_guide}

ನೀವು ಕೇವಲ ಕೆಳಗಿನ JSON ಫಾರ್ಮ್ಯಾಟ್‌ನಲ್ಲಿ ಮಾತ್ರ ಔಟ್‌ಪುಟ್ ನೀಡಬೇಕು. ಯಾವುದೇ ಹೆಚ್ಚುವರಿ ಪಠ್ಯ, ವಿವರಣೆ ಅಥವಾ ಕೋಡ್ ಫೆನ್ಸ್ ಇಲ್ಲದೆ ಕೇವಲ JSON:

{{
  "title": "ಸಿನಿಮಾದ ಶೀರ್ಷಿಕೆ",
  "kannada_title": "ಚಲನಚಿತ್ರದ ಕನ್ನಡ ಶೀರ್ಷಿಕೆ",
  "source_text": "ಮೂಲ ಕನ್ನಡ ಪಠ್ಯ",
  "total_scenes": 4,
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Scene Title in Kannada",
      "title_en": "Scene Title in English",
      "kannada_source": "ಪಠ್ಯದ ಈ ದೃಶ್ಯಕ್ಕೆ ಸಂಬಂಧಿಸಿದ ಭಾಗ (exact Kannada segment)",
      "visual_description": "Brief narrative description of what happens in this scene",
      "cinematography": {{
        "camera": "e.g., Wide establishing shot, Close-up, Medium shot, Dutch angle, Aerial view",
        "lens": "e.g., 35mm, 50mm, 85mm, Wide-angle 24mm, Telephoto 135mm, Anamorphic",
        "lighting": "e.g., Golden hour, Low-key, Soft diffused, Backlit, Candlelight, Natural daylight",
        "color_palette": "e.g., Warm amber and gold with deep brown shadows",
        "composition": "e.g., Rule of thirds, Symmetrical, Leading lines, Frame within frame, Deep focus",
        "mood": "e.g., Serene, Melancholic, Mysterious, Joyful, Intense, Contemplative"
      }},
      "image_prompt": "Detailed, ready-to-use English prompt for image generation. Include: subject, setting, lighting, colors, composition, style, atmosphere, cultural details. Must be vivid and specific — at least 3-4 sentences. Include the aspect ratio guidance.",
      "characters": ["List of characters present in this scene"],
      "setting": "Location and time setting"
    }}
  ]
}}

ಪ್ರಮುಖ:
- ಕನ್ನಡ ಪಠ್ಯವನ್ನು ಓದಿ, ಅದರ ಭಾವ, ಸಂದೇಶ, ಮತ್ತು ಸನ್ನಿವೇಶಗಳನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ
- ಪ್ರತಿ ದೃಶ್ಯಕ್ಕೂ ನಿಖರವಾದ image_prompt ರಚಿಸಿ — ಇದು Flux/Midjourney/SDXL/DALL-E ಮಾದರಿಗಳಿಗೆ ನೇರವಾಗಿ ಬಳಸಲು ಯೋಗ್ಯವಾಗಿರಬೇಕು
- image_prompt ಸಂಪೂರ್ಣ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ, ವಿವರವಾಗಿ, ಮತ್ತು ಕಲಾತ್ಮಕವಾಗಿರಬೇಕು
- ಸಾಂಸ್ಕೃತಿಕ ನಿಖರತೆಗೆ ಗಮನ ಕೊಡಿ — ಕರ್ನಾಟಕದ ಉಡುಗೆ, ವಾಸ್ತುಶಿಲ್ಪ, ಪ್ರಕೃತಿ ದೃಶ್ಯಗಳು
- ಕೇವಲ JSON ಮಾತ್ರ — ಬೇರೆ ಏನೂ ಬೇಡ

ಕನ್ನಡ ಪಠ್ಯ:
---
{kannada_text}
---"""

    return prompt


def parse_scenes(raw_output: str) -> dict | None:
    """Parse agy output to extract scene data."""
    data = extract_json(raw_output)

    if data and "scenes" in data and isinstance(data["scenes"], list):
        return data

    # If JSON parsing failed but we got content, try to build a minimal structure
    # This handles cases where agy can't produce valid JSON
    print("  ⚠ Could not parse structured JSON from agy. Trying fallback extraction...")
    return None


# ============================================================================
# Scene fallback — parse agy's free-form response
# ============================================================================

def parse_fallback_text(raw: str, source_text: str, style: str, aspect: str) -> dict:
    """When JSON parsing fails, build scene data from free-form agy output."""
    aspect_guide = ASPECT_SUFFIX.get(aspect, ASPECT_SUFFIX["16:9"])

    scenes = []
    scene_blocks = re.split(r'(?=^#{1,3}\s*Scene\s+\d+|(?:\*\*)?Scene\s+\d+(?:\*\*)?:)', raw, flags=re.MULTILINE)

    if len(scene_blocks) <= 1:
        scene_blocks = re.split(r'(?=Scene\s+\d)', raw, flags=re.IGNORECASE)

    for i, block in enumerate(scene_blocks):
        if not block.strip():
            continue
        scene_data = {
            "scene_number": i + 1,
            "title": f"Scene {i+1}",
            "title_en": f"Scene {i+1}",
            "kannada_source": "",
            "visual_description": "",
            "cinematography": {
                "camera": "",
                "lens": "",
                "lighting": "",
                "color_palette": "",
                "composition": "",
                "mood": ""
            },
            "image_prompt": "",
            "characters": [],
            "setting": ""
        }

        # Try to extract various fields using regex
        for field in ["camera", "lens", "lighting", "color_palette", "color palette",
                       "composition", "mood"]:
            field_key = field.replace(" ", "_")
            field_regex = re.compile(
                rf'(?:{field}|{field.replace("_"," ")})[\s:]*([^\n]+)',
                re.IGNORECASE
            )
            match = field_regex.search(block)
            if match:
                scene_data["cinematography"][field_key] = match.group(1).strip()

        # Try to get image_prompt
        prompt_match = re.search(r'(?:image[_\s]?prompt|prompt)[:\s]*([^\n]+(?:\n(?!\n|#|[A-Z]))*)', block, re.IGNORECASE)
        if prompt_match:
            scene_data["image_prompt"] = prompt_match.group(1).strip()

        # Try to get setting
        setting_match = re.search(r'setting[:\s]*([^\n]+)', block, re.IGNORECASE)
        if setting_match:
            scene_data["setting"] = setting_match.group(1).strip()

        # Try to get characters
        chars_match = re.search(r'characters[:\s]*([^\n]+)', block, re.IGNORECASE)
        if chars_match:
            scene_data["characters"] = [c.strip() for c in chars_match.group(1).split(",")]

        scenes.append(scene_data)

    if not scenes:
        # Last resort: split by paragraphs and treat each as a scene
        paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
        scenes = [
            {
                "scene_number": i + 1,
                "title": f"Scene {i+1}",
                "title_en": f"Scene {i+1}",
                "kannada_source": "",
                "visual_description": para[:200],
                "cinematography": {
                    "camera": "", "lens": "", "lighting": "", "color_palette": "",
                    "composition": "", "mood": ""
                },
                "image_prompt": para[:500] if len(para) > 500 else para,
                "characters": [],
                "setting": ""
            }
            for i, para in enumerate(paragraphs[:10])
        ]

    return {
        "title": "Visualised from Kannada Text",
        "kannada_title": "ಕನ್ನಡ ಪಠ್ಯದ ದೃಶ್ಯೀಕರಣ",
        "source_text": source_text,
        "total_scenes": len(scenes),
        "scenes": scenes,
    }


# ============================================================================
# Markdown output builder
# ============================================================================

def build_prompts_markdown(data: dict, style: str, aspect: str) -> str:
    """Convert scene data into a beautiful prompts.md file."""
    title = data.get("title", "Cinematographic Visualisation")
    kannada_title = data.get("kannada_title", "ದೃಶ್ಯ ವಿಭಜನೆ")
    scenes = data.get("scenes", [])
    source_text = data.get("source_text", "")

    lines = []
    lines.append("---")
    lines.append(f"title: {title}")
    lines.append(f"kannada_title: {kannada_title}")
    lines.append(f"style: {style}")
    lines.append(f"aspect_ratio: {aspect}")
    lines.append(f"total_scenes: {len(scenes)}")
    lines.append(f"generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"generator: kannada-cinematographer (agy-powered)")
    lines.append("---")
    lines.append("")

    # Header
    lines.append(f"# {kannada_title}")
    lines.append("")
    lines.append(f"*Cinematographic Scene Breakdown — {title}*")
    lines.append("")
    lines.append(f"**Visual Style:** {style} | **Aspect Ratio:** {aspect}")
    lines.append("")

    # Table of contents
    lines.append("## 📋 Scene Index")
    lines.append("")
    for scene in scenes:
        s_num = scene.get("scene_number", scenes.index(scene) + 1)
        s_title = scene.get("title_en", scene.get("title", f"Scene {s_num}"))
        lines.append(f"- **Scene {s_num}:** {s_title}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Each scene in detail
    for scene in scenes:
        s_num = scene.get("scene_number", scenes.index(scene) + 1)
        s_title_kn = scene.get("title", f"ದೃಶ್ಯ {s_num}")
        s_title_en = scene.get("title_en", f"Scene {s_num}")
        s_source = scene.get("kannada_source", "")
        s_desc = scene.get("visual_description", "")
        cine = scene.get("cinematography", {})
        img_prompt = scene.get("image_prompt", "")
        characters = scene.get("characters", [])
        setting = scene.get("setting", "")

        lines.append(f"## 🎬 Scene {s_num}: {s_title_en}")
        lines.append("")
        lines.append(f"**ಕನ್ನಡ:** {s_title_kn}")
        lines.append("")

        if s_source:
            lines.append("### 📜 Kannada Source")
            lines.append("")
            lines.append(f"> {s_source}")
            lines.append("")

        if s_desc:
            lines.append("### 👁️ Visual Description")
            lines.append("")
            lines.append(s_desc)
            lines.append("")

        if setting:
            lines.append("### 🏠 Setting")
            lines.append("")
            lines.append(setting)
            lines.append("")

        if characters:
            lines.append("### 👤 Characters")
            lines.append("")
            for char in characters:
                lines.append(f"- {char}")
            lines.append("")

        lines.append("### 🎥 Cinematography")
        lines.append("")
        lines.append("| Element | Specification |")
        lines.append("|---------|--------------|")
        lines.append(f"| **Camera** | {cine.get('camera', '—')} |")
        lines.append(f"| **Lens** | {cine.get('lens', '—')} |")
        lines.append(f"| **Lighting** | {cine.get('lighting', '—')} |")
        lines.append(f"| **Color Palette** | {cine.get('color_palette', '—')} |")
        lines.append(f"| **Composition** | {cine.get('composition', '—')} |")
        lines.append(f"| **Mood** | {cine.get('mood', '—')} |")
        lines.append("")

        if img_prompt:
            lines.append("### 🤖 Image Generation Prompt")
            lines.append("")
            lines.append(f"> {img_prompt}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Footer
    lines.append("")
    lines.append("*Generated by kannada-cinematographer skill — agy-powered scene visualisation*")
    lines.append("")

    return "\n".join(lines)


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate cinematographic scene breakdowns and image prompts from Kannada text"
    )
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument("--text", help="Direct Kannada text input")
    text_group.add_argument("--file", help="Path to .txt or .md file with Kannada text")
    text_group.add_argument("--source", help="Named source (agy will use context if possible)")

    parser.add_argument("--style", default="cinematic",
                        choices=list(STYLE_GUIDES.keys()),
                        help="Visual style for prompts (default: cinematic)")
    parser.add_argument("--aspect", default="16:9",
                        choices=list(ASPECT_SUFFIX.keys()),
                        help="Aspect ratio for image prompts (default: 16:9)")
    parser.add_argument("--model", default="gemini-3.1-pro-high",
                        help="agy model to use")
    parser.add_argument("--effort", default="high",
                        choices=["low", "medium", "high"],
                        help="agy reasoning effort (default: high)")
    parser.add_argument("--output", default=str(PROMPTS_DIR),
                        help="Output directory")
    parser.add_argument("--num-scenes", type=int, default=8,
                        help="Number of scenes to generate (default: 8, good for ~2min video)")
    parser.add_argument("--force", action="store_true",
                        help="Re-generate if prompts.md exists")

    args = parser.parse_args()

    # Get the kannada text
    kannada_text = ""
    source_label = ""
    slug_base = ""

    if args.text:
        kannada_text = args.text
        source_label = args.text[:60]
        slug_base = slugify(args.text[:60])
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"✗ File not found: {args.file}")
            sys.exit(1)
        kannada_text = file_path.read_text(encoding="utf-8")
        source_label = file_path.stem
        slug_base = slugify(file_path.stem)
    elif args.source:
        kannada_text = args.source
        source_label = args.source
        slug_base = slugify(args.source)

    if not kannada_text.strip():
        print("✗ No Kannada text provided or text is empty.")
        sys.exit(1)

    # Determine output path
    output_dir = Path(args.output) / slug_base
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "prompts.md"
    source_file = output_dir / "source.txt"

    # Check if already exists
    if output_file.exists() and not args.force:
        print(f"⚠ Prompts already exist: {output_file}")
        print(f"  Use --force to re-generate")
        sys.exit(0)

    print("=" * 60)
    print("  ಕನ್ನಡ ಸಿನಿಮಾಟೋಗ್ರಾಫರ್")
    print("  Kannada Cinematographic Scene Creator")
    print("=" * 60)
    print()
    print(f"  Source: {source_label[:80]}")
    print(f"  Style: {args.style} | Aspect: {args.aspect}")
    print(f"  Model: {args.model}")
    print()

    try:
        # Step 1: Generate scenes via agy
        print("  ▶ Analysing text and generating scenes...")
        scene_prompt = build_scene_prompt(kannada_text, args.style, args.aspect)
        raw_output = run_agy(scene_prompt, timeout=300, model=args.model, effort=args.effort)

        # Step 2: Parse the result
        data = parse_scenes(raw_output)

        if data is None:
            print("  ▶ JSON parsing failed. Using fallback extraction...")
            data = parse_fallback_text(raw_output, kannada_text, args.style, args.aspect)

        # Step 3: Save source text
        source_file.write_text(kannada_text, encoding="utf-8")
        print(f"  ✓ Source saved: {source_file}")

        # Step 4: Build and save prompts.md
        markdown = build_prompts_markdown(data, args.style, args.aspect)
        output_file.write_text(markdown, encoding="utf-8")
        file_size = output_file.stat().st_size / 1024

        scene_count = data.get("total_scenes", len(data.get("scenes", [])))
        print(f"  ✓ Prompts saved: {output_file}")
        print(f"  ✓ Scenes: {scene_count}")
        print(f"  ✓ Size: {file_size:.1f} KB")
        print()
        print("=" * 60)

    except subprocess.TimeoutExpired:
        print("✗ agy timed out after 300 seconds. Try shorter text or use --style realistic (faster).")
        sys.exit(1)
    except RuntimeError as e:
        print(f"✗ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
