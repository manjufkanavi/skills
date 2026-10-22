#!/usr/bin/env python3
"""learning-forge engagement critic.

Two phases:
  --phase script : scores script.json against the engagement rubric
                   (hooks, pacing variance, re-hooks, open loops, dual coding,
                    monotony, citation, voice variety, CTA, word budget).
  --phase media  : scores the rendered final.mp4 (duration window, decode,
                   loudness, static-frame dead zones, SRT coverage, streams).

Exit 0 = no FAIL (WARNs tolerated); 1 = at least one FAIL.
Writes critic_<phase>.json to the project dir so the agent can iterate on it.
"""
import argparse, json, math, re, statistics, subprocess
from pathlib import Path

LL = ["-loglevel", "error"]
FORMAT_WORDS_PER_SEC = 2.4
FORMATS = {
    "pulse":      {"default_target": 60,   "scenes": (4, 7),   "min_rehooks": 0},
    "lesson":     {"default_target": 240,  "scenes": (6, 12),  "min_rehooks": 3},
    "deep_dive":  {"default_target": 660,  "scenes": (10, 22), "min_rehooks": 6},
}
CURIOSITY = re.compile(r"\?|!|never|not what|actually|wrong|lies|breaks|trap|catch|surprise|but |except|wait|twist", re.I)
REHOOK = re.compile(r"\?|but |twist|surprise|catch|wait |except|here'\s?s|here is|however|problem", re.I)

def word_count(s): return len(s.split())

def check_script(proj: Path):
    sc = json.loads((proj / "script.json").read_text())
    try:
        ped = json.loads((proj / "pedagogy.json").read_text())
    except FileNotFoundError:
        ped = None
    checks, fails = [], 0
    def add(name, ok, detail, hard=True):
        nonlocal fails
        status = "PASS" if ok else ("FAIL" if hard else "WARN")
        if not ok and hard: fails += 1
        checks.append({"check": name, "status": status, "detail": detail})
        print(f"  [{status}] {name}: {detail}")

    fmt = sc.get("format", "lesson"); spec = FORMATS[fmt]
    scenes = sc["scenes"]; target = sc.get("target_seconds", spec["default_target"])
    total_w = sum(word_count(l["text"]) for s in scenes for l in s["lines"])
    budget = 2.4 * target
    add("word_budget", 0.82 * budget <= total_w <= 1.25 * budget,
         f"{total_w} words (target {budget:.0f} @ 2.4wps for {target}s)", hard=True)
    add("scene_count", spec["scenes"][0] <= len(scenes) <= spec["scenes"][1],
         f"{len(scenes)} scenes (format {fmt} wants {spec['scenes'][0]}-{spec['scenes'][1]})", hard=True)

    # hook
    h = scenes[0]
    htext = " ".join(l["text"] for l in h["lines"])
    hw = word_count(htext)
    hook_ok = hw <= 18 and len(h["lines"]) <= 3
    curiosity = bool(CURIOSITY.search(htext))
    add("hook_strength", hook_ok and curiosity,
         f"hook {hw} words, curiosity_marker={curiosity} (want <=18w, <=3 lines, a curiosity trigger)", hard=True)

    # pacing variance (use duration_target if present, else estimate from words)
    durs = [s.get("duration_target") or word_count(" ".join(l["text"] for l in s["lines"])) / 2.4 for s in scenes]
    mean = statistics.fmean(durs); sd = statistics.pstdev(durs)
    cv = sd / mean if mean else 0
    add("pacing_variance", cv > 0.18, f"scene durations {['%.0f' % d for d in durs]}s, cv={cv:.2f} (want >0.18: rhythm!)", hard=True)
    same = sum(1 for a, b in zip(durs, durs[1:]) if abs(a - b) < 2)
    add("no_uniform_neighbors", same <= max(1, len(scenes) // 3),
         f"{same} adjacent scene pairs within 2s of each other")

    # re-hook density
    rh = sum(1 for s in scenes for l in s["lines"] if REHOOK.search(l["text"]))
    density = rh / (target / 20)
    add("rehook_density", rh >= spec["min_rehooks"] and density >= 0.5,
         f"{rh} re-hooks in {target}s = {density:.1f}/20s (want >= {spec['min_rehooks']} and >=1 per 40s)")

    # open loops
    loops = sc.get("open_loops", [])
    balanced = all(l.get("opened_in") and l.get("closed_in") and l["closed_in"] > l["opened_in"] for l in loops)
    add("open_loops", bool(loops) and balanced,
         f"{len(loops)} open loops, all balanced={balanced}" if loops else "no open loops declared (want >=1 for lesson/deep_dive)",
         hard=(fmt != "pulse"))

    # dual coding
    empty = sum(1 for s in scenes for l in s["lines"] if not l.get("visual", "").strip())
    all_lines = [l.get("visual", "").strip() for s in scenes for l in s["lines"]]
    uniq = len(set(all_lines))
    add("dual_coding", empty == 0, f"{empty} lines missing visual spec (every line needs a visual action)", hard=True)
    add("visual_variation", uniq >= 0.6 * len(all_lines), f"{uniq}/{len(all_lines)} distinct visual actions")

    # monotony
    wcs = [word_count(l["text"]) for s in scenes for l in s["lines"]]
    m = statistics.fmean(wcs); sd = statistics.pstdev(wcs)
    cv2 = sd / m if m else 0
    add("sentence_monotony", cv2 >= 0.25, f"line lengths mean={m:.1f} cv={cv2:.2f} (want >=0.25: vary sentence length)")

    # citation
    if ped:
        known = {c["id"] for c in ped.get("claims", [])} | {m["id"] for m in ped.get("misconceptions", [])} \
              | {a["id"] for a in ped.get("analogies", [])} | {e["id"] for e in ped.get("examples", [])}
        cited = {c for s in scenes for l in s["lines"] for c in l.get("claims", [])}
        dangling = cited - known
        add("citation", not dangling, f"all {len(cited)} cited ids resolve into pedagogy.json" if not dangling else f"dangling ids: {sorted(dangling)}", hard=True)
        add("sourced_depth", len(ped.get("claims", [])) >= 3 and len(ped.get("misconceptions", [])) >= 2 and len(ped.get("analogies", [])) >= 2 and len(ped.get("sources", [])) >= 3,
            f"pedagogy: {len(ped.get('claims',[]))} claims, {len(ped.get('misconceptions',[]))} misconceptions, {len(ped.get('analogies',[]))} analogies, {len(ped.get('sources',[]))} sources", hard=True)
    else:
        add("citation", False, "pedagogy.json missing — research+pedagogy stages not run", hard=True)

    # voice variety
    voices = {s.get("voice") for s in scenes} | {l.get("voice") for s in scenes for l in s["lines"]}
    if "second" in voices:
        add("voice_variety", True, "second voice in use")
    else:
        add("voice_variety", fmt == "pulse", f"single voice only ({'ok for pulse' if fmt == 'pulse' else 'lesson/deep_dive want a 2nd voice for the quiz/beat'})")

    # CTA
    add("cta", scenes[-1].get("role") == "cta", f"last scene role={scenes[-1].get('role')}", hard=False)

    return fails, checks, {"format": fmt, "target_seconds": target, "total_words": total_w,
                           "estimated_seconds": round(total_w / 2.4)}

def check_media(proj: Path):
    sc = json.loads((proj / "script.json").read_text())
    fmt = sc.get("format", "lesson"); target = sc.get("target_seconds", FORMATS[fmt]["default_target"])
    final = proj / "out" / "final.mp4"
    checks, fails = [], 0
    def add(name, ok, detail, hard=True):
        nonlocal fails
        status = "PASS" if ok else ("FAIL" if hard else "WARN")
        if not ok and hard: fails += 1
        checks.append({"check": name, "status": status, "detail": detail})
        print(f"  [{status}] {name}: {detail}")

    if not final.exists():
        add("final_exists", False, "out/final.mp4 missing — run produce.py first")
        return 1, checks
    d = float(subprocess.check_output(["ffprobe", *LL, "-show_entries", "format=duration",
                                       "-of", "default=noprint_wrappers=1:nokey=1", str(final)]).decode().strip())
    add("duration_window", abs(d - target) <= 0.12 * target, f"{d:.1f}s vs target {target}s (±12%)")
    res = subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"], capture_output=True)
    add("decode_clean", res.returncode == 0 and not res.stderr, "zero decode errors" if not res.stderr else res.stderr.decode()[:200])
    loud = subprocess.run(["ffmpeg", "-i", str(final), "-af", "loudnorm=print_format=summary",
                           "-f", "null", "-"], capture_output=True)
    m = re.search(r"Input Integrated:\s*(-?\d+\.?\d*)", loud.stderr.decode(errors=""))
    if m:
        i = float(m.group(1))
        add("loudness", -19 <= i <= -13, f"integrated {i} LUFS (want -16±3)")
    else:
        add("loudness", False, "could not measure loudness (no audio stream?)")
    # static-frame dead zone: scene-change events per 4s window
    sc_events = subprocess.run(["ffmpeg", "-i", str(final), "-vf",
        "select='gt(scene,0.02)',showinfo", "-f", "null", "-"], capture_output=True).stderr.decode(errors="")
    times = [float(x) for x in re.findall(r"pts_time:(\d+\.?\d*)", sc_events)]
    dead = 0
    for w0 in range(0, int(d), 4):
        if not any(w0 <= t < w0 + 4 for t in times):
            dead += 1
    add("no_dead_zones", dead <= max(1, d / 40), f"{dead} silent 4s windows without a scene change (want <= {max(1, d/40):.0f})")
    srt = proj / "out" / "subtitles.srt"
    if srt.exists():
        txt = srt.read_text().decode()
        cues = re.findall(r"--> (.+)$", txt, re.M)
        last = cues[-1] if cues else "00:00:00,000"
        hh, mm, rest = last.split(":"); end = int(hh) * 3600 + int(mm) * 60 + float(rest)
        cov = end / d if d else 0
        add("srt_coverage", len(cues) > 5 and cov >= 0.8, f"{len(cues)} cues, last ends {end:.0f}s ({cov:.0%} of video)")
    else:
        add("srt_coverage", False, "subtitles.srt missing")
    probe = subprocess.check_output(["ffprobe", *LL, "-show_entries", "stream=codec_name",
                                     "-of", "csv=p=0", str(final)]).decode().split()
    add("streams", "h264" in probe and "aac" in probe, f"streams: {probe}")
    return fails, checks, {"duration": d}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--phase", default="script", choices=["script", "media"])
    a = ap.parse_args()
    proj = Path(a.project).resolve()
    print(f"learning-forge critic: {a.phase} phase — {proj.name}")
    fails, checks, meta = (check_script(proj) if a.phase == "script" else check_media(proj))
    out = {"phase": a.phase, "fails": fails, "checks": checks, **(meta or {})}
    (proj / f"critic_{a.phase}.json").write_text(json.dumps(out, indent=1))
    print(f"\n{'=' * 46}\nVERDICT: {'FAIL' if fails else 'PASS'} — {fails} failing checks\n"
          f"report: {proj / f'critic_{a.phase}.json'}")
    raise SystemExit(1 if fails else 0)

if __name__ == "__main__":
    main()
