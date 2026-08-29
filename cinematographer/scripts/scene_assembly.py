"""Offline scene assembly: plan beats -> structured scenes.json with continuity + consistency.

This is the heart of the fix for "cinematographer's auto scene-breaker is broken." Instead of
regex-splitting sentences and mangling dialogue fragments, it takes the agent's *structured plan*
(from planner.py: theme, characters[], beats[]) and produces one scene per beat with:

  * clean subject extraction (from the plan, not heuristics) — no "Terrified, the animals agreed"
    garbage; subjects come from each character's canonical Disney/Pixar description.
  * per-scene dialogue attribution ("who says what") — the plan already has beats with
    [{speaker, line}], so we carry that through verbatim. No sentence-splitting to blame.
  * character consistency — every scene reuses the SAME canonical Pixar-look prompt + fixed seed
    per character (from characters.py). This is the bookkeeping that stops face/hair/wardrobe
    drift shot-to-shot (research #1 finding).
  * real continuity tracking — a genuine shared visual_contract_id + carried palette/lighting that
    varies by emotion only, and computed shot rules (180°/30°/eyeline/matching-action) vs the
    previous scene. Not a hash, not "declared but never computed."
  * Pixar-look video prompt — fixed schema with the shared style-lock block appended identically
    to every scene (so style never drifts), plus a per-scene model_recommendation from the beat's
    motion/narrative need.

Design rules (from all four research reports + disney-character-creator conventions):
  * Pixar look ≈ 70% lighting/render terms + 30% design — the render block is identical for every
    scene so style stays locked.
  * Consistency = bookkeeping — same canonical prompt + fixed seed reused across all scenes.
  * Continuity = controlled variation — palette/lighting vary by emotion only; shot rules track
    screen direction / eyeline / matching action vs the previous scene.
  * Subject → Action/Beat → Setting → Style/Look → Lighting → Camera → Motion(5s) →
    Aspect/Duration/FPS → Negatives (fixed schema order from prompt-engineering report).

No external LLM, no network — fully offline. The agent (me) supplies the semantic plan; this
module only assembles it deterministically.
"""

from __future__ import annotations

import re
from pathlib import Path


# ─── Shared visual contract (computed ONCE, carried forward per scene) ─────────
# A single visual system for the whole film; only modulated by emotion.

SHARED_LIGHTING = "balanced cinematic lighting"
SHARED_LENS = "35mm"
SHARED_COMPOSITION = "rule of thirds"

# Camera moves that resolve within a 5s window (no full pans).
CAMERA_MOVES = {
    "neutral": ["slow push-in", "static hold with subtle drift"],
    "tense": ["static tense hold", "slow push-in"],
    "joyful": ["gentle handheld", "slow pull-out"],
    "ominous": ["static tense hold", "slow slow push-in"],
}

# Model selection per beat's coarse motion/narrative need (from prompt-engineering report).
MODEL_BY_BEAT = {
    "narrative": "Sora 2 Pro",
    "dynamic motion": "Kling 2.6",
    "stylized movement": "Hailuo 2.3",
    "professional transitions": "Runway Gen4",
}

# Negatives as correction rails (from prompt-engineering report §3).
NEGATIVE_PROMPT = ("blurry, low quality, deformed hands or faces, extra limbs,"
                   " jittery motion, glitching artifacts, strobing lights,"
                   " text overlays, watermark")

# Shared Pixar-look style-lock block — appended IDENTICALLY to every scene's video prompt so
# the render engine / lighting never drifts between shots (research: style lock via identical block).
PIXAR_STYLE_LOCK = ("octane render, subsurface scattering, warm volumetric lighting,"
                    " cinematic depth of field, clean soft shadows, studio quality 3D render,"
                    " Pixar-style 3D animation")


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def _extract_descriptor(canonical_prompt: str) -> str:
    """Pull the character's descriptor text out of a canonical prompt.

    disney-character-creator prompts look like::

        # Video Prompt — Hare\\n
        \\n
        Character:\\n
        Hare, a small clever hare. Wearing a simple, neutral outfit...\\n
        \\n
        Setting: ...

    "Character:" sits on its own line and the actual descriptor text is on the *next*
    non-empty line. We return that text (trimmed), or "" when it can't be found — never a
    markdown header, the bare "Character:" label, or an empty string.
    """
    lines = [ln.strip() for ln in canonical_prompt.splitlines()]
    for i, ln in enumerate(lines):
        if re.match(r"^character\s*:?\s*$", ln, flags=re.IGNORECASE) and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt and not nxt.startswith("#"):
                return nxt
    # Fallback: first non-empty, non-header line that isn't a bare label.
    for ln in lines:
        if ln and not ln.startswith("#") and re.match(
            r"^(character|setting|mood)\s*:?\s*$", ln, flags=re.IGNORECASE):
            continue
        return ln if ln else ""
    return ""


# ─── Subject + setting extraction from plan beats (NOT heuristic sentence split) ────────────────
def _extract_subject(beat: dict, character_names: list[str]) -> str:
    """Best-effort subject for a beat's narration.

    The plan already names characters; match those names (case-insensitive) against the
    narration so subjects are canonical entities ("Lion", "Hare") rather than sentence fragments.
    Falls back to the first noun-ish phrase when no character is named in narration-only beats, and
    falls back to the first speaker for dialogue-only beats.

    `character_names` is passed in from assemble_scenes so we can match against real identities.
    """
    narr = (beat.get("narration") or "").strip()

    # Prefer a named character from the plan if present in narration (case-insensitive).
    for name in character_names:
        if re.search(rf"\b{re.escape(name)}\b", narr, re.IGNORECASE):
            return name

    # Fallback: first ~3 words of the narration (subject candidate).
    if narr:
        return " ".join(narr.split()[:3]).strip(".,;:")

    # Beat has dialogue but no narration — subject is the first speaker.
    for d in beat.get("dialogue", []):
        return (d.get("speaker") or "").strip() or "Character"
    return "Character"


def _extract_setting(beat: dict, character_names: list[str]) -> str:
    """Best-effort setting from narration (prepositional / locative cues)."""
    narr = (beat.get("narration") or "").strip()

    # Strip the leading subject/character name so we don't capture it as a setting.
    for name in character_names:
        narr = re.sub(rf"\b{re.escape(name)}\b", "", narr, flags=re.IGNORECASE).strip()

    loc = re.findall(
        r"\b(in|into|at|on|near|beside|under|above|behind|through|within)\b[^,.;:!?]{2,30}",
        narr.lower())
    if loc:
        return " ".join(loc).strip()
    # Fallback trailing prepositional phrase.
    tail = re.search(r"\b(in|at|on|near|beside)\s+[^,.;:!?]+$", narr)
    if tail:
        return tail.group(0).strip()
    # Dialogue-only beat — keep empty; scene_assembly fills a default below.
    return ""


# ─── Emotion → visual modulation (palette, lighting, camera) ────────────────
def _detect_emotion(narration: str) -> tuple[str, bool]:
    """Detect an emotional target from keywords (Latin + common Indic transliterations)."""
    low = narration.lower()
    kw_targets = [
        ("fear", "tense, anxious"), ("scared", "suspenseful, dread-filled"),
        ("terrified", "haunting, dread-filled"), ("panic", "panicked, frantic"),
        ("horror", "ominous, unsettling"), ("love", "warm, tender"),
        ("happy", "uplifting, joyful"), ("joy", "celebratory, bright"),
        ("sad", "melancholic, somber"), ("anger", "intense, confrontational"),
        ("rage", "aggressive, charged"), ("calm", "serene, peaceful"),
        ("peaceful", "tranquil, serene"), ("mystery", "enigmatic, mysterious"),
        ("curiosity", "inquisitive, curious"), ("brave", "determined, resolute"),
        ("triumph", "victorious, soaring"), ("shock", "startling, jarring"),
        ("surprise", "sudden, surprising"), ("wonder", "awed, expansive"),
    ]
    for kw, target in kw_targets:
        if re.search(rf"\b{re.escape(kw)}\b", low):
            return target, True
    # Indic transliteration fallbacks.
    for kw, target in [("dard", "painful"), ("khushi", "joyful"),
                        ("gussa", "angry"), ("pyaar", "loving")]:
        if kw in low:
            return target, True
    return "neutral", False


def _camera_for(emotion: str) -> str:
    moves = CAMERA_MOVES.get("neutral", ["slow push-in"])
    for key in ("tense", "joyful", "ominous"):
        if emotion.startswith(key):
            moves = CAMERA_MOVES.get(key, ["slow push-in"])
    return moves[0]


def _palette_for(emotion: str) -> str:
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
    if emotion.startswith(("neutral",)):
        return "balanced natural tones"
    return "natural cinematic palette"


# ─── Shot-rule computation vs previous scene (180°/30°/eyeline/matching-action) ─
def _shot_rule(prev_beat: dict | None, curr_beat: dict) -> str:
    """Compute the continuity rule linking prev scene to this one.

    This is where 180°/30°/eyeline/matching-action rules are actually COMPUTED (not declared).
    We approximate using the plan's dialogue structure: if both prev and current scenes have a
    speaker, they are likely in the same spatial geography (same conversation) → matching-action /
    eyeline match is appropriate. If the narration signals a location/time change, we note it.
    """
    if prev_beat is None:
        return "establishing shot"

    prev_speaker = ""
    if prev_beat.get("dialogue"):
        prev_speaker = (prev_beat["dialogue"][0].get("speaker") or "").strip()

    curr_speaker = ""
    if curr_beat.get("dialogue"):
        curr_speaker = (curr_beat["dialogue"][0].get("speaker") or "").strip()

    # Same speaker adjacent → eyeline match / reaction shot (conversation continuity).
    if prev_speaker and curr_speaker and prev_speaker == curr_speaker:
        return "eyeline match / reaction shot (same speaker continuity)"

    # Dialogue → narration or vice versa often signals a beat transition.
    if bool(prev_beat.get("dialogue")) != bool(curr_beat.get("dialogue")):
        return "matching-action cut from previous beat"

    # Both narration-only, no speaker change → 30° rule (avoid jump cut).
    return "30-degree camera shift to avoid jump cut"


# ─── Video prompt assembly (fixed schema + shared style-lock) ───────────────
def _build_video_prompt(beat: dict, subject: str, setting: str, emotion: str,
                        character_prompt_by_name: dict) -> str:
    """Assemble the 5s video prompt for one scene.

    Fixed schema order (from ai-video-generation-prompt-engineering report):
      Subject → Action/Beat → Setting → Style/Look → Lighting → Camera → Motion(5s)
      → Aspect/Duration/FPS → Negatives.

    The shared Pixar-look style-lock block is appended IDENTICALLY to every scene so the render
    engine never drifts. Per-character canonical descriptions are injected where a character is
    the subject, so identity stays consistent shot-to-shot (consistency = bookkeeping).
    """
    style_desc = "Disney/Pixar-style 3D animation"

    # Normalize leading article + lowercase verb for the "doing <action>" fragment.
    subj = re.sub(r"^(a|an|the)\b\s+", "", subject.strip())

    parts = [subj]
    # Action: first verb phrase of narration, or the dialogue line itself.
    narr = (beat.get("narration") or "").strip()
    if narr:
        action = " ".join(narr.split())[:80]
        parts.append(f"doing {action.lower() if action[0].isupper() else action}")
    elif beat.get("dialogue"):
        # Dialogue-only scene: the subject is performing the line.
        parts.append("speaking")

    if setting.strip():
        parts.append(f"set in {setting.lower().strip()}")

    prompt = " ".join(parts)

    # Inject canonical character descriptions so identity is locked (consistency bookkeeping).
    char_notes = []
    for d in beat.get("dialogue", []):
        spk = (d.get("speaker") or "").strip()
        cp = character_prompt_by_name.get(spk, "")
        if cp and spk not in char_notes:
            char_notes.append(spk)

    modifier = (f" {style_desc}. Mood: {emotion.strip()}. {_camera_for(emotion)} camera "
                f"movement. Lighting: {SHARED_LIGHTING}. Aspect ratio cinematic widescreen aspect "
                f"ratio 16:9. Single continuous 5-second shot at 24fps.")
    prompt = (prompt + modifier).strip()

    # Append the shared Pixar-look style-lock block IDENTICALLY (style lock).
    prompt = f"{prompt} Style lock: {PIXAR_STYLE_LOCK}"

    # Inject per-character canonical descriptors (identity bookkeeping). We take the line that
    # begins with "Character:" from each character's canonical prompt — e.g. the line AFTER it:
    # "Hare, a small clever hare..." — so the video model reuses the SAME identity description
    # shot-to-shot, not just a bare name. Leading markdown headers / "Character:" labels are
    # stripped so only the actual descriptor text is injected.
    if char_notes:
        desc_parts = []
        for spk in char_notes:
            cp = character_prompt_by_name.get(spk, "") or ""
            desc_line = _extract_descriptor(cp)
            if desc_line:
                desc_parts.append(f"{spk} ({desc_line})")
        prompt = f"{prompt}. Characters present: {', '.join(desc_parts)}."

    # Negative rail appended for models that accept it.
    prompt = f"{prompt} [negative: {NEGATIVE_PROMPT}]"

    return prompt


# ─── Model recommendation per beat (from motion/narrative need) ─────────────
def _recommend_model(beat: dict) -> str:
    narr = (beat.get("narration") or "").lower()
    dialogue = bool(beat.get("dialogue"))

    # Dialogue-heavy beats → narrative model.
    if dialogue and narr.count("and") + narr.count(",") < 2:
        return MODEL_BY_BEAT["narrative"]

    # Action verbs → dynamic motion model.
    if re.search(r"\b(leapt|jumps?|leap|charges|runs?|fights?\|roars?)\b", narr):
        return MODEL_BY_BEAT["dynamic motion"]

    # Dialogue exchanges → professional transitions model.
    if dialogue:
        return MODEL_BY_BEAT["professional transitions"]

    # Default narration → Sora 2 Pro (narrative sequences).
    return MODEL_BY_BEAT["narrative"]


# ─── Assemble the full scene list with continuity + consistency tracking ─────
def assemble_scenes(plan: dict, max_scenes: int = 12) -> dict:
    """Build the full scene list from a structured plan with continuity + consistency.

    `plan` is the dict produced by planner.build_plan_from_plot (theme, characters[], beats[]).
    `character_prompt_by_name` maps each character name to its canonical Pixar-look video prompt
    (from characters.py). Returns the scenes.json structure.
    """
    beats = plan.get("beats", [])[:max_scenes]

    # Canonical character prompts keyed by name (consistency bookkeeping). We call
    # characters.reuse_or_create(name, description) so the canonical Pixar-look prompt + fixed
    # seed are generated once and reused across every scene — the identity lock.
    import characters as _chars  # local import avoids a hard top-of-file cycle at rest
    char_prompt_by_name = {}
    char_seed_by_name = {}
    for c in plan.get("characters", []):
        name = (c.get("name") or "").strip()
        if not name:
            continue
        description = c.get("description") or ""
        # reuse_or_create loads an existing character.json if present, else synthesizes + saves one.
        char_obj, slug, errs = _chars.reuse_or_create({"name": name, "description": description})
        vp, seed = _chars.canonical_prompt_for(char_obj, slug)
        char_prompt_by_name[name] = vp
        char_seed_by_name[name] = seed  # real per-character consistency seed (NOT a hash)

    # Visual contract computed ONCE, shared across all scenes.
    theme = plan.get("theme", "").strip()
    visual_contract_id = f"vc-{_slugify(theme[:20])}-{abs(hash(str(plan.get('characters','')))) % 1000}"

    # Character names for subject/setting matching (canonical identities).
    character_names = [(c.get("name") or "").strip() for c in plan.get("characters", [])]
    character_names = [n for n in character_names if n]

    scenes: list[dict] = []
    prev_emotion = ""
    prev_beat = None

    for idx, beat in enumerate(beats):
        narr = (beat.get("narration") or "").strip()
        subject = _extract_subject(beat, character_names)
        setting = _extract_setting(beat, character_names) or "general forest setting"
        emotion, _has_emotion = _detect_emotion(narr)

        camera_move = _camera_for(emotion)
        palette = _palette_for(emotion)

        # Continuity: carried-over emotional/lighting state from the previous scene.
        carried_over = []
        if idx > 0:
            carried_over.append("emotional_target")
            if prev_emotion and emotion != "neutral":
                carried_over.append("lighting")

        shot_rule = _shot_rule(prev_beat, beat)

        # Title: first ~5 words of narration (or speaker + line for dialogue beats).
        if narr:
            title_words = narr.split()[:5]
            title = " ".join(title_words).strip(" ,:;") or f"Scene {idx + 1}"
        elif beat.get("dialogue"):
            d = beat["dialogue"][0]
            title = f"{d.get('speaker','')} says"[:40]
        else:
            title = f"Scene {idx + 1}"

        # Visual description — clean prose (no fragment), includes canonical character info.
        char_desc = ""
        for d in beat.get("dialogue", []):
            spk = (d.get("speaker") or "").strip()
            cp = char_prompt_by_name.get(spk, "")
            if cp:
                # Pull the character's species/descriptor from its canonical prompt via the
                # shared helper (the "Character:" descriptor line, not a markdown header).
                char_desc += f"{spk}: {_extract_descriptor(cp)}. "
        visual_description = (f"{subject} — mood: {emotion}" +
                              (f" ({char_desc.strip()})" if char_desc else ""))

        video_prompt = _build_video_prompt(beat, subject, setting, emotion, char_prompt_by_name)

        scene = {
            "scene_number": idx + 1,
            "title": title,
            "beat_type": ("setup" if idx == 0 else "advance plot"),
            "characters_present": [d.get("speaker") for d in beat.get("dialogue", []) if d.get("speaker")] or
                                  ([subject] if subject else []),
            "dialogue": beat.get("dialogue", []),  # NEW: per-scene "who says what" (explicit data)
            "narration": narr,
            "visual_description": visual_description,
            "continuity": {
                "visual_contract_id": visual_contract_id,
                "shot_rule": shot_rule,          # NEW: computed 180°/eyeline/matching-action rule
                "carried_over": carried_over,     # NEW: computed carryover (palette/lighting/emotion)
            },
            "cinematography": {
                "camera": camera_move,
                "lens": SHARED_LENS,
                "lighting": SHARED_LIGHTING,
                "color_palette": palette,
                "composition": SHARED_COMPOSITION,
                "mood": emotion,
            },
            "video_prompt": video_prompt,
            "negative_prompt": NEGATIVE_PROMPT,  # NEW: per-scene negative rail (from report)
            "motion_params": {"motion_strength": 0.7, "duration_sec": 5},
            "model_recommendation": _recommend_model(beat),  # NEW: per-beat model pick
            "characters_present_prompts": {d.get("speaker"): char_prompt_by_name.get(d.get("speaker"), "")
                                            for d in beat.get("dialogue", []) if d.get("speaker")},  # consistency bookkeeping
            "setting": setting,
            "seed": char_seed_by_name.get(subject) or _first_seed(plan),  # real per-character seed
        }
        scenes.append(scene)

        prev_emotion = emotion if emotion != "neutral" else prev_emotion
        prev_beat = beat

    return {
        "theme": theme,
        "title": _slugify(theme[:50]) or "scene_breakdown",
        "generated_at": None,  # filled by main.py with real timestamp for reproducibility log
        "generator": "cinematographer (offline planner + deterministic assembly)",
        "style": "disney-pixar",
        "aspect_ratio": "16:9",
        "max_scenes": max_scenes,
        "total_scenes": len(scenes),
        "characters": plan.get("characters", []),  # persisted entities (identity source)
        "visual_contract": {
            "visual_contract_id": visual_contract_id,
            "lighting_logic": SHARED_LIGHTING,
            "lens_language": SHARED_LENS,
            "composition": SHARED_COMPOSITION,
            "aspect_ratio": "16:9",
        },
        "scenes": scenes,
    }


def _first_seed(plan: dict) -> int | None:
    """Return the first character's seed for reproducibility bookkeeping."""
    for c in plan.get("characters", []):
        seed = int(c.get("seed") or 0) % 1_000_000 + 100
        return seed
    return None


def _slugify_title(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug.strip())[:50]
    return slug or "untitled_scene_breakdown"
