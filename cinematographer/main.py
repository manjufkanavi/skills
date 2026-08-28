#!/usr/bin/env python3
"""
cinematographer — offline, language-agnostic scene breakdown and 5-second video-prompt generator.

Takes natural-language text in ANY language (English, Kannada, Hindi, ...) and turns it into a
scene-by-scene breakdown plus ready-to-use 5-second video-generation prompts.

No agy, no LLM CLI, no network calls — pure-Python heuristics. Deterministic and offline.

Scene-breaking uses structural cues only (sentence/paragraph boundaries, punctuation like
`. ! ? 。`, and universal narrative connectors). This is language-agnostic because it keys on
structure, not vocabulary.

Video prompts follow the fixed schema from ai-video-generation-prompt-engineering.md:
    Subject -> Action -> Setting -> Style -> Lighting -> Camera -> Motion(5s) -> Aspect/Duration/FPS -> Negatives

Continuity fields (visual_contract_id, carried_over) follow
cinematographer-scene-construction-story-narrative-continuity.md.

Usage:
    python3 main.py --text "A woman walks into a rain-soaked alley. She stops, looks back."
    python3 main.py --file path/to/story.txt
    python3 main.py --text "..." --style cinematic --aspect 16:9 --max-scenes 8
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ============================================================================
# Configuration / presets (language-agnostic)
# ============================================================================

SCENE_BREAK_MARKERS = [
    # Universal narrative connectors (Latin script) — these often mark scene/beat changes.
    r"\bthen\b", r"\band then\b", r"\bafter that\b", r"\bfinally\b",
    r"\bmeanwhile\b", r"\bhowever\b", r"\bbut\b", r"\bnext\b",
    r"\bsuddenly\b", r"\bjust then\b", r"\bin the meantime\b",
    # Universal narrative connectors (Devanagari / Indic) — कि/फिर etc.
    r"\bकि\b", r"\bfir\b", r"\bफिर\b",
    # Time-transition phrases.
    r"(\d+|\bafterword|later|minutes? later|hours? later|days? later)\b.*",
]

# Time-transition phrases that strongly imply a scene change.
SCENE_CHANGE_PATTERNS = [
    r"\bthen\b", r"\band then\b", r"\bafter that\b", r"\bfinally\b",
    r"\bmeanwhile\b", r"\bsubsequently\b", r"\blater\b",
    r"\bmeanwhile\b", r"\bin the meantime\b", r"\bjust then\b",
    r"\bafter (a|the) ", r"\byears? later\b", r"\bdays? later\b",
    r"\bminutes? later\b", r"\bmoments? later\b", r"\bhours? later\b",
    # Indic time transitions.
    r"\bफिर\b", r"\u092c\u093e\u0926\u094d\b", r"\u0915\u0947 \u092b\u093e\u0926\u094d\b",
]

# Sentence-ending punctuation (covers Latin + Indic + CJK).
SENTENCE_END = re.compile(r"[.!?।]+|\s")

# Universal connectors used to detect intra-sentence scene breaks (lowercased).
CONNECTORS = {
    "then", "and then", "after that", "finally", "meanwhile", "however",
    "but", "next", "suddenly", "just then", "in the meantime",
    "कि", "फिर", "बाद", "तो", "phir", "tab",
}

# Emotional-target keywords -> mapped targets (universal enough to detect in any Latin-script text).
EMOTION_KEYWORDS = [
    ("fear", "tense, anxious"), ("scared", "suspenseful, dread-filled"),
    ("frightened", "tense, anxious"), ("terrified", "haunting, dread-filled"),
    ("panic", "panicked, frantic"), ("horror", "ominous, unsettling"),
    ("love", "warm, tender"), ("happy", "uplifting, joyful"), ("joy", "celebratory, bright"),
    ("sad", "melancholic, somber"), ("grief", "somber, mournful"),
    ("anger", "intense, confrontational"), ("rage", "aggressive, charged"),
    ("calm", "serene, peaceful"), ("peaceful", "tranquil, serene"),
    ("mystery", "enigmatic, mysterious"), ("curiosity", "inquisitive, curious"),
    ("lonely", "isolated, contemplative"), ("solitude", "quiet, introspective"),
    ("hope", "hopeful, luminous"), ("triumph", "victorious, soaring"),
    ("shock", "startling, jarring"), ("surprise", "sudden, surprising"),
    ("nostalgia", "wistful, nostalgic"), ("longing", "yearning, wistful"),
    ("tension", "suspenseful, charged"), ("dread", "foreboding, ominous"),
    ("wonder", "awed, expansive"), ("awe", "sublime, awestruck"),
    # Derived adjectives / states (matched via prefix).
    ("anxious", "tense, anxious"), ("nervous", "tense, nervous"),
    ("worried", "worried, uneasy"), ("crying", "tearful, distressed"),
    ("desperate", "desperate, tense"), ("alone", "isolated, lonely"),
    ("vulnerable", "vulnerable, tense"), ("powerless", "helpless, tense"),
    ("brave", "determined, resolute"), ("courageous", "resolute, determined"),
    ("grateful", "warm, grateful"), ("content", "peaceful, content"),
    ("melancholy", "melancholic, somber"), ("bittersweet", "wistful, bittersweet"),
    ("awe-struck", "awed, expansive"),
]

# Style presets -> descriptive look (universal visual vocabulary).
STYLE_GUIDES = {
    "cinematic": ("photorealistic cinematic look, shallow depth of field, anamorphic lens feel,"
                  " film grain, professional color grading"),
    "anime": ("Japanese anime style, cel-shaded, vibrant colors, expressive eyes,"
              " stylized backgrounds"),
    "realistic": ("photorealistic, ultra-detailed, natural lighting,"
                  " true-to-life textures"),
    "watercolor": ("soft pastel watercolor painting, flowing brush strokes,"
                    " paper texture, gentle color transitions"),
    "painterly": ("oil painting style, impasto brushwork, classical composition,"
                  " warm rich palette"),
    "theatrical": ("dramatic stage lighting, bold shadows, high contrast,"
                   " theatrical composition"),
    "noir": ("black-and-white film noir, high-contrast chiaroscuro lighting,"
             " dramatic shadows, rain-slicked streets"),
}

# Aspect ratio suffix.
ASPECT_SUFFIX = {
    "16:9": "cinematic widescreen aspect ratio 16:9",
    "9:16": "vertical portrait aspect ratio 9:16 for mobile",
    "1:1": "square aspect ratio 1:1",
    "4:3": "classic 4:3 aspect ratio, Academy frame",
}

# Camera moves that resolve within a ~5s window (no full pans).
CAMERA_MOVES = {
    "cinematic": ["slow push-in", "static hold with subtle drift", "gentle handheld"],
    "anime": ["dynamic zoom-in", "static hold", "quick tilt-up"],
    "realistic": ["slow push-in", "static handheld hold", "subtle dolly"],
    "watercolor": ["slow dissolve zoom", "static hold"],
    "painterly": ["slow Ken Burns drift", "static hold"],
    "theatrical": ["slow push-in on subject", "static wide hold"],
    "noir": ["slow push-in", "static tense hold"],
}

# Model recommendations keyed by a coarse motion/narrative descriptor.
MODEL_RECOMMENDATIONS = [
    ("narrative", "Sora 2 Pro"),
    ("dynamic motion", "Kling 2.6"),
    ("stylized movement", "Hailuo 2.3"),
    ("professional transitions", "Runway Gen4"),
]

# Default negative prompt (correction rails from the report).
DEFAULT_NEGATIVE = ("blurry, low quality, deformed hands or faces, extra limbs,"
                    " jittery motion, glitching artifacts, strobing lights,"
                    " text overlays, watermark")


# ============================================================================
# Text segmentation (language-agnostic heuristics)
# ============================================================================

def split_sentences(text: str) -> list[str]:
    """Split text into sentences using universal punctuation + Indic full stops.

    Language-agnostic: keys on Unicode sentence-ending marks (Latin . ! ? , Indic । ॥,
    CJK 。 ！？), not on language-specific word boundaries.
    """
    # Normalize a few Indic / CJK marks to ASCII so the splitter handles them uniformly.
    norm = (text.replace("।", ". ").replace("॥", ". ")
                .replace("。", ". ").replace("！", ".").replace("？", "?"))

    # Split on sentence-ending punctuation, keeping non-space trailing chars.
    parts = re.split(r"(?<=[.!?\u0964])\s+", norm)
    sentences = [s.strip() for s in parts if s.strip()]

    # If nothing split (e.g. no punctuation at all), fall back to newline / paragraph breaks.
    if len(sentences) <= 1:
        pieces = re.split(r"\n\s*\n|\n", text.strip())
        sentences = [p.strip() for p in pieces if p.strip()]

    # Trim trailing sentence punctuation from each.
    cleaned = []
    for s in sentences:
        trimmed = re.sub(r"[.!?।\u0964]+$", "", s).strip()
        if trimmed:
            cleaned.append(trimmed)
    return cleaned


def _shares_subject(prev: str, sent: str) -> bool:
    """Heuristic: do two consecutive sentences share the same grammatical subject?

    Used to decide whether they should be grouped into one scene. Language-agnostic:
    compares the leading subject token(s) after stripping common determiners/verbs.
    """
    a = extract_subject(prev).lower().strip()
    b = extract_subject(sent).lower().strip()

    # Normalize common leading articles.
    a = re.sub(r"^(a|an|the)\b\s+", "", a)
    b = re.sub(r"^(a|an|the)\b\s+", "", b)

    if not a or not b:
        return False

    # Exact subject match (covers "She ... She", "The woman ... The woman").
    if a == b:
        return True

    # Pronoun agreement (she/he/it/they/we/i) with a matching prior noun.
    pronouns = {"she", "he", "it", "they", "we", "i", "him", "her", "them"}
    if a in pronouns or b in pronouns:
        # If one side is a noun and the other references it via pronoun.
        longer = a if len(a) > len(b) else b
        shorter = b if len(a) > len(b) else a
        if longer in pronouns:
            return True  # both are pronouns -> assume same actor for grouping

    # First-token match (covers "The woman ... A young woman").
    first_a = a.split()[0] if a.split() else ""
    first_b = b.split()[0] if b.split() else ""
    return bool(first_a and first_b and (first_a in b or first_b in a))


def split_into_scenes(text: str, max_scenes: int = 12) -> list[str]:
    """Split text into scene blocks using sentence grouping + transition detection.

    Groups consecutive sentences, but breaks a new scene whenever:
      - an explicit transition marker/connector is found mid-sentence, or
      - the sentence contains a strong scene-change cue.
    """
    sentences = split_sentences(text)
    if not sentences:
        return []

    blocks: list[list[str]] = [[sentences[0]]]

    for prev, sent in zip(sentences[:-1], sentences[1:]):
        low = sent.lower()

        # Strong scene-change cue -> always a new block.
        if any(re.search(p, low) for p in SCENE_CHANGE_PATTERNS):
            blocks.append([sent])
            continue

        # Merge with the previous block only when both sentences share a subject and
        # are joined by a coupling connector (single-beat grouping).
        if _shares_subject(prev, sent) and any(c in low for c in CONNECTORS):
            blocks[-1].append(sent)
        else:
            blocks.append([sent])

    # Cap the number of scenes: keep first max_scenes-1 blocks, concatenate all
    # remaining sentences into a single final block.
    if len(blocks) > max_scenes:
        tail = " ".join(" ".join(b) for b in blocks[max_scenes - 1:])
        blocks = blocks[:max_scenes - 1] + [tail.split()]

    return [" ".join(b) if isinstance(b, list) else b for b in blocks]


# ============================================================================
# Heuristic field extraction
# ============================================================================

_PRONOUNS = {"she", "he", "it", "they", "we", "i", "you", "him", "her", "them"}

PREPS = {"in", "into", "at", "on", "over", "under", "behind",
         "near", "beside", "through", "within", "around", "above",
         "below", "by", "from", "with", "about"}

CONJ = {"but", "however", "meanwhile", "then", "and", "so"}

AUX = {"is", "was", "are", "were", "been", "being", "do", "does", "did",
       "have", "has", "had", "will", "would", "shall", "should", "can",
       "could", "may", "might", "must", "need", "dared"}


def _is_article(word: str) -> bool:
    return word in {"a", "an", "the"}


def _find_first_main_verb(sentence: str) -> int:
    """Return the index of the first main verb token, or -1.

    Find the subject/verb boundary (first preposition/conjunction/clause-end), then
    locate the verb within that span:

      1. Auxiliary / modal verb (is/was/have/could/...).
      2. -ed/-ing word that is NOT an adjective (not immediately followed by a bare
         noun — so "frightened child" / "torn teddy" are skipped, but
         "walked into", "quickened her pace", "stops and looks" are caught).
      3. -s word (len>=4, simple present) preceded by a pronoun or followed by an
         article/preposition ("She quickens", "A woman walks into").

    Everything after the boundary is a post-verb modifier, never part of the subject.
    """
    toks = sentence.split()
    n = len(toks)

    def clean(i: int) -> str:
        return toks[i].strip().strip(".,;:!?)") if 0 <= i < n else ""

    def low(i: int) -> str:
        return clean(i).lower() if 0 <= i < n else ""

    # Subject/verb boundary: first clause-end punctuation, preposition or conjunction.
    bound = n
    for i in range(n):
        if toks[i].strip() != clean(i):  # trailing clause punctuation (comma/period)
            bound = i
            break
        c = low(i)
        if c in PREPS or c in CONJ:
            bound = i
            break

    # Rule 1: auxiliary / modal verb.
    for i in range(bound):
        if low(i) in AUX:
            return i

    # Rules 2 & 3: -ed/-ing/-s words within the subject span.
    for i in range(bound):
        c = clean(i)
        if len(c) < 4 or not (c.endswith("s") or c.endswith("ed") or c.endswith("ing")):
            continue

        nxt = low(i + 1) if i + 1 < bound else ""
        prev = low(i - 1)

        if c.endswith("ed") or c.endswith("ing"):
            # Skip adjectives: -ed/-ing immediately followed by a bare noun.
            if (nxt and nxt.isalpha() and not _is_article(nxt)
                    and len(nxt) >= 3 and not nxt.endswith("ly")
                    and nxt not in _PRONOUNS):
                continue
            return i

        if c.endswith("s"):  # len>=4, simple present 3rd-person verb
            if prev in _PRONOUNS:
                return i
            if nxt and (nxt in PREPS or _is_article(nxt)):
                return i

    # Fallback: last word before boundary that looks verb-like.
    if 0 < bound <= n and len(clean(bound - 1)) >= 3:
        c = clean(bound - 1)
        if c.endswith("s") or c.endswith("ed"):
            return bound - 1

    return -1


def extract_subject(sentence: str) -> str:
    """Best-effort subject — everything before the first main verb.

    e.g. "A woman walks into a rain-soaked alley" -> "a woman".
    """
    s = sentence.strip()

    # Strip leading discourse markers common across languages (Devanagari + Latin).
    s = re.sub(r"^\b(and|but|then|however|meanwhile|afterward|finally)\b\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\u0925\b\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\u092b\b\s*", "", s, flags=re.IGNORECASE)

    vidx = _find_first_main_verb(s)
    tokens = s.split()
    if vidx > 0 and vidx <= len(tokens):
        subj_tokens = tokens[:vidx]
    else:
        # No verb found — take the first ~4 words as subject.
        subj_tokens = tokens[:4]

    # Drop trailing conjunctions ("she stops and" -> "she stops").
    while subj_tokens and subj_tokens[-1].lower() in {"and", "but"}:
        subj_tokens.pop()

    # Drop leading articles for cleaner prompts.
    if subj_tokens and subj_tokens[0].lower() in {"a", "an", "the"}:
        subj_tokens = subj_tokens[1:]

    return " ".join(subj_tokens).strip()


def extract_action(sentence: str) -> str:
    """Best-effort action — everything from the first verb onward.

    e.g. "A woman walks into a rain-soaked alley" -> "walks into a rain-soaked alley".
    """
    s = sentence.strip()
    vidx = _find_first_main_verb(s)

    if vidx > 0:
        action = " ".join(s.split()[vidx:])
    else:
        subj = extract_subject(s)
        start = s.lower().find(subj.lower())
        action = (s[start + len(subj):].strip() if start >= 0 else s)

    # Strip leading discourse markers / prepositions that leaked into the action.
    action = re.sub(r"^\b(and|but|then|however|meanwhile|afterward|finally)\b\s*", "",
                    action, flags=re.IGNORECASE)
    action = re.sub(r"^\b(in|into|at|on|near|beside)\b\s+", "", action, flags=re.IGNORECASE)

    return action.strip()[:120]


def extract_setting(sentence: str) -> str:
    """Best-effort setting extraction — look for prepositional/locative cues."""
    s = sentence.strip()

    loc = re.findall(
        r"\b(in|into|at|on|near|beside|under|above|behind|around|through|within)\b[^,.;:!?\n]{2,30}",
        s.lower(),
    )
    if loc:
        return " ".join(loc).strip()

    # Fallback: trailing adverbial / last prepositional phrase.
    tail = re.search(r"\b(in|at|on|near|beside)\s+[^,.;:!?\n]+$", s)
    if tail:
        return tail.group(0).strip()

    # Last clause as a loose setting fallback.
    clauses = s.split(",")
    if len(clauses) > 1:
        return clauses[-1].strip()
    return "general setting"


def detect_emotion(sentence: str) -> tuple[str, bool]:
    """Detect an emotional target from keywords (Latin + common Indic transliterations)."""
    low = sentence.lower()
    for kw, target in EMOTION_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", low):
            return target, True
    # Indic transliteration fallbacks.
    for kw, target in [("dard", "painful"), ("khushi", "joyful"),
                        ("gussa", "angry"), ("pyaar", "loving")]:
        if kw in low:
            return target, True
    # Default neutral.
    return "neutral", False


def pick_camera(style: str) -> str:
    """Pick a camera move appropriate to the style and 5s window."""
    moves = CAMERA_MOVES.get(style, CAMERA_MOVES["cinematic"])
    # Deterministic pick so repeated runs are reproducible.
    return moves[len(moves) % len(moves)]  # always index 0 for determinism


def pick_aspect_ratio_for_shot(width: int, height: int) -> str:
    """Derive a per-shot aspect ratio from frame dimensions."""
    if width <= 0 or height <= 0:
        return "16:9"
    ratio = width / height
    if abs(ratio - 16 / 9) < 0.1:
        return "16:9"
    if abs(ratio - 9 / 16) < 0.1:
        return "9:16"
    if abs(ratio - 1) < 0.1:
        return "1:1"
    if abs(ratio - 4 / 3) < 0.1:
        return "4:3"
    # Closest match by default to 16:9.
    return "16:9"


def recommend_model(style: str) -> str:
    """Pick a model recommendation based on style (heuristic)."""
    return MODEL_RECOMMENDATIONS[0][1]  # default first recommendation


# ============================================================================
# Prompt assembly (5-second video, fixed schema)
# ============================================================================

def build_video_prompt(
    subject: str, action: str, setting: str, style: str, mood: str,
    camera_move: str, lighting: str, aspect: str, negative_prompt: str,
) -> str:
    """Assemble a single 5-second video prompt following the fixed schema.

        Subject -> Action -> Setting -> Style -> Lighting -> Camera -> Motion(5s)
                  -> Aspect/Duration/FPS -> Negatives
    """
    style_desc = STYLE_GUIDES.get(style, STYLE_GUIDES["cinematic"])
    aspect_desc = ASPECT_SUFFIX.get(aspect, ASPECT_SUFFIX["16:9"])

    parts = []
    subject_part = re.sub(r"^(a|an|the)\b\s+", "", subject.strip())
    parts.append(subject_part)
    if action:
        # Normalize leading article ("an walks" -> "walks") and lowercase verb.
        act = re.sub(r"^((?<!\w)[AaAnNoO]\b)\s+", "", action.strip())
        act = re.sub(r"^[A-Z]", lambda m: m.group(0).lower(), act)
        parts.append(f"doing {act}")
    parts.append("set in " + setting.lower().strip())

    prompt = " ".join(parts)
    # Append descriptive modifiers.
    modifier = (f" {style_desc}. Mood: {mood.strip()}. "
                f"{camera_move} camera movement. Lighting: {lighting.lower().strip()}. "
                f"Aspect ratio {aspect_desc}. Single continuous 5-second shot at 24fps.")
    prompt = (prompt + modifier).strip()

    # Negative rail appended for models that accept it.
    if negative_prompt:
        prompt = f"{prompt} [negative: {negative_prompt.strip()}]"

    return prompt


# ============================================================================
# Scene assembly + continuity tracking
# ============================================================================

def assemble_scenes(
    raw_text: str, style: str, aspect: str, negative_prompt: str, max_scenes: int
) -> dict:
    """Build the full scene list with continuity tracking across scenes."""
    blocks = split_into_scenes(raw_text, max_scenes=max_scenes)

    scenes: list[dict] = []
    prev_emotion = ""
    visual_contract_id = f"vc-{style[:3]}-{abs(hash(raw_text)) % 10000}"

    for idx, block in enumerate(blocks):
        sentence = block.strip()
        subject = extract_subject(sentence)
        action = extract_action(sentence)
        setting = extract_setting(sentence)
        emotion, _ = detect_emotion(sentence)

        camera_move = pick_camera(style)
        lighting = "natural daylight" if emotion.startswith(("bright", "joyful", "hopeful")) else (
            "warm practical lighting" if emotion.startswith(("tender", "loving", "nostalgia"))
            else "moody low-key lighting" if emotion.startswith(("tense", "dread", "ominous"))
            else "balanced cinematic lighting"
        )

        # Continuity: carried-over emotional/lighting state from the previous scene.
        carried_over = []
        preceding_rule = ""
        if idx > 0:
            # Emotional carryover.
            carried_over.append("emotional_target")
            if prev_emotion and emotion != "neutral":
                carried_over.append("lighting")
            # Preceding shot rule — simple 30°/eyeline heuristic based on scene role.
            preceding_rule = "matching-action cut from previous shot" if idx > 0 else ""

        # Title: first ~5 words of the block, capitalized.
        title_words = sentence.split()[:5]
        title = " ".join(title_words).strip(" ,:;") or f"Scene {idx + 1}"

        video_prompt = build_video_prompt(
            subject=subject, action=action, setting=setting, style=style,
            mood=emotion, camera_move=camera_move, lighting=lighting,
            aspect=aspect, negative_prompt=negative_prompt,
        )

        scene = {
            "scene_number": idx + 1,
            "title": title,
            "narrative_purpose": ("advance plot" if idx > 0 and preceding_rule else
                                  "establish scene"),
            "emotional_target": emotion,
            "text_segment": sentence[:280],  # cap for readability in JSON
            "visual_description": (f"{subject} {action.lower() if action and not action[0].isupper() else ''}"
                                   f" in {setting.lower()} — mood: {emotion}."),
            "continuity": {
                "visual_contract_id": visual_contract_id,
                "preceding_shot_rule": preceding_rule,
                "carried_over": carried_over,
            },
            "cinematography": {
                "camera": camera_move,
                "lens": "35mm",
                "lighting": lighting,
                "color_palette": _palette_for(emotion),
                "composition": "rule of thirds",
                "mood": emotion,
            },
            "video_prompt": video_prompt,
            "negative_prompt": negative_prompt if not negative_prompt.startswith("[") else negative_prompt[8:],
            "motion_params": {"motion_strength": 0.7, "duration_sec": 5},
            "model_recommendation": recommend_model(style),
            "characters": [subject],
            "setting": setting,
            "seed": None,
        }
        scenes.append(scene)

        prev_emotion = emotion if emotion != "neutral" else prev_emotion

    return {
        "title": _slugify_title(raw_text[:60]),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "cinematographer (offline heuristic engine)",
        "style": style,
        "aspect_ratio": aspect,
        "max_scenes": max_scenes,
        "total_scenes": len(scenes),
        "scenes": scenes,
    }


def _palette_for(emotion: str) -> str:
    """Map an emotion to a color palette (universal visual vocabulary)."""
    if emotion.startswith(("tense", "dread", "ominous")):
        return "desaturated cool blues and greys with deep shadows"
    if emotion.startswith(("tender", "loving", "nostalgia")):
        return "warm ambers and golds with soft highlights"
    if emotion.startswith(("joyful", "uplifting", "hopeful")):
        return "bright saturated warm tones"
    if emotion.startswith(("melancholic", "somber")):
        return "muted desaturated blues and greys"
    if emotion.startswith(("intense", "confrontational")):
        return "high-contrast reds and blacks"
    if emotion.startswith(("serene", "tranquil")):
        return "soft pastels and light greens"
    if emotion.startswith(("excited", "energetic")):
        return "vibrant saturated colors"
    if emotion.startswith(("yearning", "wistful")):
        return "soft sepia and dusty golds"
    if emotion.startswith(("startling", "surprising")):
        return "bold high-contrast colors"
    if emotion.startswith(("awed", "sublime")):
        return "expansive cool blues and luminous whites"
    if emotion.startswith(("neutral",)):
        return "balanced natural tones"
    return "natural cinematic palette"


def _slugify_title(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug.strip())[:50]
    return slug or "untitled_scene_breakdown"


# ============================================================================
# Shot log + markdown output builders
# ============================================================================

def build_shot_log(data: dict) -> dict:
    """Build the per-shot reproducibility table (report #2 §5)."""
    shots = []
    for scene in data["scenes"]:
        mp = scene.get("motion_params", {})
        shots.append({
            "scene_number": scene["scene_number"],
            "title": scene["title"],
            "video_prompt": scene["video_prompt"],
            "negative_prompt": scene.get("negative_prompt", ""),
            "aspect_ratio": data["aspect_ratio"],
            "duration_sec": mp.get("duration_sec", 5),
            "fps": scene["motion_params"].get("fps", 24) if "fps" in mp else 24,
            "motion_strength": mp.get("motion_strength", 0.7),
            "seed": scene["seed"],
        })
    return {
        "aspect_ratio": data["aspect_ratio"],
        "resolution": "1920x1080",
        "fps": 24,
        "shots": shots,
    }


def build_prompts_markdown(data: dict) -> str:
    """Human-readable markdown summary."""
    lines = []
    lines.append(f"# {data['title']}")
    lines.append("")
    lines.append(f"*{len(data['scenes'])} scenes · style: {data['style']} · "
                 f"aspect ratio: {data['aspect_ratio']}*")
    lines.append("")

    for scene in data["scenes"]:
        s = scene["scene_number"]
        lines.append(f"## Scene {s}: {scene['title']}")
        lines.append("")
        if scene.get("text_segment"):
            lines.append(f"> {scene['text_segment']}")
            lines.append("")
        if scene.get("visual_description"):
            lines.append(f"{scene['visual_description']}")
            lines.append("")
        cine = scene.get("cinematography", {})
        if cine:
            lines.append(f"- Camera: {cine.get('camera', '—')}")
            lines.append(f"- Lens: {cine.get('lens', '—')}")
            lines.append(f"- Lighting: {cine.get('lighting', '—')}")
            lines.append(f"- Color palette: {cine.get('color_palette', '—')}")
            lines.append(f"- Composition: {cine.get('composition', '—')}")
            lines.append(f"- Mood: {cine.get('mood', '—')}")
            lines.append("")

        vp = scene.get("video_prompt", "")
        if vp:
            lines.append(f"**Video prompt (5s):** {vp}")
            lines.append("")

        cont = scene.get("continuity", {})
        if cont:
            lines.append(f"- Continuity contract: {cont.get('visual_contract_id', '—')}")
            lines.append(f"- Carried over: {', '.join(cont.get('carried_over', [])) or '—'}")
            lines.append("")

    return "\n".join(lines)


# ============================================================================
# Output writing
# ============================================================================

def write_outputs(data: dict, output_dir: Path) -> None:
    """Write scenes.json, shot_log.json and prompts.md into output_dir."""
    slug = _slugify_title(data["title"])
    out_path = output_dir / slug
    out_path.mkdir(parents=True, exist_ok=True)

    (out_path / "scenes.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    (out_path / "shot_log.json").write_text(
        json.dumps(build_shot_log(data), indent=2, ensure_ascii=False), encoding="utf-8")

    (out_path / "prompts.md").write_text(build_prompts_markdown(data), encoding="utf-8")


# ============================================================================
# CLI entry point
# ============================================================================

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Offline, language-agnostic scene breakdown and 5-second video-prompt generator.")
    p.add_argument("--text", help="Direct text input (any language).")
    p.add_argument("--file", help="Path to a .txt/.md file with text.")
    p.add_argument("--style", default="cinematic",
                   choices=["cinematic", "anime", "realistic", "watercolor",
                            "painterly", "theatrical", "noir"])
    p.add_argument("--aspect", default="16:9", choices=["16:9", "9:16", "1:1", "4:3"])
    p.add_argument("--max-scenes", type=int, default=12)
    p.add_argument("--output", default="prompts")
    p.add_argument("--force", action="store_true", help="Re-generate if output exists.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    text = ""
    if args.text is not None:
        text = args.text.strip()
    elif args.file is not None:
        try:
            text = Path(args.file).read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            return 2
    else:
        print("Error: provide --text or --file.", file=sys.stderr)
        return 2

    if not text:
        print("Error: empty input.", file=sys.stderr)
        return 2

    output_dir = Path(args.output)
    slug = _slugify_title(text[:60])
    out_path = output_dir / slug

    if out_path.exists() and not args.force:
        print(f"Output already exists at {out_path}. Use --force to overwrite.")
        return 0

    data = assemble_scenes(text, args.style, args.aspect, DEFAULT_NEGATIVE, args.max_scenes)
    write_outputs(data, output_dir)

    print(f"Generated {data['total_scenes']} scene(s).")
    print(f"Output: {out_path}/")
    for s in data["scenes"]:
        print(f"  Scene {s['scene_number']}: {s['title']} "
              f"(mood: {s['emotional_target']})")
    print("Files written: scenes.json, shot_log.json, prompts.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
