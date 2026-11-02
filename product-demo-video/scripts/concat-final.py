#!/usr/bin/env python3
"""Assemble the final video: intro title card + scene clips, size-budget aware.

usage:
  concat-final.py --out final.mp4 --inputs scene1.mp4 scene2.mp4 ...
                  [--title "IacGenie Tour" --subtitle "2-minute overview"]
                  [--w 1280 --h 720 --fps 30 --max-mb 48]

Steps:
  1. If --title: render a 2.5s intro card (render-card.py) with silent audio,
     encoded to the same normalized parameters as the scene clips.
  2. If --url: render a 1.5s browser-bar card (traffic lights + URL) — the
     "entering the URL" moment — after the title card.
  3. Concatenate all clips via the concat demuxer (stream copy).
  4. If the result exceeds --max-mb (Telegram bot upload limit ~50MB):
     re-encode at crf 27; if still over, re-encode at 960x540 crf 27.

Prints one JSON object: {"path": ..., "size_mb": ..., "duration_s": ...}
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER_CARD = os.path.join(SKILL_DIR, "scripts", "render-card.py")


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip() or 0)
    except ValueError:
        return 0.0


def size_mb(path: str) -> float:
    return os.path.getsize(path) / (1024 * 1024)


def make_card_clip(kind: str, title: str, subtitle: str, out: str, w: int, h: int, fps: int, seconds: float, url: str = "") -> bool:
    args = [sys.executable, RENDER_CARD, kind, "--w", str(w), "--h", str(h), "--out", out.replace(".mp4", ".png")]
    if kind == "browserbar":
        args += ["--url", url]
    else:
        args += ["--text", title]
        if subtitle:
            args += ["--sub", subtitle]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-500:] + "\n")
        return False
    card_png = out.replace(".mp4", ".png")
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", card_png,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(seconds),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


def reencode(src: str, dst: str, w: int, h: int, crf: int, scale: bool) -> bool:
    vf = [f"scale={w}:{h}"] if scale else []
    cmd = [
        "ffmpeg", "-y", "-i", src,
    ]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        dst,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--inputs", nargs="+", required=True, help="scene mp4 files, in playback order")
    ap.add_argument("--title", default="")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--url", default="", help="URL for the browser-bar 'entering the URL' card")
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=720)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--max-mb", type=float, default=48)
    a = ap.parse_args()

    for p in a.inputs:
        if not os.path.exists(p):
            sys.exit(f"missing input: {p}")

    tmpdir = tempfile.mkdtemp(prefix="pdv-final-")
    ordered = []
    if a.title:
        intro = os.path.join(tmpdir, "intro.mp4")
        if make_card_clip("card", a.title, a.subtitle, intro, a.w, a.h, a.fps, 2.5):
            ordered.append(intro)
            print("[intro] title card added (2.5s)", file=sys.stderr)
        else:
            print("[warn] intro card failed — continuing without it", file=sys.stderr)
    if a.url:
        urlbar = os.path.join(tmpdir, "urlbar.mp4")
        if make_card_clip("browserbar", "", "", urlbar, a.w, a.h, a.fps, 1.5, url=a.url):
            ordered.append(urlbar)
            print(f"[urlbar] entering-URL card added (1.5s, {a.url})", file=sys.stderr)
        else:
            print("[warn] url bar card failed — continuing without it", file=sys.stderr)
    ordered += a.inputs

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    listfile = os.path.join(tmpdir, "concat.txt")
    with open(listfile, "w") as f:
        for p in ordered:
            f.write(f"file '{os.path.abspath(p)}'\n")

    staged = os.path.join(tmpdir, "staged.mp4")
    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", staged],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-1500:] + "\n")
        sys.exit("concat failed (are all scene clips the same w/h/fps? re-run merge-scene.py on each)")

    final = staged
    mb = size_mb(staged)
    if mb > a.max_mb:
        print(f"[size] {mb:.1f}MB > {a.max_mb}MB budget — re-encoding at crf 27", file=sys.stderr)
        alt = os.path.join(tmpdir, "small1.mp4")
        if reencode(staged, alt, a.w, a.h, 27, scale=False) and size_mb(alt) < a.max_mb:
            final, mb = alt, size_mb(alt)
        else:
            alt2 = os.path.join(tmpdir, "small2.mp4")
            if reencode(staged, alt2, 960, 540, 27, scale=True) and size_mb(alt2) < a.max_mb:
                final, mb = alt2, size_mb(alt2)
                print("[size] dropped to 960x540", file=sys.stderr)
            else:
                print(f"[warn] still {mb:.1f}MB after re-encode — Telegram bot upload may fail (>50MB)", file=sys.stderr)

    if os.path.abspath(final) != os.path.abspath(a.out):
        subprocess.run(["cp", final, a.out], check=True)
    else:
        final = a.out
    print(json.dumps({"path": os.path.abspath(a.out), "size_mb": round(size_mb(a.out), 2), "duration_s": round(ffprobe_duration(a.out), 1)}))


if __name__ == "__main__":
    main()
