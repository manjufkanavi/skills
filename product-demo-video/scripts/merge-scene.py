#!/usr/bin/env python3
"""Merge one scene: screencast webm + narration mp3 (+ optional caption bar) -> mp4.

usage:
  merge-scene.py --video scene.webm --audio scene.mp3 --out scene.mp4
                 [--caption cap.png --caption-dur 4.5 --caption-h 96]
                 [--w 1280 --h 720 --fps 30 --crf 24]

Scene length = max(video, audio):
  audio  longer than video -> freeze the last video frame for the difference (tpad clone)
  video  longer than audio -> pad audio with silence (apad + atrim)

Output is always normalized (w/h/fps/pix_fmt + AAC 128k stereo 44.1kHz) so
clips from all scenes can be stream-copy concatenated by concat-final.py.
"""
import argparse
import os
import subprocess
import sys


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
    ap.add_argument("--video", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--caption", default="", help="transparent PNG caption bar (bottom)")
    ap.add_argument("--caption-dur", type=float, default=4.5)
    ap.add_argument("--caption-h", type=int, default=96, help="must match the caption PNG height")
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=720)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=24)
    a = ap.parse_args()

    for p in (a.video, a.audio):
        if not os.path.exists(p):
            sys.exit(f"missing input: {p}")
    if a.caption and not os.path.exists(a.caption):
        sys.exit(f"missing caption: {a.caption}")

    vdur = ffprobe_duration(a.video)
    adur = ffprobe_duration(a.audio)
    if vdur <= 0:
        sys.exit(f"video has no duration (broken/empty webm?): {a.video}")

    vchain = (
        f"scale={a.w}:{a.h}:force_original_aspect_ratio=decrease,"
        f"pad={a.w}:{a.h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={a.fps}"
    )
    achain = "aformat=sample_rates=44100:channel_layouts=stereo"

    inputs = ["-i", a.video, "-i", a.audio]
    if adur > vdur + 0.3:
        vchain += f",tpad=stop_mode=clone:stop_duration={adur - vdur:.3f}"
        print(f"[scene] audio {adur:.1f}s > video {vdur:.1f}s — freezing last frame for {adur - vdur:.1f}s", file=sys.stderr)
    elif vdur > adur + 0.3:
        achain += f",apad,atrim=0:{vdur:.3f}"
        print(f"[scene] video {vdur:.1f}s > audio {adur:.1f}s — padding silence for {vdur - adur:.1f}s", file=sys.stderr)

    has_cap = bool(a.caption) and os.path.exists(a.caption)
    if has_cap:
        inputs += ["-i", a.caption]

    fc = f"[0:v]{vchain}"
    if has_cap:
        fc += f"[v1];[v1][2:v]overlay=x=0:y={a.h - a.caption_h}:enable='lt(t,{a.caption_dur})'[vout]"
    else:
        fc += "[vout]"
    fc += f";[1:a]{achain}[aout]"

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(a.crf),
        "-pix_fmt", "yuv420p", "-r", str(a.fps),
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        a.out,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-1500:] + "\n")
        sys.exit(f"ffmpeg merge failed for {a.out}")
    print(f"[ok] {a.out} ({ffprobe_duration(a.out):.1f}s)")


if __name__ == "__main__":
    main()
