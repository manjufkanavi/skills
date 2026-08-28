#!/usr/bin/env python3
"""
kannada-essay — Agy-powered Kannada essay generator.

Uses agy (Antigravity CLI) with a role-based prompting system to generate
high-quality Kannada essays on any topic. Saves output as a .md file.

Usage:
    python3 main.py --topic "ಪ್ರೀತಿ ಮತ್ತು ಆಧ್ಯಾತ್ಮಿಕತೆ"
    python3 main.py --topic "Love and Spirituality" --style reflective --length 2000
"""

import subprocess
import sys
import os
import re
import argparse
from pathlib import Path
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

REPO_PATH = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
# Resolve workspace path
WORKSPACE = REPO_PATH
ESSAYS_DIR = WORKSPACE / "essays"
ESSAYS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Default Role (Kannada Essayist)
# ============================================================================

DEFAULT_ROLE = """ನಿಮ್ಮ ಪಾತ್ರ: ಪ್ರಖ್ಯಾತ ಕನ್ನಡ ಪ್ರಬಂಧಕಾರ.

ನೀವು ಕನ್ನಡ ಸಾಹಿತ್ಯದಲ್ಲಿ ಆಳವಾದ ಪಾಂಡಿತ್ಯವನ್ನು ಹೊಂದಿದ್ದೀರಿ. ನಿಮ್ಮ ಬರಹಗಳು ಸರಳ, ಸುಂದರ ಮತ್ತು ಅರ್ಥಪೂರ್ಣವಾಗಿರುತ್ತವೆ. ನೀವು ಸಂಕೀರ್ಣ ವಿಚಾರಗಳನ್ನು ಸಹ ಸಾಮಾನ್ಯ ಓದುಗರಿಗೆ ಸುಲಭವಾಗಿ ಅರ್ಥವಾಗುವಂತೆ ವಿವರಿಸಬಲ್ಲಿರಿ.

ನಿಮ್ಮ ಪ್ರಬಂಧಗಳಲ್ಲಿ:
- ಶ್ರೀಮಂತ ಕನ್ನಡ ಪದಸಂಪತ್ತು ಬಳಸಿ
- ಸೂಕ್ತ ಕನ್ನಡ ಗಾದೆಗಳು, ನಾಣ್ಣುಡಿಗಳು ಮತ್ತು ಸಾಹಿತ್ಯಿಕ ಉಲ್ಲೇಖಗಳನ್ನು ಸೇರಿಸಿ
- ಪ್ರತಿ ವಿಭಾಗಕ್ಕೂ ಸ್ಪಷ್ಟ ಶೀರ್ಷಿಕೆ ನೀಡಿ
- ಪೀಠಿಕೆ, ವಿಷಯ ವಿವರಣೆ ಮತ್ತು ಉಪಸಂಹಾರ ಕಡ್ಡಾಯವಾಗಿ ಇರಲಿ
- ಓದುಗರನ್ನು ತೊಡಗಿಸಿಕೊಳ್ಳುವ ಶೈಲಿಯಲ್ಲಿ ಬರೆಯಿರಿ"""

# ============================================================================
# Style presets
# ============================================================================

STYLE_GUIDES = {
    "philosophical": """ಶೈಲಿ: ತಾತ್ವಿಕ — ಆಳವಾದ ಚಿಂತನೆ ಮತ್ತು ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳುವ ಶೈಲಿ. ನಿಮ್ಮ ವಾದಗಳಿಗೆ ಆಧ್ಯಾತ್ಮಿಕ ಮತ್ತು ತಾತ್ವಿಕ ಆಯಾಮ ನೀಡಿ. ದಾಸರು, ಶರಣರು, ಸೂಫಿಗಳ ವಚನಗಳನ್ನು ಉಲ್ಲೇಖಿಸಿ.""",

    "analytical": """ಶೈಲಿ: ವಿಶ್ಲೇಷಣಾತ್ಮಕ — ಸತ್ಯಾಂಶಗಳು, ಅಂಕಿ-ಅಂಶಗಳು ಮತ್ತು ತಾರ್ಕಿಕ ವಾದಗಳೊಂದಿಗೆ ವಿಷಯವನ್ನು ವಿಶ್ಲೇಷಿಸಿ. ವಿಭಿನ್ನ ದೃಷ್ಟಿಕೋನಗಳನ್ನು ಹೋಲಿಸಿ.""",

    "descriptive": """ಶೈಲಿ: ವರ್ಣನಾತ್ಮಕ — ಸವಿಸ್ತಾರವಾದ ವರ್ಣನೆಗಳ ಮೂಲಕ ಓದುಗರ ಮನದಲ್ಲಿ ಚಿತ್ರಣವನ್ನು ಮೂಡಿಸಿ. ಇಂದ್ರಿಯಗಳನ್ನು ತೊಡಗಿಸಿಕೊಳ್ಳಿ (ಕಾಣುವ, ಕೇಳುವ, ಸ್ಪರ್ಶಿಸುವ, ರುಚಿಸುವ, ವಾಸನೆ).""",

    "narrative": """ಶೈಲಿ: ಕಥನಾತ್ಮಕ — ಕಥೆ, ನೆನಪು, ಅನುಭವಗಳ ಮೂಲಕ ವಿಷಯವನ್ನು ಬಿಡಿಸಿ. ವೈಯಕ್ತಿಕ ನಿರೂಪಣೆ ಮತ್ತು ಸನ್ನಿವೇಶಗಳನ್ನು ಬಳಸಿ.""",

    "reflective": """ಶೈಲಿ: ಆತ್ಮಚಿಂತನಾತ್ಮಕ — ಸ್ವಾನುಭವ, ಆತ್ಮಾವಲೋಕನ ಮತ್ತು ವೈಯಕ್ತಿಕ ಬೆಳವಣಿಗೆಯ ದೃಷ್ಟಿಕೋನದಿಂದ ಬರೆಯಿರಿ. ನಿಮ್ಮ ಸ್ವಂತ ಅನಿಸಿಕೆಗಳನ್ನು ಪ್ರಾಮಾಣಿಕವಾಗಿ ಹಂಚಿಕೊಳ್ಳಿ.""",
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
    # Replace spaces and special chars with underscores
    slug = re.sub(r'[^\w\s\-ಂಃಅ-ಹಾ-ೄೆ-ೌ್]', '', text)
    slug = re.sub(r'[\s_]+', '_', slug.strip())
    slug = slug.lower()[:100]
    # Ensure it's not empty
    if not slug:
        slug = "essay"
    return slug


def extract_essay_content(raw: str) -> str:
    """Clean up agy output to get clean markdown content."""
    # Remove any agy conversational framing
    lines = raw.split('\n')
    clean_lines = []
    in_content = False

    for line in lines:
        # Skip agy's own system messages
        if any(skip in line.lower() for skip in [
            "i'll write", "let me write", "here's your", "here is your",
            "certainly", "absolutely", "i will write", "i can write",
            "here's a", "here is a"
        ]):
            # But check if this is just describing what it will do
            if ':' not in line and len(line) < 80:
                continue

        # Skip empty leading lines
        if not in_content and not line.strip():
            continue

        in_content = True
        clean_lines.append(line)

    content = '\n'.join(clean_lines).strip()

    # Remove trailing conversational lines
    ending_phrases = [
        "i hope this", "let me know", "would you like",
        "i can also", "feel free to", "i'm here",
        "does this", "i'd be happy"
    ]
    for phrase in ending_phrases:
        idx = content.lower().rfind(phrase)
        if idx > len(content) * 0.7:  # Only trim if near the end
            content = content[:idx].strip()

    return content


def generate_essay(
    topic: str,
    role: str = DEFAULT_ROLE,
    style: str = "philosophical",
    length: int = 500,
    model: str = "gemini-3.1-pro-high",
    effort: str = "high",
) -> str:
    """Generate a Kannada essay using agy with role-based prompting."""
    style_guide = STYLE_GUIDES.get(style, STYLE_GUIDES["philosophical"])

    prompt = f"""{role}

{style_guide}

<think>
I need to write a thoughtful Kannada essay on "{topic}". Let me carefully consider:
1. The spiritual and philosophical dimensions of this topic
2. How to connect it to Kannada cultural and literary traditions
3. The structure - introduction, body sections, conclusion
4. Making every word count since this should be crisp and impactful
5. Using rich Kannada vocabulary while keeping it accessible
</think>

ವಿಷಯ: {topic}
ಅಂದಾಜು ಉದ್ದ: ಸುಮಾರು {length} ಪದಗಳು

ದಯವಿಟ್ಟು ಕೆಳಗಿನ ರಚನೆಯಲ್ಲಿ ಪ್ರಬಂಧವನ್ನು ಬರೆಯಿರಿ:

## ಶೀರ್ಷಿಕೆ
(ಆಕರ್ಷಕ ಶೀರ್ಷಿಕೆ ಕನ್ನಡದಲ್ಲಿ)

## ಪೀಠಿಕೆ
(ವಿಷಯದ ಪರಿಚಯ ಮತ್ತು ಪ್ರಸ್ತುತತೆ — ಓದುಗರ ಗಮನ ಸೆಳೆಯುವಂತಿರಬೇಕು)

## ವಿಷಯ ವಿವರಣೆ
(2-3 ವಿಭಾಗಗಳು — ಪ್ರತಿ ವಿಭಾಗಕ್ಕೂ ಸೂಕ್ತ ಶೀರ್ಷಿಕೆ ನೀಡಿ. ವಿಷಯದ ವಿವಿಧ ಆಯಾಮಗಳನ್ನು ಅನಾವರಣಗೊಳಿಸಿ)

## ಉಪಸಂಹಾರ
(ಸಾರಾಂಶ ಮತ್ತು ಅಂತಿಮ ಚಿಂತನೆ — ಓದುಗರಿಗೆ ಚಿಂತಿಸಲು ಆಹ್ವಾನ)

ಪ್ರಮುಖ ಸೂಚನೆಗಳು:
- ಸಂಪೂರ್ಣ ಪ್ರಬಂಧ ಕನ್ನಡದಲ್ಲೇ ಇರಲಿ (ವಿಷಯ ಮತ್ತು ಶೀರ್ಷಿಕೆ ಸೇರಿದಂತೆ)
- ಸಹಜ, ಓದಲು ಸುಲಭವಾದ ಕನ್ನಡದಲ್ಲಿ ಬರೆಯಿರಿ
- ಅತಿಯಾದ ಕ್ಲಿಷ್ಟ ಪದಗಳನ್ನು ತಪ್ಪಿಸಿ
- ಪ್ರತಿ ವಿಭಾಗಕ್ಕೂ ಸ್ಪಷ್ಟ ಶೀರ್ಷಿಕೆ ನೀಡಿ
- **ಸಂಕ್ಷಿಪ್ತವಾಗಿ ಮತ್ತು ಅರ್ಥಪೂರ್ಣವಾಗಿ ಬರೆಯಿರಿ — 3 ನಿಮಿಷದಲ್ಲಿ ಓದುವಷ್ಟು ಮಾತ್ರ**
- ಕೊನೆಯಲ್ಲಿ ಒಂದು ಅರ್ಥಪೂರ್ಣ ವಾಕ್ಯದಿಂದ ಮುಕ್ತಾಯಗೊಳಿಸಿ
- ಯಾವುದೇ ಪೀಠಿಕೆ ಅಥವಾ ವಿವರಣೆ ಇಲ್ಲದೆ ನೇರವಾಗಿ ಪ್ರಬಂಧವನ್ನು ಪ್ರಾರಂಭಿಸಿ"""

    print(f"  ▶ Generating essay on: {topic}")
    print(f"  ▶ Style: {style} | Target length: {length} words")
    print(f"  ▶ Model: {model} | Effort: {effort}")
    print()

    raw = run_agy(prompt, timeout=300, model=model, effort=effort)

    # Extract clean content
    content = extract_essay_content(raw)

    # If content is too short or seems like an error, raise
    if len(content) < 100:
        print(f"  ⚠ Response seems short ({len(content)} chars). Full response:")
        print(raw[:1000])

    return content


def get_essay_metadata(topic: str, style: str, length: int) -> dict:
    """Return metadata for the essay frontmatter."""
    return {
        "title": topic,
        "style": style,
        "word_count_target": length,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generator": "kannada-essay (agy-powered)",
    }


def build_markdown(content: str, metadata: dict) -> str:
    """Wrap essay content with YAML frontmatter."""
    meta_lines = [
        "---",
    ]
    for key, val in metadata.items():
        meta_lines.append(f"{key}: {val}")
    meta_lines.append("---")
    meta_lines.append("")
    meta_lines.append(content)
    return "\n".join(meta_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Kannada essay using agy (role-based prompting)"
    )
    parser.add_argument("--topic", required=True, help="Essay topic (Kannada or English)")
    parser.add_argument("--role", default=DEFAULT_ROLE, help="agy agent role override")
    parser.add_argument("--style", default="philosophical",
                        choices=list(STYLE_GUIDES.keys()),
                        help="Essay writing style (default: philosophical)")
    parser.add_argument("--length", type=int, default=500,
                        help="Target word count (default: 500 = ~3min read)")
    parser.add_argument("--model", default="gemini-3.1-pro-high",
                        help="agy model to use")
    parser.add_argument("--effort", default="high",
                        choices=["low", "medium", "high"],
                        help="agy reasoning effort (default: high)")
    parser.add_argument("--output", default=str(ESSAYS_DIR),
                        help="Output directory for essays")
    parser.add_argument("--force", action="store_true",
                        help="Re-generate even if file exists")

    args = parser.parse_args()

    # Calculate output path
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{slugify(args.topic)}.md"

    # Check if already exists
    if output_file.exists() and not args.force:
        print(f"⚠ Essay already exists: {output_file}")
        print(f"  Use --force to re-generate")
        sys.exit(0)

    print("=" * 60)
    print("  ಕನ್ನಡ ಪ್ರಬಂಧ — Kannada Essay Generator")
    print("=" * 60)
    print()

    try:
        # Generate essay
        content = generate_essay(
            topic=args.topic,
            role=args.role,
            style=args.style,
            length=args.length,
            model=args.model,
            effort=args.effort,
        )

        # Build markdown with frontmatter
        metadata = get_essay_metadata(
            topic=args.topic,
            style=args.style,
            length=args.length,
        )
        markdown = build_markdown(content, metadata)

        # Save
        output_file.write_text(markdown, encoding="utf-8")
        file_size = output_file.stat().st_size / 1024

        print()
        print(f"  ✓ Essay saved: {output_file}")
        print(f"  ✓ Size: {file_size:.1f} KB")
        print(f"  ✓ Words (approx): {len(content.split())}")
        print()
        print("=" * 60)

    except subprocess.TimeoutExpired:
        print("✗ agy timed out after 300 seconds. Try a shorter topic or split it.")
        sys.exit(1)
    except RuntimeError as e:
        print(f"✗ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
