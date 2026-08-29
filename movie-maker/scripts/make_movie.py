#!/usr/bin/env python3
"""Movie Maker — orchestrates the creative pipeline into one short movie.

A deterministic *orchestrator*. The agent (you, running this skill) writes the
story; this script wires the existing skills together into an end-to-end short film:

    brief + story ──▶ characters (reuse-or-create) ──▶ cinematographer scenes
         │                                                    │
         ▼                    story.txt (prose + dialogue)     ▼
    character.json ──▶ disney-pixar-video-generation ◀── scenes.json (visuals)
         │                                                    │
         ▼                    script-audio-generator          │
    audio/scene_nn.wav ─────────▶ per-scene dialogue ◀───────┘
                                    │
                                    ▼
                         ffmpeg crossfade concat + audio sync

Run:
    python3 make_movie.py --script script.json                  # full control (recommended)
    python3 make_movie.py --topic "a brave robot finds a friend"  # quick seed script

Environment / prerequisites (checked + fail early):
    - ffmpeg on PATH.
    - Apple Silicon Mac with FastVideo at ~/.studio/FastVideo + models downloaded.
    - Sibling skills: cinematographer, script-audio-generator, disney-character-creator,
      disney-pixar-video-generation, video-generation.

Caveats (documented honestly):
    - FastMetal-QAD is text-to-video with NO image input, so cross-scene character identity
      relies on fixed seed + identical wording — not true image lock-in.
    - script-audio-generator and cinematographer use separate scene-break heuristics; counts
      may differ by ~1. The assembler trims each video to its own audio length, so minor
      mismatches are absorbed.
    - Kokoro / script-audio-generator is English-only; use kannada-tts for Kannada.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

# ─── Resolve sibling skills relative to THIS skill (symlink-safe) ─────────────
THIS_SKILL = Path(__file__).resolve().parent.parent          # .../skills/movie-maker
SKILLS_ROOT = THIS_SKILL.parent                              # real skills dir (symlink resolved)

def _skill(path: str) -> Path:
    return SKILLS_ROOT / path

CINEMATOGRAPHER_MAIN = _skill("cinematographer/main.py")
DISNEY_CHAR_SKILL = _skill("creative/disney-character-creator")
DISNEY_BUILD_PROMPT = DISNEY_CHAR_SKILL / "scripts" / "build_prompt.py"
DISNEY_CHAR_DATA = DISNEY_CHAR_SKILL / "data" / "characters"
DISney_PIXAR_VID = _skill("creative/disney-pixar-video-generation/scripts/run_pipeline.py")
VIDEO_GEN_MAIN = _skill("creative/video-generation/scripts/generate_video.py")

# Kokoro-tts skill lives as a sibling; resolve its TTS script relative to this one.
KOKORO_TTS_SCRIPT = SKILLS_ROOT / "kokoro-tts" / "scripts" / "tts.py"

XFADE_DUR = "0.5"

# ─── Progress helper — flush so long-running GPU work shows a live indicator ──
def step(n: int, total: int, title: str) -> None:
    print(f"\n\033[1;34m[{n}/{total}] {title}\033[0m", flush=True)

def info(msg: str) -> None:
    print(f"  {msg}", flush=True)

def warn(msg: str) -> None:
    print(f"  ⚠ {msg}", file=sys.stderr, flush=True)

def die(msg: str, code: int = 1) -> NoReturn:
    print(f"✗ {msg}", file=sys.stderr, flush=True)
    raise SystemExit(code)

def run(cmd: list[str], *, timeout: int = 900, label: str = "") -> subprocess.CompletedProcess | None:
    """Run a command; surface stderr on failure without dumping huge output."""
    info(f"▶ {label or ' '.join(cmd[:4])}…" if label else f"▶ {' '.join(cmd[:4])}…")
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        die(f"timed out after {timeout}s: {' '.join(cmd[:4])}")

# ─── Minimal slugify (mirrors disney-character-creator common.slugify) ─────────
def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")

# ─── 0. Brief / script loading ────────────────────────────────────────────────
def build_seed_script(topic: str) -> dict:
    """Build a minimal but valid script.json from just a topic.

    Used only for quick tests / when the agent hasn't hand-written a story. The
    creative quality is low; for real output, author script.json and pass --script.

    Keeps the seed honest to the topic: it becomes the title + first-scene
    narration, and any capitalized words in the topic become candidate character
    names. This is a quick smoke-test path only -- for real output, author your own
    script.json and pass --script.
    """
    # Pull capitalized proper-noun-ish tokens from the topic as candidate names.
    caps = []
    for tok in re.findall(r"\b([A-Z][a-zA-Z]{2,})\b", topic):
        low = tok.lower()
        if low in {"the", "a", "an", "and", "but", "was", "she", "he",
                   "they", "it", "run", "runs"}:
            continue
        if tok not in caps:
            caps.append(tok)

    characters = []
    for i, nm in enumerate(caps[:4]):
        gender = "female" if nm.lower()[-1] == "e" else ("male" if i % 2 == 0 else "female")
        characters.append({"name": nm, "gender": gender,
                            "description": f"a character named {nm}"})

    if not characters:
        # Neutral fallback pair so the pipeline still has something to render.
        characters = [{"name": "Protagonist", "gender": "male",
                        "description": "the central character of the story"}]

    # One scene per sentence in the topic (split on . ! ?), each with a blank dialogue.
    raw = topic.strip()
    parts = [s.strip() for s in re.split(r"[.!?]+", raw) if s.strip()]
    scenes = [{"narration": p + ".", "dialogue": []} for p in parts]
    if not scenes:
        scenes = [{"narration": raw + ".", "dialogue": []}]

    return {
        "title": topic.strip()[:60],
        "genre": "drama",
        "characters": characters,
        "scenes": scenes,
    }

def story_from_script(script: dict) -> str:
    """Serialize script.json into flowing prose (with dialogue) for the skills.

    Bug 1 fix: dialogue beats are emitted as on-screen dramatic sentences
    ("<Character> says, '<line>'") instead of quoted lines tagged with a speaker. Cinematographer
    reads the character as the on-screen actor, so scenes are driven by characters speaking rather
    than an external narrator describing them. Narration-only beats keep their prose so the
    cinematographer can render them as establishing shots (no voiceover is generated for audio).

    Both skills consume this; dialogue carries speaker tags so the audio skill can cast each line
    to its character's voice.
    """
    names = [c.get("name", "") for c in script.get("characters", [])]

    def resolve(speaker: str) -> str:
        """Map a script speaker to its canonical character name (for consistent subjects)."""
        if not speaker:
            return "Character"
        for c in names:
            if re.search(rf"\b{re.escape(c.lower())}\b", speaker.lower()):
                return c
        for c in names:
            for tok in re.split(r"[^a-z]+", c.lower()):
                if len(tok) >= 4 and re.search(rf"\b{re.escape(tok)}\b", speaker.lower()):
                    return c
        return speaker

    lines = []
    for sc in script.get("scenes", []):
        narr = (sc.get("narration") or "").strip()
        beats = list(sc.get("dialogue", []))
        if not narr and not beats:
            continue

        # A beat with dialogue is an on-screen line spoken by its character.
        for d in beats:
            name = resolve((d.get("speaker") or "").strip())
            line = d.get("line", "").strip().strip('"')
            lines.append(f'{name} says, "{line}"')

        # Narration-only scene: keep prose so cinematographer renders an establishing beat.
        if narr and not beats:
            lines.append(narr)

    return "\n\n".join(l for l in lines if l).strip()

# ─── 1. Characters: reuse existing or create new character.json ────────────────
def load_existing_character(slug: str) -> dict | None:
    """Return character.json if an existing saved character matches the slug."""
    path = DISNEY_CHAR_DATA / slug / "character.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            warn(f"could not read {path}: {e}")
    return None

def build_new_character(char_def: dict) -> dict:
    """Synthesize a valid Disney/Pixar character.json from the script's description.

    Fills all required fields (see disney-character-creator common.FIELDS). This is
    an automated stand-in for the interactive clarify() flow — best effort.
    """
    name = char_def.get("name", "Character")
    gender = (char_def.get("gender") or "").lower()
    desc = str(char_def.get("description", "")).strip().lower()

    # Objectified (robot/creature) -> no clothing required.
    objectified = any(k in desc for k in ("robot", "machine", "droid", "golem"))

    return {
        "name": name,
        "species": desc or f"a person ({gender})",
        "appearance_age": None,
        "gender": gender if gender in ("male", "female") else "neutral",
        "traits": ["curious", "brave", "kind"],
        "motivation": "",
        "flaw_or_arc": "",
        "body_proportions": "rounded, friendly proportions",
        "face_shape": "round",
        "eyes": {"size": "large and expressive", "color": "warm brown"},
        "hair_color_texture_style": ("short dark hair" if gender == "female" else "short brown hair"),
        "skin_tone": "warm tan",
        "relative_height": "average height",
        "clothing": (["a simple dress"] if gender == "female" else ["a shirt and pants"])
        if not objectified else [],
        "palette": ["warm amber", "soft teal"],
        "signature_accessory": "",
        "setting": "",
        "camera_direction": "slow dolly-in on the character, gentle handheld feel",
        "aspect_ratio": "16:9",
        "render_intensity": 0.5,
        "seed": random.randint(100000, 999999),
        "model": "flux2-klein-9b",
        "video_model": "Kling 3.0",
    }

def resolve_characters(script: dict) -> list[dict]:
    """For each script character, reuse existing or create new. Returns metadata.

    Each result: {name, slug, gender, video_prompt (canonical text-to-video
    description from build_prompt), char_desc (--character string for the video skill)}
    """
    results = []
    for char_def in script.get("characters", []):
        name = char_def["name"]
        slug = slugify(name)

        existing = load_existing_character(slug)
        if existing is not None:
            info(f"reuse character '{name}' (slug={slug})")
        else:
            existing = build_new_character(char_def)
            info(f"create new character '{name}' (slug={slug})")

        # Persist the new character.json so it can be reused next time.
        if load_existing_character(slug) is None:
            char_dir = DISNEY_CHAR_DATA / slug
            char_dir.mkdir(parents=True, exist_ok=True)
            (char_dir / "character.json").write_text(
                json.dumps(existing, indent=2), encoding="utf-8")

        # Canonical text-to-video description via the pure-Python build_prompt engine.
        video_prompt = ""
        char_json_path = str(DISNEY_CHAR_DATA / slug / "character.json")
        try:
            res = run(
                [sys.executable, str(DISNEY_BUILD_PROMPT), "--character", char_json_path],
                label="build character prompt", timeout=120,
            )
            if res is not None and res.returncode == 0:
                vp_path = Path(DISNEY_CHAR_DATA, slug, "video_prompt.md")
                if vp_path.exists():
                    video_prompt = vp_path.read_text(encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            warn(f"build_prompt failed for {name}: {e}")

        # The --character string for disney-pixar-video-generation: name + species.
        sp = str(existing.get("species", "")).strip()
        char_desc = f"{sp} named {name}" if sp else name

        results.append({
            "name": name,
            "slug": slug,
            "gender": (existing.get("gender") or char_def.get("gender", "")).lower(),
            "video_prompt": video_prompt,
            "char_desc": char_desc,
        })
    return results

# ─── Build a structured plan for cinematographer Mode A from script.json ──────
def build_plan_from_script(script: dict) -> dict:
    """Build {theme, characters[], beats[]} for cinematographer's --plan (Mode A).

    This is the fix for "only one character in every clip". Mode B (plain --file)
    hardcodes characters_present=[] and strips all character data, so the video step's
    fallback always renders the first character. Mode A populates characters_present,
    per-scene dialogue attribution and canonical character descriptors from this plan.

    Each script scene becomes one beat; dialogue carries {speaker, line} so the
    cinematographer can attribute on-screen lines and mark which characters are present.
    """
    theme = (script.get("title") or "").strip()

    characters: list[dict] = []
    for c in script.get("characters", []):
        name = (c.get("name") or "").strip()
        if not name:
            continue
        gender = (c.get("gender") or "").strip().lower()
        characters.append({
            "name": name,
            "gender": gender if gender in ("male", "female") else "neutral",
            "description": (c.get("description") or "").strip(),
        })

    beats: list[dict] = []
    for sc in script.get("scenes", []):
        narr = (sc.get("narration") or "").strip()
        dialogue: list[dict] = []
        for d in sc.get("dialogue", []):
            speaker = (d.get("speaker") or "").strip()
            line = (d.get("line") or "").strip().strip('"').strip("'").strip()
            if not speaker or not line:
                continue  # drop half-empty dialogue; narration-only scene still counts
            dialogue.append({"speaker": speaker, "line": line})

        if not narr and not dialogue:
            continue  # no-op scene, skip it

        beats.append({"narration": narr, "dialogue": dialogue})

    if not characters:
        raise ValueError("script has no named characters — cannot drive Mode A")
    if not beats:
        raise ValueError("script has no scenes — cannot drive Mode A")

    return {"theme": theme, "characters": characters, "beats": beats}


# ─── 2. Cinematographer — visual scene breakdown (N scenes) ──────────────────
def run_cinematographer(script: dict, out_dir: Path) -> list[dict]:
    """Run cinematographer (Mode A plan path) and return the parsed scenes.

    We build a structured plan from script.json (characters + beats with dialogue) and
    pass it via --plan so Mode A populates characters_present, per-scene dialogue
    attribution and canonical character descriptors. This is the fix for "only one
    character in every clip": Mode B (plain --file) hardcodes characters_present=[].

    Cinematographer computes its own slug from the plan theme, so we point --output at
    out_dir and then locate whatever <out_dir>/<slug>/scenes.json it produced rather than
    assuming a fixed slug.
    """
    scenes_json = _find_cinematographer_output(out_dir)
    if scenes_json is not None:
        info(f"reusing existing {scenes_json}")
        return json.loads(scenes_json.read_text(encoding="utf-8"))["scenes"]

    plan = build_plan_from_script(script)
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")

    run(
        [sys.executable, str(CINEMATOGRAPHER_MAIN), "--plan", str(out_dir / "plan.json"),
         "--max-scenes", "12",
         "--output", str(out_dir)],
        label="cinematographer scene breakdown", timeout=180,
    )

    scenes_json = _find_cinematographer_output(out_dir)
    if scenes_json is None:
        die("cinematographer produced no output — check the story text and try again.")

    data = json.loads(scenes_json.read_text(encoding="utf-8"))
    return data.get("scenes", [])


def _find_cinematographer_output(out_dir: Path) -> Path | None:
    """Find the <out_dir>/<slug>/scenes.json cinematographer wrote.

    Returns None if none exists yet (so the caller can run it).
    """
    for scenes_json in out_dir.rglob("scenes.json"):
        if scenes_json.is_file():
            return scenes_json
    return None

# ─── 3. Audio — per-scene dialogue + narration via tts.py (Kokoro) ───────────
def _voice_for_gender(gender: str) -> tuple[str, float]:
    """Return (kokoro_voice, speed) for a character's gender.

    Kokoro voices are English-only; the Indian-accented models sound most
    natural for an Indian-English story. Speed is tuned for unhurried narration.
    """
    if gender == "female":
        return ("if_sara", 0.9)     # female Indian voice, natural pace
    if gender == "male":
        return ("im_nicola", 0.95)  # male Indian voice, natural pace
    return ("im_nicola", 0.9)      # default narrator voice


def _tts_line(text: str, voice: str, speed: float, out_path: Path) -> bool:
    """Run tts.py for one line; return True if the wav was produced."""
    cmd = [sys.executable, str(KOKORO_TTS_SCRIPT), text, "-v", voice,
           "-s", f"{speed:.2f}", "--max-segment", "380"]
    if out_path.suffix == ".mp3":
        cmd += ["-f", "mp3"]
    cmd += ["-o", str(out_path)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        warn(f"tts timed out for '{text[:40]}…'")
        return False
    if proc.returncode != 0:
        last = (proc.stderr or "").strip().splitlines()[-1] if proc.stderr else ""
        warn(f"tts failed for '{text[:40]}…': {last}")
        return False
    if not out_path.exists():
        warn(f"expected {out_path} was not created")
        return False
    return True


def _concat_wavs(wavs: list[Path], out_path: Path) -> bool:
    """Concatenate per-scene wavs into one file via ffmpeg concat."""
    if len(wavs) == 1:
        shutil.copyfile(wavs[0], out_path)
        return True

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for fp in wavs:
            f.write(f"file '{fp}'\n")
        concat_list = f.name
    try:
        proc = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", concat_list, "-c", "copy", str(out_path)],
            capture_output=True, text=True)
        if proc.returncode != 0 or not out_path.exists():
            last = (proc.stderr or "").strip().splitlines()[-1] if proc.stderr else ""
            warn(f"audio concat failed: {last}")
            return False
        return True
    finally:
        os.unlink(concat_list)


def run_audio(script: dict, out_dir: Path, force: bool) -> dict[int, list[Path]]:
    """Generate per-scene dialogue audio directly via tts.py.

    Bug 1 fix: we no longer generate a narrated voiceover (the previous behaviour played an
    external 3rd-person narrator describing the action, which is exactly what was wanted to be
    removed). Now ONLY characters speak on-screen: each dialogue line is cast to its character's
    gendered Kokoro voice and concatenated per scene. A scene with no dialogue is skipped for
    audio here (a music/ambience bed, if any, would be added separately). Returns
    {scene_number: [wav paths]}.

    Root-cause fix for the earlier "no audio" bug (also fixed here): the previous run_audio()
    never passed --output-dir to script-audio-generator, so it wrote relative-to-CWD into a
    stray prompts/ dir that was never found (glob pattern also wrong). On top of that,
    script-audio-generator returned empty speakers for proper-noun dialogue ("— Brahmin"),
    producing zero audio. This version drives tts.py directly and casts each dialogue line to
    the character's gendered voice.
    """
    audio_dir = Path(out_dir) / "audio"
    if force and audio_dir.exists():
        shutil.rmtree(audio_dir, ignore_errors=True)

    char_gender = {c["name"]: c.get("gender", "") for c in script.get("characters", [])}
    per_scene: dict[int, list[Path]] = {}

    for idx, sc in enumerate(script.get("scenes", []), start=1):
        info(f"scene {idx}: generating audio")

        scene_dir = audio_dir / f"scene_{idx:02d}"
        scene_dir.mkdir(parents=True, exist_ok=True)

        wavs: list[Path] = []

        # Bug 1 fix: NO narration voiceover. Only characters speak on-screen.
        for d in sc.get("dialogue", []):
            speaker = (d.get("speaker") or "").strip()
            line = d.get("line", "").strip().strip('"')
            if not line:
                continue
            gender = char_gender.get(speaker, "") or (d.get("gender") or "")
            voice, speed = _voice_for_gender(gender)
            d_wav = scene_dir / f"{slugify(speaker or 'voice')}.wav"
            if _tts_line(line, voice, speed, d_wav):
                wavs.append(d_wav)

        if not wavs:
            warn(f"scene {idx}: no dialogue audio (characters stay silent this beat)")
            continue

        combined = scene_dir / "scene.wav"
        if _concat_wavs(wavs, combined):
            per_scene[idx] = [combined]

    return per_scene

# ─── 4. Video — disney-pixar-video-generation (per scene, x N) ───────────────
def run_video(scenes: list[dict], characters: list[dict], model: str, seed: int,
              out_dir: Path) -> dict[int, Path]:
    """Generate one ~5s Pixar clip per cinematographer scene. Returns {scene: mp4}.

    Reuses existing clips on disk if a full set is already present (regeneration
    after an audio/assembly fix) so we don't pay the ~10s-per-clip GPU cost twice.
    """
    video_dir = Path(out_dir) / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)

    # Reuse existing clips if a full set is already present (regeneration).
    existing = sorted(video_dir.glob("*.mp4"))
    if len(existing) >= len(scenes):
        info(f"reusing {len(existing)} existing clips (skipping GPU generation)")
        produced = {}
        for i, scene in enumerate(scenes, start=1):
            if i - 1 < len(existing):
                produced[i] = existing[i - 1]
        return produced

    # Map scene subject -> closest character by name overlap.
    char_by_name = {c["name"].lower(): c for c in characters}

    produced: dict[int, Path] = {}
    total = len(scenes)
    for i, scene in enumerate(scenes, start=1):
        step(i, total, f"generate video scene {i}")

        # Which characters are actually on screen this beat? Mode A (cinematographer plan
        # path) fills characters_present with the canonical identities for this scene. We pass
        # ALL of them so multi-character scenes render every character that is present — this
        # is the fix for "only one character in every clip": the old code read only
        # characters_present[0] and, when that was empty (Mode B), fell back to characters[0],
        # so the first character was rendered in every single scene.
        on_screen = [s for s in (scene.get("characters_present") or []) if s]
        if not on_screen:  # narration-only scene — no dialogue attribution yet
            subject = (scene.get("subject") or "").strip()
            on_screen = [subject] if subject else []

        descs: list[str] = []
        for name in on_screen:
            match = None
            for cname in char_by_name:
                if re.search(rf"\b{re.escape(cname)}\b", name.lower()):
                    match = char_by_name[cname]
                    break
            if match is None and characters:  # unknown subject — keep the first as last resort
                match = characters[0]
            if match and (match["char_desc"] not in descs):
                descs.append(match["char_desc"])

        scene_setting = f"{scene.get('visual_description', '')} {scene.get('setting', '')}".strip()

        # Snapshot existing clips so we can detect the one just produced
        # (the video skill names outputs like video_<ts>.mp4, not clip_01.mp4).
        before = {p.name for p in video_dir.glob("*.mp4")}

        # Pass EACH on-screen character as its own --character flag so enrich_prompt's CLI
        # sees multiple and routes through build_prompt_multi (every identity rendered). With a
        # single character it still works; with zero we fall back to the neutral subject. This is
        # what fixes "only one character in every clip".
        char_flags = []
        for d in descs:
            char_flags += ["--character", d]

        run(
            [sys.executable, str(DISney_PIXAR_VID), "--model", model,
             "--seed", str(seed if seed >= 0 else -1),
             "--output-dir", str(video_dir)] + char_flags + [
             "--scene", scene_setting.strip()[:200] or "a softly lit room"],
            label=f"video scene {i}", timeout=600,
        )

        # Find the new clip that appeared after generation.
        new_clip = _newest_new_video(video_dir, before)
        if new_clip is None:
            warn(f"scene {i}: no video clip produced; skipping it")
        else:
            produced[i] = new_clip

    return produced


def _newest_new_video(video_dir: Path, seen_names: set[str]) -> Path | None:
    """Return the newest .mp4 in video_dir not already in seen_names."""
    candidates = [p for p in video_dir.glob("*.mp4") if p.name not in seen_names]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

# ─── 5. Assemble — attach per-scene audio, then crossfade concat ──────────────

def _video_duration(video: Path) -> float:
    """Return a clip's raw generated duration. All clips from FastMetal-QAD are uniform."""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            capture_output=True, text=True)
        return float(proc.stdout.strip()) if proc.returncode == 0 else 5.0625
    except Exception:
        return 5.0625


def _mux_audio_onto_clip(video: Path, audio_wav: Path | None, out: Path) -> None:
    """Attach per-scene audio to a scene clip.

    The text-to-video clips produced by disney-pixar-video-generation are SILENT —
    dialogue audio comes separately (script-audio-generator / Kokoro). We mux the per-scene
    wav onto each clip so EVERY scene video (including the LAST one) carries a real audio
    track.

    Bug 2 fix: we NEVER use `-shortest` here (it trimmed clips to min(video,audio), cutting
    lip-sync short and letting video+audio drift apart in the concat). Instead we pad audio
    with `apad` to exactly match the clip's raw generated duration, so video and audio stay
    perfectly aligned for every scene. If a scene has no audio file, we pad it with silence
    so crossfades still overlap cleanly (avoids a hard-cut click).
    """
    if audio_wav is not None and Path(audio_wav).exists():
        # Bug 2 fix: pad dialogue to the clip's raw duration and cap output at T. We do NOT use
        # `-shortest` (it trimmed clips to min(video,audio), cutting lip-sync short and letting
        # video + audio drift apart per scene). Verified idiom: `apad=pad_dur=T[a]` pads the audio
        # so it reaches T, then `-t T` caps BOTH streams to exactly the video's raw generated
        # duration. Video is copied as-is (no re-encode) so it stays exactly T; audio is padded and
        # capped to the same length, giving a perfect match every scene. This replaces an earlier
        # `apad=pad_dur=T,asetpts=N/SR/TB` form which padded *by* T (doubling long audio) and let
        # `-t` fail to cap the copied video, leaving clips at varied durations with drifted audio.
        video_dur = _video_duration(video) or 5.0625
        cmd = ["ffmpeg", "-y", "-i", str(video), "-i", str(audio_wav),
               "-filter_complex", "[1:a]apad=pad_dur=%.3f[a]" % video_dur,
               "-map", "0:v:0", "-map", "[a]",
               "-c:v", "copy", "-c:a", "aac", "-ar", "48000",
               "-t", "%.3f" % video_dur, str(out)]
    else:
        # No dialogue in this scene: pad silence to exactly T so the clip is never left video-only
        # and crossfades still overlap cleanly. anullsrc + apad then -t T yields exactly T silence.
        video_dur = _video_duration(video) or 5.0625
        cmd = ["ffmpeg", "-y", "-i", str(video),
               "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
               "-filter_complex", "[1:a]apad=pad_dur=%.3f[a]" % video_dur,
               "-map", "0:v:0", "-map", "[a]",
               "-c:v", "copy", "-c:a", "aac", "-ar", "48000",
               "-t", "%.3f" % video_dur, str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        die(f"failed to mux audio onto {video.name}:\n{proc.stderr[-500:]}")


def _clip_duration(clip: Path) -> float:
    """Return a clip's duration in seconds (5.0 fallback if ffprobe fails)."""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(clip)],
            capture_output=True, text=True)
        return float(proc.stdout.strip()) if proc.returncode == 0 else 5.0
    except Exception:
        return 5.0


def assemble(videos: dict[int, Path], audio_per_scene: dict[int, list[Path]],
             aspect: str, out_final: Path) -> None:
    """Concatenate per-scene clips into one movie WITH audio (Bug 2 fix).

    Root-cause fix for the "~5s freeze": the previous code used `xfade` +
    `acrossfade`. In this ffmpeg build (8.1.1) the xfade filter collapses every
    chained transition to a single clip's duration (~5s), so the finished movie
    froze at ~5 seconds while audio kept playing. The robust fix is to `concat`
    all clips (durations sum correctly) with per-clip fade in/out filters for a
    smooth transition. Audio is concatenated the same way, so video and audio stay
    in sync across ALL N scenes — including the last one (which xfade dropped).

    Steps:
      1. Mux each scene's audio onto its clip (incl. the last), normalized to
         48 kHz / stereo so every concat input matches format and no click pops.
      2. Apply fade in/out to each fixed clip so adjacent clips blend smoothly.
      3. Concatenate all video streams, and separately all audio streams.
      4. Mux -> out_final with libx264/aac/yuv420p (audio at 48 kHz).
      5. Fall back to a plain audio-inclusive concat if the crossfade mux fails.
    """
    out_final.parent.mkdir(parents=True, exist_ok=True)

    ordered = sorted(videos)
    if not ordered:
        die("no video clips were produced — nothing to assemble.")

    n = len(ordered)
    if n == 1:
        # Single scene: still attach audio so the clip is not silent.
        wavs = audio_per_scene.get(ordered[0], [])
        wav = Path(wavs[0]) if wavs else None
        _mux_audio_onto_clip(videos[ordered[0]], wav, out_final)
        return

    # 1. Attach per-scene audio to every clip (incl. the last), normalized format.
    fixed: list[Path] = []
    for n_key in ordered:
        wavs = audio_per_scene.get(n_key, [])
        wav = Path(wavs[0]) if wavs else None
        fixed.append(out_final.parent / f"scene_{n_key:02d}_fixed.mp4")
        _mux_audio_onto_clip(videos[n_key], wav, fixed[-1])

    # 2. Fade-filter each clip's video (smooth transition), then concat all.
    # Audio is concatenated plain (no per-clip asetpts/fade): on this ffmpeg build
    # the audio filter-graph linking fails when individual clips are pre-processed.
    vf = ""
    for i in range(n):
        dur = _clip_duration(fixed[i]) or 5.0
        fade_in_dur = XFADE_DUR
        # Fade-out starts near the end of each clip so it blends into the next.
        fade_out_start = max(0.0, dur - float(fade_in_dur))
        vf += (f"[{i}:v]setpts=PTS-STARTPTS,fade=t=in:t=0:d={fade_in_dur},"
               f"fade=t=out:st={fade_out_start:.2f}:d={fade_in_dur}[v{i}];")

    vf += f"{''.join(f'[v{k}]' for k in range(n))}concat=n={n}:v=1:a=0[mf]"
    af = f"{''.join(f'[{k}:a]' for k in range(n))}concat=n={n}:v=0:a=1[mfa]"

    cmd = ["ffmpeg", "-y"]
    for fx in fixed:
        cmd += ["-i", str(fx)]
    cmd += [
        "-filter_complex", f"{vf};{af}",
        "-map", "[mf]", "-map", "[mfa]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", str(out_final),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out_final.exists():
        # Fallback: plain concat that still keeps audio (no more silent output).
        warn("crossfade mux failed; falling back to plain concat")
        vf2 = f"{''.join(f'[{k}]' for k in range(n))}concat=n={n}:v=1:a=1[fv]"
        proc = subprocess.run(
            ["ffmpeg", "-y"] + [x for fx in fixed for x in ("-i", str(fx))] +
            ["-filter_complex", vf2, "-map", "[fv]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_final)],
            capture_output=True, text=True)
        if proc.returncode != 0 or not out_final.exists():
            die(f"final assembly failed:\n{proc.stderr[-800:]}")

# ─── Prerequisite checks ──────────────────────────────────────────────────────
def check_prereqs() -> None:
    if not shutil.which("ffmpeg"):
        die("ffmpeg is not on PATH. Install with: brew install ffmpeg")
    if not VIDEO_GEN_MAIN.exists():
        die(f"video-generation script missing: {VIDEO_GEN_MAIN}\n"
            f"Run its setup (FastVideo + FastMetal-QAD models) first.")
    if not Path(CINEMATOGRAPHER_MAIN).exists():
        die(f"required skill missing: cinematographer ({CINEMATOGRAPHER_MAIN})")

# ─── Main ─────────────────────────────────────────────────────────────────────
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Movie Maker orchestrator.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--script", help="Path to script.json (author the story here).")
    g.add_argument("--topic", help="Quick seed: build a minimal script.json from a topic.")
    p.add_argument("--genre", default="drama")
    p.add_argument("--aspect", default="16:9", choices=["16:9", "9:16", "4:5"])
    p.add_argument("--model", default="5b", choices=["1.3b", "5b"],
                   help="FastMetal-QAD model (default 5b = 720p).")
    p.add_argument("--seed", type=int, default=-1)
    p.add_argument("--output-dir", default=None, help="Default: ./movie_output/<slug>")
    p.add_argument("--force", action="store_true")
    return p.parse_args(argv)

def main() -> int:
    args = parse_args()
    check_prereqs()

    # 0. Script (author-provided or seeded).
    if args.script:
        script = json.loads(Path(args.script).read_text(encoding="utf-8"))
    elif args.topic:
        script = build_seed_script(args.topic)
    else:
        die("provide --script <path> or --topic \"...\"")

    slug = slugify(script.get("title", "untitled"))
    out_dir = Path(args.output_dir) if args.output_dir else Path(f"movie_output/{slug}")
    out_dir.mkdir(parents=True, exist_ok=True)

    total_steps = 5
    n = 0

    # Story prose (narration + dialogue) — single source for cinematographer + audio.
    story_txt = story_from_script(script)
    (out_dir / "story.txt").write_text(story_txt, encoding="utf-8")

    # 1. Characters (reuse or create).
    n += 1; step(n, total_steps, "resolve characters")
    characters = resolve_characters(script)

    # 2. Cinematographer scenes (visuals). Mode A plan path populates characters_present,
    # per-scene dialogue attribution and canonical character descriptors from the script.
    n += 1; step(n, total_steps, "cinematographer scene breakdown")
    scenes = run_cinematographer(script, out_dir)
    if not scenes:
        die("no scenes produced by cinematographer — check the story text.")

    # 3. Audio (per-scene dialogue + narration).
    n += 1; step(n, total_steps, "generate scene audio")
    audio_per_scene = run_audio(script, out_dir, args.force)

    # 4. Video (one Pixar clip per scene).
    n += 1; step(n, total_steps, "generate video clips")
    videos = run_video(scenes, characters, args.model, args.seed, out_dir)

    # 5. Assemble + crossfade.
    n += 1; step(n, total_steps, "assemble final movie")
    out_final = Path(args.output_dir) / f"{slug}.mp4" if args.output_dir \
        else Path(f"movie_output/{slug}/{slug}.mp4")
    assemble(videos, audio_per_scene, args.aspect, out_final)

    print(f"\n\033[1;32m✓ Movie ready: {out_final}\033[0m", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
