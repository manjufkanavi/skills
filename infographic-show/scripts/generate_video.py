#!/usr/bin/env python3
"""
infographic-show — generate a narrated MP4 from SVG scene cards (theloop-based pipeline).

Each input scene has type "svg" (a self-contained <svg> at 1920x1080) plus optional
narration. The skill drives the in-model closed loop (theloop) to *generate and refine*
those SVGs; this script only rasterizes + narrates + stitches them into a video.

Input scene JSON (stdin or --scenes file):
{
  "title": "...",
  "theme": "purple",
  "duration_per_scene": 4.0,
  "transition_duration": 0.8,
  "narration_voice": "af_bella",
  "narration_speed": 1.0,
  "scenes": [
    {"type":"svg","svg":"<full <svg>...</svg> at 1920x1080",
     "narration":"spoken text", "duration":4.0}
  ]
}

Pipeline: SVG scenes -> cairosvg PNG (1920x1080) -> Kokoro TTS (optional) ->
ffmpeg xfade transitions + audio -> MP4.

If Kokoro is unavailable, narration is skipped and each scene simply holds for its
duration (silent video). Run with the skill's venv so Kokoro is importable:

  ~/.venvs/infographic-show/bin/python scripts/generate_video.py --scenes scenes.json --output show.mp4

Dependencies: cairosvg, ffmpeg, python3; optionally kokoro_onnx + soundfile (from the venv).
"""
import json, os, sys, subprocess, tempfile, shutil, argparse
from pathlib import Path

W, H = 1920, 1080
SAMPLE_RATE = 24000  # Kokoro native sample rate

# macOS: cairosvg (cairocffi) cannot locate the Homebrew libcairo unless it is on
# DYLD_LIBRARY_PATH. Ensure it is set before any cairosvg invocation.
_CAIRO_LIB_DIR = "/opt/homebrew/lib"
if os.path.isdir(_CAIRO_LIB_DIR) and "DYLD_LIBRARY_PATH" not in os.environ:
    os.environ["DYLD_LIBRARY_PATH"] = _CAIRO_LIB_DIR

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Kokoro TTS (optional — skipped gracefully if the package is missing)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_kokoro = None


def _kokoro_model_paths():
    return (
        os.path.expanduser('~/.hermes/skills/voice-bridge/assets/kokoro/model.onnx'),
        os.path.expanduser('~/.hermes/skills/voice-bridge/assets/voices-v1.0.bin'),
    )


def init_kokoro():
    """Lazy-init the Kokoro model. Returns the model, or False if unavailable."""
    global _kokoro
    if _kokoro is None:
        try:
            from kokoro_onnx import Kokoro  # type: ignore
            mp, vp = _kokoro_model_paths()
            _kokoro = Kokoro(mp, vp)
            print(f"  Kokoro TTS loaded ({len(_kokoro.voices)} voices)")
        except Exception as e:  # noqa: BLE001 - report and continue silently
            _kokoro = False
            print(f"  Kokoro unavailable ({e}); narration skipped.")
    return _kokoro


def generate_speech(text, voice="af_bella", speed=1.0):
    """Return (float32 audio array, duration_seconds). Returns empty if Kokoro is down."""
    import numpy as np

    k = init_kokoro()
    if not k or k is False:
        return np.array([], dtype=np.float32), 0.0
    if not text or not text.strip():
        return np.array([], dtype=np.float32), 0.0

    phonemes_str = k.tokenizer.phonemize(text.strip(), "en-us")

    # Split long phoneme strings into batches (max 510 phonemes each).
    MAX_PHONEME_LENGTH = 510
    import re
    words = re.split(r"([.,!?;])", phonemes_str)
    batches, current = [], ""
    for part in words:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) + 1 >= MAX_PHONEME_LENGTH:
            batches.append(current.strip())
            current = part
        else:
            if part in ".,!?;":
                current += part
            else:
                current = (current + " " + part) if current else part
    if current:
        batches.append(current.strip())

    voice_emb = k.voices.get(voice)
    if voice_emb is None:
        voice_emb = k.voices.get("af_bella")
    audio_parts = []
    for batch in batches:
        tokens = np.array(k.tokenizer.tokenize(batch), dtype=np.int64)
        style = voice_emb[len(tokens), 0, :].reshape(1, -1).astype(np.float32)
        padded = np.array([[0, *tokens.tolist(), 0]], dtype=np.int64)
        inputs = {
            "input_ids": padded,
            "style": style,
            "speed": np.array([speed], dtype=np.float32),
        }
        audio = k.sess.run(None, inputs)[0].flatten().astype(np.float32)
        audio_parts.append(audio)

    result = np.concatenate(audio_parts) if audio_parts else np.array([], dtype=np.float32)
    return result, len(result) / SAMPLE_RATE


def save_audio(audio, path):
    import soundfile as sf
    sf.write(path, audio, SAMPLE_RATE)


def silence_clip(duration, audio_dir):
    import numpy as np, soundfile as sf
    p = audio_dir / f"silence_{id(audio_dir)}_{len(list(audio_dir.iterdir()))}.wav"
    sf.write(p, np.zeros(int(duration * SAMPLE_RATE), dtype=np.float32), SAMPLE_RATE)
    return p


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SVG scene -> PNG frame
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_scene_to_png(svg_markup, png_path):
    """Write the raw SVG to disk and rasterize it to a 1920x1080 PNG via cairosvg."""
    svg_path = png_path.with_suffix(".svg")
    markup = (svg_markup or "").strip()
    if not markup.lower().lstrip().startswith("<svg"):
        markup = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n{markup}\n</svg>'
    svg_path.write_text(markup, encoding="utf-8")
    try:
        subprocess.run(
            ["cairosvg", str(svg_path), "-o", str(png_path), "-W", str(W), "-H", str(H)],
            check=True, capture_output=True, timeout=120,
        )
    except subprocess.CalledProcessError:
        subprocess.run(["cairosvg", str(svg_path), "-o", str(png_path)], capture_output=True)
    return png_path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Audio assembly
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _time_stretch(audio, rate, sr=SAMPLE_RATE):
    """Stretch audio by rate factor (rate>1 = slower/longer) using rubberband.
    Pitch-preserving time-stretch via pyrubberband."""
    import pyrubberband as prb
    import numpy as np
    if len(audio) == 0 or abs(rate - 1.0) < 0.01:
        return audio
    rate = float(rate)
    # pyrubberband uses playback rate (higher=faster=shorter), so invert
    return prb.time_stretch(audio, sr, 1.0 / rate).astype(np.float32)


def generate_narration_scenes(scenes, voice, speed, min_dur, trans):
    """Return (scene_durations, audio_paths, audio_dir).
    Scene visual hold time = narration audio duration, so screen stays
    until narration is fully spoken. No speed calibration — Kokoro speed=1.0
    is the correct default."""
    import numpy as np, soundfile as sf
    audio_dir = Path(tempfile.mkdtemp(prefix="infog_audio_"))
    scene_durations, audio_paths = [], []
    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "").strip()
        if narration:
            audio, dur = generate_speech(narration, voice, speed)
            wav = audio_dir / f"n_{i:03d}.wav"
            save_audio(audio, wav)
            # Scene visual hold = audio duration + transition overlap + buffer
            # This ensures the screen stays until narration is complete
            scene_durations.append(dur + trans + 0.3)
            audio_paths.append(wav)
        else:
            dur = scene.get("duration", min_dur)
            scene_durations.append(dur)
            audio_paths.append(silence_clip(dur, audio_dir))
    return scene_durations, audio_paths, audio_dir


def build_combined_audio(audio_paths, scene_durations, output_path):
    """Concatenate per-scene clips padded to their scene durations into one WAV."""
    import numpy as np, soundfile as sf
    clips, total = [], 0.0
    for apath, sdur in zip(audio_paths, scene_durations):
        data, sr = sf.read(apath)
        tgt = int(sdur * sr)
        if len(data) < tgt:
            data = np.concatenate([data.astype(np.float32), np.zeros(tgt - len(data), np.float32)])
        else:
            data = data[:tgt].astype(np.float32)
        clips.append(data)
        total += tgt / sr
    combined = np.concatenate(clips) if clips else np.array([], dtype=np.float32)
    sf.write(output_path, combined, SAMPLE_RATE)
    return output_path, total


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Video pipeline (ffmpeg xfade)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_video(data, output_path, work_dir=None):
    title = data.get("title", "Infographic")
    scenes = data.get("scenes", [])
    trans = data.get("transition_duration", 0.8)
    min_dur = data.get("duration_per_scene", 4.0)
    voice = data.get("narration_voice", "af_bella")
    speed = data.get("narration_speed", 1.0)

    if not scenes:
        print("ERROR: No scenes provided.")
        return False
    for i, s in enumerate(scenes):
        if s.get("type") != "svg" or not s.get("svg"):
            print(f"ERROR: scene {i+1} must be type 'svg' with 'svg' markup.")
            return False

    tmp = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="infographic_show_"))
    need_cleanup = not bool(work_dir)
    if work_dir:
        tmp.mkdir(parents=True, exist_ok=True)
    n = len(scenes)
    print(f"\n  === Generating {n} scene show: {title} ===")

    print("  [1/3] Narration...")
    scene_durations, audio_paths, audio_dir = generate_narration_scenes(
        scenes, voice, speed, min_dur, trans
    )

    print("  [2/3] Render SVG -> PNG...")
    png_paths = []
    for i, s in enumerate(scenes):
        png = tmp / f"scene_{i+1:03d}.png"
        render_scene_to_png(s.get("svg", ""), png)
        png_paths.append(png)
        print(f"    [{i+1}/{n}] {s.get('title','')[:44]}")

    print("  [3/3] Assemble MP4 (ffmpeg xfade)...")
    combined = tmp / "combined.wav"
    combined, _audio_dur = build_combined_audio(audio_paths, scene_durations, combined)
    total_video_dur = sum(scene_durations)

    input_args, filter_parts = [], []
    if n == 1:
        sdur = scene_durations[0]
        input_args = ["-loop", "1", "-t", str(sdur), "-i", str(png_paths[0])]
        filter_complex = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setpts=PTS-STARTPTS[v0]"
        )
        last = "[v0]"
    else:
        for i, png in enumerate(png_paths):
            input_args.extend(["-loop", "1", "-t", str(scene_durations[i]), "-i", str(png)])
        durations = scene_durations
        offset = durations[0] - trans
        for i in range(1, n):
            if i == 1:
                filter_parts.append(
                    f"[0][1]xfade=transition=fade:duration={trans}:offset={offset}[v1]"
                )
            else:
                filter_parts.append(
                    f"[v{i-1}][{i}]xfade=transition=fade:duration={trans}:offset={offset}[v{i}]"
                )
            offset += durations[i] - trans
        filter_complex = "; ".join(filter_parts)
        last = f"[v{n-1}]"

    cmd = [
        "ffmpeg", "-y", *input_args, "-i", str(combined),
        "-filter_complex", filter_complex, "-map", last, "-map", f"{n}:a",
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-r", "30",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        size = Path(output_path).stat().st_size / 1024
        print(f"  ✓ Video: {output_path} ({size:.0f} KB, {total_video_dur:.1f}s)")
        return True
    except subprocess.CalledProcessError as e:
        print("  FFmpeg failed:", e.stderr.decode()[:800])
        return False
    finally:
        if need_cleanup:
            shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(audio_dir, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(description="Generate a narrated infographic show (SVG -> MP4).")
    p.add_argument("--scenes", "-s", required=True, help="Scene JSON file")
    p.add_argument("--output", "-o", default="infographic_show.mp4", help="Output MP4 path")
    p.add_argument("--work-dir", "-w", help="Keep working dir for debugging")
    a = p.parse_args()
    with open(a.scenes) as f:
        data = json.load(f)
    ok = generate_video(data, a.output, a.work_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
