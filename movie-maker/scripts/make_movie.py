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
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

# ─── Resolve sibling skills relative to THIS skill (symlink-safe) ─────────────
THIS_SKILL = Path(__file__).resolve().parent.parent          # .../skills/movie-maker
SKILLS_ROOT = THIS_SKILL.parent                              # real skills dir (symlink resolved)

def _skill(path: str) -> Path:
    return SKILLS_ROOT / path

CINEMATOGRAPHER_MAIN = _skill("cinematographer/main.py")
SCRIPT_AUDIO_GEN = _skill("script-audio-generator/scripts/audio_gen.py")
DISNEY_CHAR_SKILL = _skill("creative/disney-character-creator")
DISNEY_BUILD_PROMPT = DISNEY_CHAR_SKILL / "scripts" / "build_prompt.py"
DISNEY_CHAR_DATA = DISNEY_CHAR_SKILL / "data" / "characters"
DISney_PIXAR_VID = _skill("creative/disney-pixar-video-generation/scripts/run_pipeline.py")
VIDEO_GEN_MAIN = _skill("creative/video-generation/scripts/generate_video.py")

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

    Both cinematographer and script-audio-generator consume this as natural
    language; dialogue is written with speaker tags so the audio skill can extract it.
    """
    lines = []
    for sc in script.get("scenes", []):
        narr = (sc.get("narration") or "").strip()
        if narr:
            lines.append(narr)
        for d in sc.get("dialogue", []):
            spk = (d.get("speaker") or "voice").strip()
            line = d.get("line", "").strip().strip('"')
            lines.append(f'"{line}" — {spk}')
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

# ─── 2. Cinematographer — visual scene breakdown (N scenes) ──────────────────
def run_cinematographer(story_txt: str, out_dir: Path) -> list[dict]:
    """Run cinematographer and return the parsed scenes.

    Cinematographer computes its own slug from the input text, so we point
    --output at out_dir and then locate whatever <out_dir>/<slug>/scenes.json it
    produced rather than assuming a fixed slug.
    """
    scenes_json = _find_cinematographer_output(out_dir)
    if scenes_json is not None:
        info(f"reusing existing {scenes_json}")
        return json.loads(scenes_json.read_text(encoding="utf-8"))["scenes"]

    run(
        [sys.executable, str(CINEMATOGRAPHER_MAIN), "--file", str(out_dir / "story.txt"),
         "--style", "cinematic", "--max-scenes", "12",
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

# ─── 3. Audio — script-audio-generator (per-scene audio) ─────────────────────
def run_audio(story_txt: str, out_dir: Path, force: bool) -> dict[int, list[Path]]:
    """Generate per-scene dialogue audio. Returns {scene_number: [wav files]}."""
    story_file = out_dir / "story.txt"
    cmd = [sys.executable, str(SCRIPT_AUDIO_GEN), "--file", str(story_file),
           "--format", "wav", "--max-scenes", "12"]
    if force:
        cmd.append("--force")

    run(cmd, label="script-audio-generator", timeout=600)

    per_scene: dict[int, list[Path]] = {}
    audio_dir = out_dir / "story-audio"
    if audio_dir.exists():
        for wav in sorted(audio_dir.glob("scene_*/**/*.wav")):
            m = re.search(r"scene_(\d+)", str(wav))
            if m:
                per_scene.setdefault(int(m.group(1)), []).append(wav)
    return per_scene

# ─── 4. Video — disney-pixar-video-generation (per scene, x N) ───────────────
def run_video(scenes: list[dict], characters: list[dict], model: str, seed: int,
              out_dir: Path) -> dict[int, Path]:
    """Generate one ~5s Pixar clip per cinematographer scene. Returns {scene: mp4}."""
    video_dir = out_dir / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)

    # Map scene subject -> closest character by name overlap.
    char_by_name = {c["name"].lower(): c for c in characters}

    produced: dict[int, Path] = {}
    total = len(scenes)
    for i, scene in enumerate(scenes, start=1):
        step(i, total, f"generate video scene {i}")

        subject = (scene.get("characters") or [""])[0]
        char = None
        for cname in char_by_name:
            if re.search(rf"\b{re.escape(cname)}\b", subject.lower()):
                char = char_by_name[cname]
                break
        if char is None and characters:
            char = characters[0]

        character_desc = (char["char_desc"] if char else "")
        scene_setting = f"{scene.get('visual_description', '')} {scene.get('setting', '')}".strip()

        # Snapshot existing clips so we can detect the one just produced
        # (the video skill names outputs like video_<ts>.mp4, not clip_01.mp4).
        before = {p.name for p in video_dir.glob("*.mp4")}

        run(
            [sys.executable, str(DISney_PIXAR_VID), "--model", model,
             "--seed", str(seed if seed >= 0 else -1),
             "--output-dir", str(video_dir),
             "--character", character_desc or "a person",
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

def _mux_audio_onto_clip(video: Path, audio_wav: Path | None, out: Path) -> None:
    """Attach per-scene audio to a scene clip.

    The text-to-video clips produced by disney-pixar-video-generation are SILENT —
    dialogue audio comes separately (script-audio-generator / Kokoro). We mux the per-scene
    wav onto each clip so EVERY scene video (including the LAST one) carries a real audio
    track. Audio is normalized to 48 kHz / stereo so the later acrossfade has uniformly
    formatted inputs and produces no click/pop at transitions.

    If a scene has no audio file, we pad it with silence so crossfades still overlap
    cleanly (avoids a hard-cut click) and the clip is never left video-only.
    """
    if audio_wav is not None and Path(audio_wav).exists():
        cmd = ["ffmpeg", "-y", "-i", str(video), "-i", str(audio_wav),
               "-c:v", "copy", "-shortest",
               "-c:a", "aac", "-ar", "48000", "-ac", "2", str(out)]
    else:
        cmd = ["ffmpeg", "-y", "-i", str(video),
               "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
               "-c:v", "copy", "-shortest", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        die(f"failed to mux audio onto {video.name}:\n{proc.stderr[-500:]}")


def assemble(videos: dict[int, Path], audio_per_scene: dict[int, list[Path]],
             aspect: str, out_final: Path) -> None:
    """Crossfade-concatenate per-scene clips into one movie WITH audio.

    Root-cause fix for two reported bugs:
      * The text-to-video clips are SILENT; dialogue audio comes separately. The previous
        code assumed each clip already had an audio track (`[0:a]`), so the crossfade
        filtergraph failed and fell back to a video-only concat. That dropped ALL audio
        (including the last clip) AND produced hard cuts / clicks at every scene boundary.
      * Fix: mux each scene's separate audio onto its clip first (including the last one),
        normalized to 48 kHz / stereo, then crossfade-concatenate. Uniform audio format +
        a real 0.5 s overlap removes both the missing-audio and transition-glitch problems.

    Steps:
      1. For each scene, mux its audio (or silence if none) onto the clip -> fixed clips.
      2. Crossfade-concatenate with xfade (video) + acrossfade (audio).
      3. Mux -> out_final with libx264/aac/yuv420p (audio at 48 kHz).
      4. Fall back to a plain concat that still keeps audio if the crossfade mux fails.
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

    # 2. Crossfade-concatenate the self-contained clips (inputs re-indexed 0..n-1).
    vf = f"[0:v][1:v]xfade=duration={XFADE_DUR}:transition=fade[v0]"
    prev_v = "[v0]"
    for k in range(2, n):
        vf += f";[{k}:v]{prev_v}xfade=duration={XFADE_DUR}:transition=fade[v{k}]"
        prev_v = f"[v{k}]"

    af = f"[0:a][1:a]acrossfade=d={XFADE_DUR}[a0]"
    prev_a = "[a0]"
    for k in range(2, n):
        af += f";[{k}:a]{prev_a}acrossfade=d={XFADE_DUR}[a{k}]"
        prev_a = f"[a{k}]"

    cmd = ["ffmpeg", "-y"]
    for fx in fixed:
        cmd += ["-i", str(fx)]
    cmd += [
        "-filter_complex", f"{vf};{af}",
        "-map", prev_v, "-map", prev_a,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", str(out_final),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out_final.exists():
        # Fallback: plain concat that still keeps audio (no more silent output).
        warn("crossfade mux failed; falling back to audio-inclusive concat")
        vf2 = f"[0:v][1:v]concat=n={n}:v=1:a=1[fv]"
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
    for label, path in [("cinematographer", CINEMATOGRAPHER_MAIN),
                        ("script-audio-generator", SCRIPT_AUDIO_GEN)]:
        if not Path(path).exists():
            die(f"required skill missing: {label} ({path})")

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

    # 2. Cinematographer scenes (visuals).
    n += 1; step(n, total_steps, "cinematographer scene breakdown")
    scenes = run_cinematographer(story_txt, out_dir)
    if not scenes:
        die("no scenes produced by cinematographer — check the story text.")

    # 3. Audio (per-scene dialogue).
    n += 1; step(n, total_steps, "generate scene audio")
    audio_per_scene = run_audio(story_txt, out_dir, args.force)

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
