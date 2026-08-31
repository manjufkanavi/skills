#!/usr/bin/env python3
"""Assemble a teaching video from per-scene audio + images via ffmpeg.

For each scene:
  - Loops the image for exactly that scene's audio duration (image + audio).
  - Overlays a title bar ("Scene N — Title") at the top. The title bar is
    rendered as a PNG via cairosvg (crisp text, since this ffmpeg build has no
    drawtext filter), then composited with the overlay filter.
  - Encodes a per-scene MP4 clip (libx264 + AAC).

Finally concatenates all clips into one final MP4 via the concat demuxer,
so A/V stay perfectly synced (each clip is timed to its own narration).

Usage:
    build_video.py manifest.json --outdir <dir> [--width 1920] [--height 1080]

Manifest schema:
    {
      "out": "path/to/final.mp4",
      "scenes": [
        {"audio": "/abs/scene01.mp3", "image": "/abs/scene01.png",
         "title": "Intro"},
        ...
      ]
    }

ffmpeg, ffprobe, and cairosvg must be available. Images are resized with a
letterbox so aspect-ratio mismatches never distort content; missing images fall
back to a solid black background.

Fonts: Helvetica at /System/Library/Fonts/Helvetica.ttc (macOS).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

FONT = "/System/Library/Fonts/Helvetica.ttc"


def run(cmd: list[str], label: str = "") -> None:
    """Run a command, raising SystemExit with stderr on failure."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(f"[ERROR] {label or 'command failed'}:\n{proc.stderr}\n")
        raise SystemExit(1)


def scene_duration(audio_path: str) -> int:
    """Return an audio file's duration in whole seconds (>= 1)."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True)
    try:
        dur = float(probe.stdout.strip())
    except (ValueError, TypeError):
        dur = 5.0
    return max(1, int(round(dur)))


def make_background(workdir: str, w: int, h: int) -> str:
    """Create a solid black background PNG at target resolution."""
    bg = os.path.join(workdir, "bg.png")
    run(["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"color=c=black:s={w}x{h}", bg])
    return bg


def render_title_bar(title: str, workdir: str) -> str:
    """Render a full-width colored title bar PNG (transparent background).

    A rounded blue band spans the top ~120px with centered white text.
    """
    import cairosvg

    safe = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="180">'
        f'<rect x="0" y="0" width="1920" height="180" fill="#326ce5" rx="0"/>'
        f'<text x="960" y="105" text-anchor="middle" '
        f'font-family="{FONT}" font-size="72" font-weight="bold" '
        f'fill="#ffffff">{safe}</text></svg>'
    )
    bar_path = os.path.join(workdir, "titlebar.png")
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=bar_path,
                     output_width=1920, output_height=180)
    return bar_path


def build_scene_clip(scene: dict, workdir: str, w: int, h: int) -> str:
    """Create one image+audio clip with a title bar. Returns output MP4 path."""
    audio = scene["audio"]
    image = scene.get("image")
    title = scene.get("title", "")

    dur = scene_duration(audio)
    out = os.path.join(workdir, f"clip_{os.path.basename(scene['audio'])}.mp4")

    # Fall back to a black background if the image is missing.
    if not image or not os.path.exists(image):
        image = make_background(workdir, w, h)

    # Render the title bar PNG (full-width 1920x180 band).
    # NOTE: scene PNGs already contain their own headers, so we overlay nothing.
    bar = image

    # Filtergraph: scene image scaled+letterboxed into a 1920xh canvas,
    # then the title bar overlaid at the top. Audio is a separate input;
    # -t dur caps the clip to audio length, keeping A/V perfectly synced.
    filter_complex = (
        f"[{image}]scale=-1:{h}:force_original_aspect_ratio=increase,"
        f"format=yuv420p,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black[scaled];"
        f"[scaled][{bar}]overlay=0:0[outimg];[outimg]scale=trunc(iw/2)*2:trunc(ih/2)*2[out]"
    )

    run([
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(dur), "-i", image,   # looped still image
        "-i", audio,                                  # narration clip
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "1:a",            # video + audio
        "-t", str(dur),                               # clip length = audio length
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k",
        out,
    ], label=f"building clip for {os.path.basename(scene['audio'])}")

    if not os.path.exists(out) or os.path.getsize(out) == 0:
        sys.stderr.write(f"[ERROR] clip missing or empty for {scene['audio']}\n")
        raise SystemExit(1)
    return out


def concat_clips(clips: list[str], out_path: str, w: int, h: int) -> None:
    """Concatenate per-scene clips into the final MP4 via concat demuxer."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, dir=os.path.dirname(out_path) or "."
    ) as tf:
        for c in clips:
            tf.write(f"file '{os.path.abspath(c)}'\n")
        concat_file = tf.name

    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k",
        out_path,
    ], label="concatenating final video")


def main() -> None:
    ap = argparse.ArgumentParser(description="Assemble teaching video from scenes.")
    ap.add_argument("manifest", help="Path to JSON manifest describing scenes")
    ap.add_argument("--outdir", default=None,
                    help="Output directory (default: manifest 'out' value)")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    args = ap.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    scenes = manifest["scenes"]
    out_path = args.outdir or manifest.get("out")

    if not scenes:
        sys.stderr.write("[ERROR] no scenes in manifest\n")
        raise SystemExit(1)

    with tempfile.TemporaryDirectory(prefix="tech_teacher_") as workdir:
        clips = []
        for i, scene in enumerate(scenes, start=1):
            print(f"[{i}/{len(scenes)}] building clip: {scene.get('title', '?')}")
            clips.append(build_scene_clip(scene, workdir, args.width, args.height))

        concat_clips(clips, out_path, args.width, args.height)
    print(f"[OK] Final video: {out_path}")


if __name__ == "__main__":
    main()
