#!/usr/bin/env python3
"""Script Audio Generator — offline, English-only dialogue-to-audio pipeline.

Takes a movie/short-story script and produces per-character dialogue audio:

    1. Scene-break      (structural heuristics, language-agnostic)
    2. Dialogue extract (quoted speech + speaker resolution)
    3. Character + gender detection (pronoun tracking + name lexicon)
    4. Voice-casting   (auto gendered Kokoro voice + mood-derived speed)
    5. Audio generation (reuses kokoro-tts/scripts/tts.py logic, per-scene + master)

Fully offline — no agy / LLM CLI / network. English only (Kokoro is phoneme-based
for English/Indian-English; non-Latin dialogue sounds poor, use kannada-tts instead).

Usage:
    python3 audio_gen.py --text "\"Are you coming?\" Dev asked."
    python3 audio_gen.py --file script.txt
    python3 audio_gen.py --cinematographer prompts/<slug>/scenes.json
    python3 audio_gen.py --file script.txt --cast "Dev:am_adam,Priya:af_heart"
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Kokoro-tts skill lives as a sibling; resolve its TTS script relative to ours.
SKILL_DIR = Path(__file__).resolve().parent.parent  # script-audio-generator/ (scripts is the child)
KOKORO_TTS_SCRIPT = SKILL_DIR.parent / "kokoro-tts" / "scripts" / "tts.py"

# ---------------------------------------------------------------------------
# Mood -> speed table (see references/vocals.md for the full list)
# ---------------------------------------------------------------------------
MOOD_SPEED = {
    "serene": 0.85, "tranquil": 0.85, "calm": 0.85, "peaceful": 0.85,
    "tender": 0.87, "loving": 0.87, "nostalgic": 0.87,
    "melancholic": 0.82, "somber": 0.82, "tearful": 0.82,
    "hopeful": 0.88, "wistful": 0.88, "yearning": 0.88,
    "joyful": 0.98, "celebratory": 0.98, "excited": 0.98,
    "neutral": 0.9,
    "tense": 1.05, "anxious": 1.05, "suspenseful": 1.05,
    "fear": 1.08, "dread": 1.08, "frightened": 1.08,
    "anger": 1.12, "rage": 1.12, "aggressive": 1.12, "intense": 1.12,
    "panic": 1.15, "frantic": 1.15,
}
DEFAULT_SPEED = 0.9


# Emotional keywords -> mapped target (subset of cinematographer's list, English-only).
EMOTION_KEYWORDS = [
    ("fear", "tense"), ("scared", "tense"), ("terrified", "dread"),
    ("panic", "panic"), ("horror", "dread"), ("frightened", "fear"),
    ("anger", "anger"), ("rage", "rage"), ("aggressive", "anger"),
    ("tense", "tense"), ("anxious", "anxious"), ("suspenseful", "suspenseful"),
    ("love", "tender"), ("happy", "joyful"), ("joy", "joyful"),
    ("sad", "melancholic"), ("grief", "somber"), ("tearful", "tearful"),
    ("melancholic", "melancholic"), ("somber", "somber"),
    ("calm", "serene"), ("peaceful", "serene"), ("tranquil", "serene"),
    ("tender", "tender"), ("loving", "tender"), ("nostalgic", "nostalgic"),
    ("hopeful", "hopeful"), ("wistful", "wistful"), ("yearning", "yearning"),
    ("joyful", "joyful"), ("celebratory", "celebratory"), ("excited", "excited"),
    ("frantic", "frantic"),
]


def detect_emotion(text: str) -> str:
    """Detect a scene emotion from emotional keywords (English-only, case-insensitive).

    Returns the strongest match; "neutral" when nothing matches.
    """
    low = (text or "").lower()
    for kw, target in EMOTION_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", low):
            return target
    return "neutral"


def speed_for_emotion(emotion: str) -> float:
    """Map a scene emotion string to a Kokoro speed. Case-insensitive prefix match."""
    low = (emotion or "").lower()
    for key, val in MOOD_SPEED.items():
        if low.startswith(key) or key in low:
            return val
    return DEFAULT_SPEED


# ---------------------------------------------------------------------------
# 1. Scene break (structural heuristics) — mirrors cinematographer logic
# ---------------------------------------------------------------------------
SCENE_CHANGE_PATTERNS = [
    r"\bthen\b", r"\band then\b", r"\bafter that\b", r"\bfinally\b",
    r"\bmeanwhile\b", r"\bsubsequently\b", r"\blater\b",
    r"\bjust then\b", r"\bafter (a|the) ", r"\byears? later\b",
    r"\bdays? later\b", r"\bmoments? later\b", r"\bhours? later\b",
    r"(\d+|midnight|morning\slater)\b.*",
]


def split_into_scenes(text: str, max_scenes: int = 12) -> list[str]:
    """Split text into scene blocks using sentence grouping + transition detection.

    Quoted speech is treated as an opaque token so punctuation *inside* dialogue
    (e.g. "Thank you so much.") does not wrongly split a sentence into its own scene.
    A sentence boundary is an unquoted . ! ? — or a universal transition connector.
    """
    norm = text.replace("\u0964", ". ")  # Indic danda -> period

    # Tokenize: a quoted segment is one opaque token; otherwise run of non-sentence
    # punctuation characters. This lets us split only on *unquoted* . ! ? and keep
    # the original text intact for each sentence.
    TOKEN_RE = re.compile(r'"[^"]*"|\'[^\']*\'|[.!?]+|\S+')

    sentences: list[str] = []
    current: list[str] = []
    for tok in TOKEN_RE.findall(norm):
        stripped = tok.strip()
        if not stripped:
            continue
        current.append(stripped)
        # A sentence ends at an unquoted terminal mark.
        if tok in {".", "!", "?"} or re.fullmatch(r"[\.\!\?]+", tok):
            if current:
                sentences.append(" ".join(current).strip())
                current = []

    # Any leftover tokens (no trailing terminal mark) form the final sentence.
    if current:
        sentences.append(" ".join(current).strip())

    # Collapse whitespace-only / empty artifacts.
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    blocks = [[sentences[0]]]
    for prev, sent in zip(sentences[:-1], sentences[1:]):
        low = sent.lower()
        if any(re.search(p, low) for p in SCENE_CHANGE_PATTERNS):
            blocks.append([sent])
        elif len(" ".join(blocks[-1])) + len(sent) <= 260:
            # Keep scenes compact (each ~5s of dialogue).
            blocks[-1].append(sent)
        else:
            blocks.append([sent])

    if len(blocks) > max_scenes:
        tail = " ".join(" ".join(b) for b in blocks[max_scenes - 1:])
        blocks = blocks[:max_scenes - 1] + [tail.split()]

    return [" ".join(b) if isinstance(b, list) else b for b in blocks]


# ---------------------------------------------------------------------------
# 2. Dialogue extraction — quoted speech + speaker resolution
# ---------------------------------------------------------------------------

# Matches: "quoted text" — Dev said / Dev:"quote" / <Dev> quote
_SPEAKER_TAG = re.compile(
    r'(?:"([^"]+)"|\'([^\']+)\'\|(?:<<[^\\>>]+>>)?)'      # the quoted line
    r'\s*(?:[-–—]\s*)?'                                   # optional " —"
    r'(?:said|asked|whispered|shouted|muttered|growled'  # speech verbs
    r'\b[a-z]+)?\s*'                                     # optional verb...
    r'(\[[^\\]]+\])?'                                    # ...or a [Name] tag...
    r'([A-Z][a-zA-Z.\'\-]{1,25})?'                      # ...or a Capitalized name
)

# Narration verbs that tell us WHO is speaking (the subject before/after).
_SPEAKING_VERBS = {"said", "asked", "replied", "whispered", "shouted",
                   "muttered", "growled", "answered", "exclaimed"}

# Common nouns -> gender (for boy/girl/young man, etc.).
_COMMON_NOUN_GENDER = {
    "boy": "male", "girl": "female", "young man": "male",
    "young woman": "female", "he": "male", "she": "female",
}


def _narration_speaker(narration: str, direction: str = "after") -> tuple[str, bool] | None:
    """Find the speaker in a narration segment (before/after a quote).

    Returns ("male"/"female", True) if we can map it to gender, else None.
    Handles: "the boy said", "she replied", "a young man asked".

    direction="after": narration appears AFTER the quote -> use the FIRST
        speaking verb (closest to that quote). direction="before": narration
        appears BEFORE the quote -> use the LAST speaking verb (closest).
    """
    low = narration.lower()
    matches = list(re.finditer(
        r'(?:the\s+)?([a-z ]{1,20})\s+(said|asked|replied|whispered|shouted'
        r'|muttered|growled|answered|exclaimed)', low))
    if not matches:
        return None
    m = (matches[-1] if direction == "before" else matches[0])
    subject = m.group(1).strip()
    # Map common nouns / pronouns to gender.
    for token, gender in _COMMON_NOUN_GENDER.items():
        if subject == token or subject.endswith(" " + token) or re.search(
                r"\b" + re.escape(token) + r"\b", subject):
            return (gender, True)
    return None


def extract_dialogue(scene_text: str, known_names: list[str]) -> list[dict]:
    """Pull quoted speech + resolve each line to a speaker.

    Uses re.split on quotes so narration parts sit between them:
        [narr, quote, narr, quote, ..., arr]
    Each narration part is gender-detected (boy->male, girl->female, he/she) and
    attributed to the quote before it (e.g. "the boy said,") or after it
    (e.g. '," the boy said'). Returns list of {"speaker": "male"/"female",
    "line": str}. Unattributed quotes -> "".

    Quotes are stripped of their surrounding quotation marks so the line is clean
    dialogue with no leading/trailing quote characters.
    """
    lines: list[dict] = []
    clean = (scene_text.replace("\u201c", '"').replace("\u201d", '"')
                   .replace("\u2018", "'").replace("\u2019", "'"))

    # Split keeping quotes as separate tokens: [narr, quote, narr, quote, ...].
    parts = re.split(r'("[^"]*"|\'[^\']*\')', clean)
    # parts: even indices (0,2,...) are narration; odd indices (1,3,...) are quotes.
    # Drop the trailing empty string from split when text ends after a quote.
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]

    # Determine the gender each narration part implies.
    narr_genders: list[str | None] = []  # aligned to even indices (narration parts)
    narr_indices: list[int] = []         # actual index in `parts` for each narration part
    for idx, p in enumerate(parts):
        if idx % 2 == 0:  # narration part
            gender = _narration_speaker(p)
            narr_genders.append(gender[0] if gender else None)
            narr_indices.append(idx)

    # For each quote (odd index), find the nearest narration part before and after,
    # and take that gender. Prefer nearer; if tie or none, "".
    for q_idx in range(1, len(parts), 2):
        quote = parts[q_idx].strip().strip('"').strip("'").strip()
        if not quote:
            continue

        # Nearest narration before this quote (largest narr_idx < q_idx).
        best_before_i = None
        for ng_i, narr_idx in enumerate(narr_indices):
            if narr_idx < q_idx:
                best_before_i = ng_i

        # Nearest narration after this quote (smallest narr_idx > q_idx).
        best_after_i = None
        for ng_i, narr_idx in enumerate(narr_indices):
            if narr_idx > q_idx:
                best_after_i = ng_i
                break  # first match is nearest (indices are ascending)

        gender: str | None = None
        # Prefer the immediately adjacent narration (distance 1 part apart), but only
        # if that narration actually yields a gender; otherwise fall through to the
        # other side so an attribution like ', "the boy said"' is still picked up.
        if best_before_i is not None and narr_indices[best_before_i] == q_idx - 1:
            g = _narration_speaker(parts[narr_indices[best_before_i]], direction="before")
            if g is not None:
                gender = g[0]
        if gender is None and best_after_i is not None \
                and narr_indices[best_after_i] == q_idx + 1:
            g = _narration_speaker(parts[narr_indices[best_after_i]], direction="after")
            if g is not None:
                gender = g[0]

        lines.append({"speaker": gender or "", "line": quote})
    return lines


# ---------------------------------------------------------------------------
# 3. Character + gender detection (offline)
# ---------------------------------------------------------------------------

# Small first-name -> gender lexicon for common English + Indian names.
_NAME_GENDER = {
    # Female first names (Indian)
    "priya": "female", "anjali": "female", "meera": "female", "kavita": "female",
    "lakshmi": "female", "sarala": "female", "devika": "female", "nandini": "female",
    "ananya": "female", "kavya": "female", "pooja": "female", "sneha": "female",
    # Female first names (Western)
    "mary": "female", "elizabeth": "female", "sarah": "female", "grace": "female",
    "clara": "female", "victoria": "female", "emma": "female", "lily": "female",
    "anna": "female", "isabella": "female", "maya": "female",
    # Male first names (Indian)
    "dev": "male", "ram": "male", "ravi": "male", "arjun": "male",
    "krishna": "male", "vikram": "male", "arav": "male", "adhvik": "male",
    "karan": "male", "rohan": "male", "samarth": "male", "vikrant": "male",
    # Male first names (Western)
    "john": "male", "james": "male", "william": "male", "robert": "male",
    "michael": "male", "david": "male", "thomas": "male", "oliver": "male",
    "henry": "male", "alexander": "male", "charles": "male",
}



def collect_characters(text: str) -> list[str]:
    """Collect proper-noun character names from the scene text.

    Heuristic: Capitalized words of length 2-15 that are not sentence-initial
    (appear mid-sentence) and aren't common stopwords. Deduped, order-preserving.
    """
    stop = {
        "she", "he", "they", "we", "i", "you", "it", "was", "were", "are",
        "had", "has", "have", "will", "would", "should", "could", "can",
        "this", "that", "these", "those", "there", "here", "into", "onto",
        "upon", "with", "from", "about", "their", "them", "her", "him",
        # Sentence-initial / connective words that are capitalized but not names.
        "the", "but", "and", "however", "meanwhile", "then", "after",
        "before", "when", "as", "so", "because", "although", "since",
        "therefore", "thus", "nevertheless", "still", "yet", "only",
    }
    names: list[str] = []
    seen_lower: set[str] = set()
    # Sentence-initial positions to skip (these capitalize the first word only).
    initials = set(re.findall(r"(?:^|[.!?])\s+([A-Z][a-zA-Z.\'\-]{1,24})", text))
    for tok in re.findall(r"\b([A-Z][a-zA-Z.\'\-]{1,24})\b", text):
        low = tok.lower()
        if low in stop or re.match(r"^\d+$", tok):
            continue
        # Skip pure-acronyms (all caps, length > 2).
        if len(tok) > 2 and tok.isupper():
            continue
        # Skip sentence-initial words (not true character names).
        if tok in initials and low not in _NAME_GENDER:
            continue
        if low not in seen_lower:
            seen_lower.add(low)
            names.append(tok)
    return names


# ---------------------------------------------------------------------------
# 4. Voice-casting (auto gendered Kokoro)
# ---------------------------------------------------------------------------

GENDER_VOICES = {
    "male":   ("im_nicola", ["if_sarath", "am_jacob"]),
    "female": ("if_sara",   ["af_lily", "am_ruth"]),
}


def cast_voice(gender: str, overrides: dict[str, str]) -> tuple[str, bool]:
    """Return (voice, cast_from_override). Auto-detect gendered voice by default."""
    if gender in overrides:
        return overrides[gender], True
    voices = GENDER_VOICES.get(gender, ("", [""]))
    return (voices[0] if voices[0] else ""), False


# ---------------------------------------------------------------------------
# 5. Cinematographer scenes.json reader (integration)
# ---------------------------------------------------------------------------

def read_cinematographer_scenes(path: Path, max_scenes: int) -> list[dict]:
    """Read a cinematographer scenes.json; return normalized scene dicts.

    Each output: {"scene_number", "text_segment", "characters", "emotional_target"}.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    scenes: list[dict] = []
    for i, sc in enumerate(data.get("scenes", [])[:max_scenes], start=1):
        scenes.append({
            "scene_number": sc.get("scene_number", i),
            "text_segment": sc.get("text_segment") or sc.get("visual_description", ""),
            "characters": list(sc.get("characters", [])),
            "emotional_target": sc.get("emotional_target") or "",
        })
    return scenes


# ---------------------------------------------------------------------------
# Build full scene dataset
# ---------------------------------------------------------------------------

def build_scenes(text: str, max_scenes: int) -> list[dict]:
    """Run the full offline pipeline per scene. Returns normalized scene dicts."""
    scenes = []
    for i, block in enumerate(split_into_scenes(text, max_scenes=max_scenes), start=1):
        dialogue = extract_dialogue(block, [])
        names = collect_characters(block) if not dialogue else []
        emotion = detect_emotion(block)
        scenes.append({
            "scene_number": i,
            "text_segment": block.strip()[:280],
            "dialogue": dialogue,
            "characters": names,
            "emotional_target": emotion,   # used by manifest + speed lookup below
            "speed": DEFAULT_SPEED,        # filled from emotion right after this loop
        })

    # Fill per-scene speed from detected emotion (one pass, avoids re-deriving).
    for sc in scenes:
        sc["speed"] = speed_for_emotion(sc.get("emotional_target", "neutral"))

    return scenes


# ---------------------------------------------------------------------------
# Manifest + output writing
# ---------------------------------------------------------------------------

def build_manifest(data: dict) -> str:
    """Human-readable cast + dialogue summary."""
    out = []
    out.append(f"# {data['title']} — Dialogue Audio")
    out.append("")
    out.append(
        f"*{len(data['scenes'])} scenes · "
        f"{data.get('generator', 'script-audio-generator')}*")
    out.append("")

    # Cast table.
    if data.get("cast"):
        out.append("## 🎭 Voice Cast")
        out.append("")
        for char, info in data["cast"].items():
            tag = " (override)" if info.get("from_override") else ""
            gender = info.get("gender", "?")
            out.append(f"- **{char}** → `{info['voice']}` ({gender}){tag}")
        out.append("")

    out.append("## 🎬 Scenes")
    out.append("")
    for sc in data["scenes"]:
        parts = []
        for d in sc.get("dialogue", []):
            speaker = d["speaker"] or "?"
            parts.append(f"{speaker}: {d['line']}")
        line = " | ".join(parts) if parts else "> (no dialogue detected)"
        speed = sc.get("speed", DEFAULT_SPEED)
        out.append(f"### Scene {sc['scene_number']} — mood: "
                   f"{sc.get('emotional_target', '—')} (speed {speed:.2f})")
        out.append("")
        if line.startswith(">"):
            out.append(line)
        else:
            for p in parts:
                out.append(f"> {p}")
        out.append("")

    out.append("---")
    out.append("_Offline heuristic pipeline. Gender/tone detection is best-effort; "
               "inspect the manifest and cast to correct misassigned lines._")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Audio generation via kokoro-tts script + ffmpeg concat
# ---------------------------------------------------------------------------

def tts_line(line: str, voice: str, speed: float, fmt: str, out_path: Path) -> bool:
    """Run the kokoro-tts script for a single line, persisting to out_path.

    Returns True on success (file written), False otherwise.
    """
    if not KOKORO_TTS_SCRIPT.exists():
        print(f"✗ kokoro-tts script not found at {KOKORO_TTS_SCRIPT}. "
              f"Install/clone the kokoro-tts skill first.", file=sys.stderr)
        return False

    cmd = [sys.executable, str(KOKORO_TTS_SCRIPT), line, "-v", voice,
           "--max-segment", "380"]
    if fmt == "mp3":
        cmd += ["-f", "mp3"]
    cmd += ["-o", str(out_path)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            print(f"  ✗ TTS failed for voice '{voice}': {proc.stderr[:200]}",
                  file=sys.stderr)
            return False
        if not out_path.exists():
            print(f"  ✗ Expected output {out_path} was not created.", file=sys.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  ✗ TTS timed out for voice '{voice}.", file=sys.stderr)
        return False


def concat_with_ffmpeg(wav_files: list[Path], master_out: Path) -> bool:
    """Concatenate audio files into a single master via ffmpeg. Returns success."""
    if not wav_files:
        return False
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for fp in wav_files:
            f.write(f"file '{fp}'\n")
        concat_list = f.name
    try:
        if master_out.suffix == ".mp3":
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                            "-i", concat_list, "-c", "copy", str(master_out)],
                           check=True, capture_output=True)
        else:
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                            "-i", concat_list, "-c", "copy", str(master_out)],
                           check=True, capture_output=True)
        return True
    except Exception as e:  # noqa: BLE001 - surface any ffmpeg failure to user
        print(f"⚠ Master concat failed ({e}). Per-scene audio is still available.",
              file=sys.stderr)
        return False
    finally:
        os.unlink(concat_list)


def run_pipeline(data: dict, args: argparse.Namespace, out_path: Path) -> int:
    """Per-scene + master audio generation. Returns 0 on success."""
    audio_dir = out_path / "audio"

    combined_wavs: list[Path] = []
    for sc in data["scenes"]:
        scene_dir = audio_dir / f"scene_{sc['scene_number']:02d}"
        scene_dir.mkdir(parents=True, exist_ok=True)

        # Group this scene's dialogue lines by speaker.
        groups: dict[str, list[dict]] = {}
        for d in sc.get("dialogue", []):
            groups.setdefault(d["speaker"], []).append(d)

        scene_wavs: list[Path] = []
        for speaker, group in groups.items():
            if not group:
                continue
            info = data["cast"].get(speaker, {})
            voice = info.get("voice", "") or ""
            if not voice:
                print(f"  ⚠ No voice cast for speaker '{speaker}' in scene "
                      f"{sc['scene_number']} — skipping audio. Fix with --cast.")
                continue

            speed = sc.get("speed", DEFAULT_SPEED)
            joined = " ".join(d["line"] for d in group)
            slug = re.sub(r"[^a-z0-9]", "_", speaker.lower())

            out_file = scene_dir / f"{slug}.{args.format}"
            if tts_line(joined, voice, speed, args.format, out_file):
                scene_wavs.append(out_file)

        if not scene_wavs:
            print(f"  ⚠ Scene {sc['scene_number']}: no audio generated.")
            continue

        combined_wavs.extend(scene_wavs)

    # Master concat.
    master_out = audio_dir / f"master.{args.format}"
    if combined_wavs and concat_with_ffmpeg(combined_wavs, master_out):
        return 0

    print(f"✓ Audio dir: {audio_dir}/")
    if not combined_wavs:
        print("  ⚠ No audio generated — check that voices are cast and kokoro-tts is set up.")
    return 0


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def parse_cast(raw: str) -> dict[str, str]:
    """Parse `Char1:voice1,Char2:voice2` into a dict."""
    cast: dict[str, str] = {}
    if not raw:
        return cast
    for pair in raw.split(","):
        if ":" in pair:
            k, v = pair.strip().split(":", 1)
            cast[k.strip()] = v.strip()
    return cast


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Offline, English-only dialogue-to-audio generator for movie scripts.")
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--text", help="Direct script text (any language).")
    grp.add_argument("--file", help="Path to a .txt/.md script file.")
    grp.add_argument("--cinematographer", help="Path to a cinematographer scenes.json (one scene).")
    p.add_argument("--cast", default="", help='Comma cast map, e.g. "Dev:am_adam,Priya:af_heart".')
    p.add_argument("--style", default="cinematic", help="Visual style hint (passed to cinematographer scenes).")
    p.add_argument("--max-scenes", type=int, default=12)
    p.add_argument("--output-dir", default="prompts")
    p.add_argument("--format", choices=["wav", "mp3"], default="wav")
    p.add_argument("--force", action="store_true", help="Re-generate if output exists.")
    args = p.parse_args(argv)

    # Gather raw text / scenes.
    if args.cinematographer:
        data = {
            "title": Path(args.cinematographer).stem + "-audio",
            "generator": "script-audio-generator (offline heuristic)",
            "scenes": read_cinematographer_scenes(Path(args.cinematographer), args.max_scenes),
            "cast": {},
        }
    else:
        text = ""
        if args.text is not None:
            text = args.text.strip()
        elif args.file:
            try:
                text = Path(args.file).read_text(encoding="utf-8").strip()
            except FileNotFoundError:
                print(f"✗ File not found: {args.file}", file=sys.stderr)
                return 2

        scenes = build_scenes(text, args.max_scenes) if text.strip() else []
        data = {
            "title": Path(args.file).stem if args.file else "script-audio",
            "generator": "script-audio-generator (offline heuristic)",
            "scenes": scenes,
            "cast": {},
        }

    if not data["scenes"]:
        print("✗ No dialogue detected in input.", file=sys.stderr)
        return 2

    # Auto voice-cast: detect gender per character, assign Kokoro voices.
    overrides = parse_cast(args.cast)

    def resolve_voice(char_name: str) -> tuple[str, bool]:
        """Resolve a character's voice (cached in data['cast'])."""
        if char_name in data["cast"]:
            info = data["cast"][char_name]
            return info["voice"], info.get("from_override", False)


        # The speaker label is already the resolved gender ("male"/"female");
        # do NOT re-detect from content, which misclassifies pronouns.
        gender = char_name if char_name in ("male", "female") else ""
        detected = True if char_name in ("male", "female") else False
        voice, from_override = cast_voice(gender, overrides)

        # Unknown + no override -> leave voice blank; manifest flags it for eyeballing.
        if not detected and not from_override:
            voice = ""

        data["cast"][char_name] = {
            "voice": voice, "gender": gender,
            "detected": detected, "from_override": from_override,
        }
        return voice, from_override

    # Collect all unique speakers across scenes.
    for sc in data["scenes"]:
        for d in sc.get("dialogue", []):
            sp = d["speaker"]
            if sp and sp not in data["cast"]:
                resolve_voice(sp)

    # Slug + output dir.
    slug = re.sub(r"[^\w\s-]", "", data["title"])[:50].strip().replace(" ", "-") or "untitled-audio"
    out_path = Path(args.output_dir) / slug

    if (out_path / "manifest.md").exists() and not args.force:
        print(f"⚠ Output already exists at {out_path}. Use --force to overwrite.")
        return 0

    out_path.mkdir(parents=True, exist_ok=True)

    # Write manifest + cast.
    (out_path / "manifest.md").write_text(build_manifest(data), encoding="utf-8")

    # Per-scene audio via kokoro-tts script + ffmpeg master concat.
    rc = run_pipeline(data, args, out_path)

    # Write scenes.json (cast + dialogue for programmatic use).
    with open(out_path / "scenes.json", "w", encoding="utf-8") as j:
        json.dump(data, j, indent=2, ensure_ascii=False)

    print(f"✓ Manifest: {out_path / 'manifest.md'}")
    print(f"✓ Scenes JSON + cast: {out_path / 'scenes.json'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
