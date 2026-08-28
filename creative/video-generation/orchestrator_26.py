#!/usr/bin/env python3
"""Orchestrator: generate 26 Kimiko video styles (unique paths), then sync narration."""
import json, os, subprocess, sys, time
from pathlib import Path

SKILL = Path("/Users/manjunathkanavi/.hermes/skills/creative/video-generation")
FASTVIDEO = Path("/Users/manjunathkanavi/.studio/FastVideo")
PYTHON = sys.executable

# ---- config ----
STYLES_FILE = SKILL / "styles" / "kimiki_styles.txt"
NARRATION = "/Users/manjunathkanavi/.hermes/skills/creative/video-generation/narration/kimiko_hi.wav"
OUT = SKILL / "videos_26"            # generated silent clips (unique paths)
FINAL = SKILL / "final_26"           # synced videos with audio
SCRIPT = FASTVIDEO / "examples/inference/basic/mlx_wan22_generate.py"

# shared cache of all styles (populated before parallel generation)
STYLES_CACHE: list[str] = []

# narration duration in seconds (measured earlier)
NARR_LEN = 3.5


def read_styles():
    lines = [l.strip() for l in STYLES_FILE.read_text().splitlines() if l.strip()]
    return lines


def unique_video_path(style: str) -> Path:
    """Return a safe, unique output path for this style (no collisions)."""
    slug = "".join(c if c.isalnum() else "_" for c in style)[:40]
    return OUT / f"{slug}.mp4"


def _generate_one(i: int, style: str) -> None:
    """Generate a single style's video (runs in its own process)."""
    total = len(STYLES_CACHE)
    outp = unique_video_path(style)
    if outp.exists() and outp.stat().st_size > 10_000:
        print(f"[{i+1}/{total}] SKIP (exists): {style[:45]}", flush=True)
        return

    seed = (i + 7) * 13 % 9999
    cmd = [PYTHON, str(SCRIPT), "--prompt", style,
           "--text-encoder-root", "/Users/manjunathkanavi/.lmstudio/models/FastMetal-5B-QAD",
           "--mlx-checkpoint", "/Users/manjunathkanavi/.lmstudio/models/FastMetal-5B-QAD",
           "--vae-root", "/Users/manjunathkanavi/.lmstudio/models/FastMetal-5B-QAD/vae",
           "--output-path", str(outp),
           "--seed", str(seed), "--flow-shift", "5.0", "--fast"]

    print(f"\n[{i+1}/{total}] GENERATE: {style[:50]}", flush=True)
    t = time.time()
    r = subprocess.run(cmd, cwd=str(FASTVIDEO), capture_output=True, text=True)
    elapsed = time.time() - t

    if r.returncode != 0 or not outp.exists():
        print(f"  FAIL rc={r.returncode} size={outp.stat().st_size if outp.exists() else 0}", flush=True)
        print("   " + (r.stderr[-400:] if r.stderr else "(no stderr)"), flush=True)
        return

    print(f"  DONE in {elapsed:.0f}s -> {outp.name}", flush=True)


def generate_all(max_workers: int = 2):
    """Generate all styles with at most max_workers running simultaneously."""
    global STYLES_CACHE
    from concurrent.futures import ThreadPoolExecutor

    styles = read_styles()
    STYLES_CACHE = styles
    total = len(styles)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(_generate_one, range(total), styles))

    # count completed
    done = sum(1 for s in styles if unique_video_path(s).exists() and unique_video_path(s).stat().st_size > 10_000)
    return total, done


def sync_all():
    """Mux narration into each silent video (trim to match)."""
    videos = sorted(OUT.glob("*.mp4"))
    total, done = len(videos), 0
    for i, v in enumerate(videos):
        stem = v.stem
        outp = FINAL / f"{stem}.mp4"
        if outp.exists() and outp.stat().st_size > 10_000:
            print(f"[{i+1}/{total}] SKIP sync exists", flush=True)
            done += 1
            continue

        # find narration wav with matching name; fallback to the one we made
        narr = None
        cand = (SKILL / "narration" / f"{stem}.wav")
        if cand.exists():
            narr = str(cand)
        else:
            # use the first narration wav we have as generic fallback
            alln = list((SKILL / "narration").glob("*.wav"))
            if alln:
                narr = str(alln[0])

        cmd = ["ffmpeg", "-y", "-i", str(v), "-i", narr,
               "-map", "0:v:0", "-map", "1:a:0",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
               "-t", str(NARR_LEN), str(outp)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and outp.exists() and outp.stat().st_size > 10_000:
            print(f"[{i+1}/{total}] SYNCED -> {outp.name}", flush=True)
            done += 1
        else:
            print(f"  SYNC FAIL rc={r.returncode}", flush=True)

    return total, done


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    result = {}
    if stage in ("generate", "all"):
        t, d = generate_all()
        result["generated"] = {"total": t, "done": d}
    if stage in ("sync", "all"):
        # small pause to let any last file flush from disk
        time.sleep(1)
        t, d = sync_all()
        result["synced"] = {"total": t, "done": d}

    print("\nRESULT:", json.dumps(result))
    sys.exit(0 if result.get("generated", {}).get("done") == result.get("generated", {}).get("total") else 1)
