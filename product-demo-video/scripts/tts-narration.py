#!/usr/bin/env python3
"""Generate per-scene Kokoro narration for a product-demo-video scenario.

usage:
  tts-narration.py <scenario.yaml> --run-dir <dir> [--voice im_nicola] [--speed 0.9] [--production]

Writes <run-dir>/audio/scene_NN_<id>.mp3 for every scene that has narration,
and prints a JSON manifest on stdout:
  [{"scene": 1, "id": "hero", "file": ".../scene_01_hero.mp3", "duration": 12.3}, ...]
(Progress lines go to stderr.)

TTS engine (sibling skill, resolved relative to this skill's install dir):
  default      ../kokoro-tts/scripts/tts.py                     (local ONNX, offline)
  --production ../kokoro-tts-production/scripts/kokoro_tts.py   (hosted API, needs network)

Voice/speed defaults come from the scenario file (voice: / speed:), else
im_nicola @ 0.9.
"""
import argparse
import json
import os
import subprocess
import sys

import yaml

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.dirname(SKILL_DIR)
LOCAL_TTS = os.path.join(SKILLS_DIR, "kokoro-tts", "scripts", "tts.py")
PROD_TTS = os.path.join(SKILLS_DIR, "kokoro-tts-production", "scripts", "kokoro_tts.py")


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip() or 0)
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--voice", default=None, help="overrides scenario voice")
    ap.add_argument("--speed", type=float, default=None, help="overrides scenario speed")
    ap.add_argument("--production", action="store_true", help="use hosted kokoro-tts-production API")
    a = ap.parse_args()

    with open(a.scenario) as f:
        sc = yaml.safe_load(f) or {}
    voice = a.voice or sc.get("voice") or "im_nicola"
    speed = a.speed if a.speed is not None else (sc.get("speed") or 0.9)

    tts = PROD_TTS if a.production else LOCAL_TTS
    if not os.path.exists(tts):
        sys.exit(f"ERROR: TTS script not found: {tts}\nInstall the sibling skill (kokoro-tts or kokoro-tts-production) next to product-demo-video.")

    adir = os.path.join(a.run_dir, "audio")
    os.makedirs(adir, exist_ok=True)

    manifest = []
    for i, scene in enumerate(sc.get("scenes") or [], 1):
        sid = scene.get("id") or f"{i:02d}"
        out = os.path.join(adir, f"scene_{i:02d}_{sid}.mp3")
        text = (scene.get("narration") or "").strip()
        if not text:
            print(f"[warn] scene {i} ({sid}) has no narration — no audio", file=sys.stderr)
            continue
        cmd = [sys.executable, tts, text, "-v", voice, "-s", str(speed), "-f", "mp3", "-o", out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(out):
            sys.stderr.write(r.stderr[-1000:] + "\n")
            sys.exit(f"ERROR: TTS failed for scene {i} ({sid})")
        entry = {"scene": i, "id": sid, "file": out, "duration": round(ffprobe_duration(out), 2)}
        manifest.append(entry)
        print(f"[ok] scene {i} ({sid}): {entry['duration']}s audio", file=sys.stderr)

    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
