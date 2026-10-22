#!/usr/bin/env python3
"""learning-forge production runner.

Inputs (project dir):
  script.json   engagement script (scenes -> lines with prosody + visual specs)
  script.py     Manim scene classes (class names MUST equal scene ids in script.json)

Pipeline: TTS(prosody) -> music bed -> manim render -> align(no-freeze) -> stitch
          -> mix(ducked music) + loudnorm -> SRT + scene_offsets.json
Outputs (project/out/): final.mp4, subtitles.srt, scene_offsets.json, full_narration.wav

Interpreter auto-detection:
  prefers the skill-local .venv (built by scripts/setup.sh) when it has BOTH
  manim and kokoro_onnx; otherwise splits: manim from ~/.manim-env, TTS from system python3.
"""
import argparse, json, math, os, re, subprocess, time, wave, array, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ASSETS = SKILL / "assets" / "kokoro"
LL = ["-loglevel", "error"]

def progress(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def run(args, **kw):
    subprocess.run([str(a) for a in args], check=True, **kw)

def ffmpeg(args):
    run(["ffmpeg", *LL, "-y", *args])

def probe_dur(path):
    out = subprocess.check_output(["ffprobe", *LL, "-show_entries", "format=duration",
                                   "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(out.decode().strip())

def pick_interpreters():
    cands = [SKILL / ".venv" / "bin" / "python",
             Path.home() / "manim-env" / "bin" / "python",
             Path(sys.executable), Path("/usr/bin/env"), ]
    tts_py = manim_py = None
    for c in cands:
        if not c.exists() or c.name == "env":
            if c.name == "env":
                continue
            continue
        ok_m = subprocess.run([str(c), "-c", "import manim"], capture_output=True).returncode == 0
        ok_k = subprocess.run([str(c), "-c", "import kokoro_onnx"], capture_output=True).returncode == 0
        if ok_m: manim_py = manim_py or str(c)
        if ok_k: tts_py = tts_py or str(c)
    if tts_py is None:
        # fall back to plain python3 (system 3.14 has kokoro_onnx on this host)
        if subprocess.run(["python3", "-c", "import kokoro_onnx"], capture_output=True).returncode == 0:
            tts_py = "python3"
    if not manim_py or not tts_py:
        sys.exit(f"ERROR: need interpreters. manim={'yes' if manim_py else 'NO'} tts={'yes' if tts_py else 'NO'} — run scripts/setup.sh")
    progress(f"interpreters: manim={manim_py}  tts={tts_py}")
    return manim_py, tts_py

def split_sentences(text, maxchars=300):
    if len(text) <= maxchars: return [text]
    parts = re.split(r'(?<=[.!?])\s+', text)
    out, cur = [], ""
    for p in parts:
        if len(cur) + len(p) + 1 > maxchars and cur:
            out.append(cur); cur = p
        else:
            cur = f"{cur} {p}".strip()
        if len(p) > maxchars:            # single giant sentence: hard-split on words
            words = p.split()
            for w in words:
                if len(cur) + len(w) + 1 > maxchars and cur: out.append(cur); cur = ""
                cur = f"{cur} {w}".strip()
    if cur: out.append(cur)
    return [x for x in out if x]

def write_wav(path, samples, sr):
    a = array.array("h", [int(max(-1.0, min(1.0, float(v))) * 32767) for v in samples])
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(a.tobytes())

def to_np(x):
    import numpy as np
    out = []
    def rec(o):
        try: it = iter(o)
        except TypeError: out.append(float(o)); return
        for e in it: rec(e)
    rec(x); return np.asarray(out, dtype=np.float32)

def synth_scenes(script, out_dir):
    """Per-line Kokoro synthesis with prosody. Returns {scene_id: (wav_path, line_offsets, line_texts)}"""
    import numpy as np
    from kokoro_onnx import Kokoro
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    model, voices = ASSETS / "model.onnx", ASSETS / "voices-v1.0.bin"
    if not model.exists():
        sys.exit("ERROR: Kokoro weights missing — run scripts/setup.sh")
    t0 = time.time()
    k = Kokoro(str(model), str(voices))
    progress(f"Kokoro loaded in {time.time()-t0:.1f}s")
    sr = 24000
    LINE_GAP = int(0.35 * sr)      # breath between lines
    results = {}
    total_words = 0
    for sc in script["scenes"]:
        sid = sc["id"]; voice = sc.get("voice") or script.get("voice", {}).get("main", "af_bella")
        if voice == "second": voice = script["voice"]["second"]
        segs, line_info = [], []
        for ln in sc["lines"]:
            text = ln["text"].strip()
            total_words += len(text.split())
            t0 = time.time()
            pieces = []
            for chunk in split_sentences(text):
                a, s = k.create(chunk, voice=voice, speed=float(ln.get("speed", 1.0)))
                pieces.append(to_np(a))
            a = np.concatenate(pieces)
            pb = int(ln.get("pause_before_ms", 0) / 1000 * sr)
            a = np.concatenate([np.zeros(pb, np.float32), a, np.zeros(int(0.15 * sr), np.float32)])
            wpath = out_dir / f"{sid}_s{len(segs):02d}.wav"
            write_wav(wpath, a, s)
            segs.append(wpath)
            line_info.append({"text": text, "dur": len(a) / s})
            progress(f"  {sc['role']:<9} {a.shape[0]/s:5.2f}s  {len(pieces)}seg {time.time()-t0:4.1f}x  {text[:48]}")
        # concat scene lines with gaps; last scene gets a short tail, others 0.6s
        is_last = sc is script["scenes"][-1]
        tail = int((0.15 if is_last else 0.6) * sr)
        import wave as _w
        audio = []
        for i, (wpath, li) in enumerate(zip(segs, line_info)):
            with _w.open(str(wpath)) as wf:
                raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype="int16").astype(np.float32) / 32767
            if i > 0: audio.append(np.zeros(LINE_GAP, np.float32))
            audio.append(raw)
        audio.append(np.zeros(tail, np.float32))
        scene_audio = np.concatenate(audio)
        swav = out_dir / f"{sid}_audio.wav"
        write_wav(swav, scene_audio, sr)
        # line offsets within scene (for SRT)
        off, offs = 0.0, []
        for i, (wpath, li) in enumerate(zip(segs, line_info)):
            if i > 0: off += LINE_GAP / sr
            offs.append({"start": off, "end": off + li["dur"]})
            off += li["dur"]
        results[sid] = {"wav": swav, "dur": len(scene_audio) / sr, "lines": line_info, "offsets": offs}
    progress(f"TTS done: {total_words} words, {sum(r['dur'] for r in results.values()):.0f}s narration")
    return results

def make_music(total_dur, out_dir):
    out_dir = Path(out_dir)
    p = out_dir / "music.wav"
    if p.exists(): return p
    # soft ambient pad: A2-E3-A3-D4, lowpassed, slow tremolo, very quiet
    ffmpeg(["-f", "lavfi", "-i", "sine=f=110", "-f", "lavfi", "-i", "sine=f=164.81",
            "-f", "lavfi", "-i", "sine=f=220", "-f", "lavfi", "-i", "sine=f=293.66",
            "-filter_complex",
            "[0][1][2][3]amix=inputs=4:normalize=0,lowpass=f=650,tremolo=f=0.07:d=0.35,volume=0.055[a]",
            "-t", f"{total_dur:.2f}", "-map", "[a]", "-ar", "24000", "-ac", "1", str(p)])
    progress(f"music bed generated ({total_dur:.0f}s)")
    return p

QMAP = {"ql": ("480p15", 15, 854, 480), "qm": ("720p30", 30, 1280, 720), "qh": ("1080p60", 60, 1920, 1080)}

def render_scenes(manim_py, script_py, scenes, quality, out_dir):
    qdir, fps, w, h = QMAP[quality]
    out_dir = Path(out_dir)
    clips = []
    t0 = time.time()
    for sc in scenes:
        sid = sc["id"]
        clip = script_py.parent / "media" / "videos" / script_py.stem / qdir / f"{sid}.mp4"
        if not clip.exists():
            progress(f"rendering {sid} ({quality})...")
            run([manim_py, "-m", "manim", f"-{quality}", str(script_py), sid], cwd=script_py.parent)
        clips.append((sc, clip))
        progress(f"  {sid} done ({time.time()-t0:.0f}s elapsed total)")
    return clips

def align_scene(clip, scene_dur, fps, w, h, work_dir, sid):
    """Match clip to narration length WITHOUT freezing: slow push-in (zoompan) on last frame."""
    work_dir = Path(work_dir)
    d = probe_dur(clip)
    if d >= scene_dur - 0.05:
        return clip, d
    extra = math.ceil((scene_dur - d) * 2) / 2.0
    last = work_dir / f"{sid}_last.png"
    ffmpeg(["-i", str(clip), "-vf", "reverse,select=eq(n\\,0)", "-vframes", "1", "-update", "1", str(last)])
    zoom = work_dir / f"{sid}_zoom.mp4"
    ffmpeg(["-loop", "1", "-t", f"{extra:.2f}", "-r", str(fps), "-i", str(last),
            "-vf", f"zoompan=z='min(zoom+0.0012,1.18)':d=1:s={w}x{h}:fps={fps},scale={w}:{h}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-profile:v", "high", str(zoom)])
    padded = work_dir / f"{sid}_padded.mp4"
    ct = work_dir / f"{sid}_cc.txt"
    ct.write_text(f"file '{clip.resolve()}'\nfile '{zoom.resolve()}'\n")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(ct), "-c:v", "libx264",
            "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-level", "4.2", str(padded)])
    progress(f"  {sid}: clip {d:.1f}s + {extra:.1f}s push-in tail -> {d+extra:.1f}s (audio {scene_dur:.1f}s)")
    return padded, probe_dur(padded)

def fmt_ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"

def write_srt(script, scene_results, scene_starts, out_path):
    lines = []
    for i, sc in enumerate(script["scenes"]):
        r = scene_results[sc["id"]]
        for ln, off in zip(r["lines"], r["offsets"]):
            t0 = scene_starts[i] + off["start"]; t1 = scene_starts[i] + off["end"]
            lines.append(f"{len(lines)+1}\n{fmt_ts(max(0,t0))} --> {fmt_ts(max(t0+0.2,t1))}\n{ln['text']}\n")
    out_path.write_text("\n".join(lines))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--quality", default="qm", choices=["ql", "qm", "qh"])
    ap.add_argument("--no-music", action="store_true")
    a = ap.parse_args()
    proj = Path(a.project).resolve()
    script = json.loads((proj / "script.json").read_text())
    script_py = proj / "script.py"
    if not script_py.exists(): sys.exit("ERROR: script.py (Manim scenes) missing")
    out = proj / "out"; work = proj / "work"; out.mkdir(exist_ok=True); work.mkdir(exist_ok=True)
    qdir, fps, w, h = QMAP[a.quality]

    manim_py, tts_py = pick_interpreters()
    progress("STEP 1/6 TTS (Kokoro, per-line prosody)")
    t0 = time.time()
    scene_results = synth_scenes(script, work / "tts")
    progress(f"TTS total {time.time()-t0:.0f}s")

    progress("STEP 2/6 render Manim scenes")
    clips = render_scenes(manim_py, script_py, script["scenes"], a.quality, work)

    progress("STEP 3/6 align clips to narration (no-freeze push-in)")
    aligned, starts, cum = [], [], 0.0
    for sc, clip in clips:
        r = scene_results[sc["id"]]
        p, d = align_scene(clip, r["dur"], fps, w, h, work, sc["id"])
        aligned.append(p); starts.append(cum); cum += d
    total = cum
    progress(f"video total {total:.1f}s across {len(aligned)} scenes")

    progress("STEP 4/6 stitch")
    allc = work / "allc.txt"
    allc.write_text("\n".join(f"file '{p.resolve()}'" for p in aligned) + "\n")
    master = out / "master.mp4"
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(allc),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
            "-movflags", "+faststart", str(master)])

    progress("STEP 5/6 audio mix (narration + ducked music) + loudnorm")
    narr_concat = work / "narr_concat.txt"
    narr_concat.write_text("\n".join(f"file '{scene_results[s['id']]['wav'].resolve()}'" for s in script["scenes"]) + "\n")
    narr = work / "full_narration.wav"
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(narr_concat), "-c", "copy", str(narr)])
    music = None if a.no_music or not script.get("music", True) else make_music(total, work)
    final = out / "final.mp4"
    if music:
        ffmpeg(["-i", str(master), "-i", str(narr), "-i", str(music),
                "-filter_complex",
                "[1:a]aformat=sample_rates=24000[voice];"
                "[2:a]aformat=sample_rates=24000,sidechaincompress=threshold=0.02:ratio=8:attack=20:release=350[mus];"
                "[voice][mus]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRU=-13[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", "-shortest", str(final)])
    else:
        ffmpeg(["-i", str(master), "-i", str(narr),
                "-filter_complex", "[1:a]loudnorm=I=-16:TP=-1.5:LRU=-13[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", "-shortest", str(final)])

    progress("STEP 6/6 SRT + scene offsets + manifest")
    write_srt(script, scene_results, starts, out / "subtitles.srt")
    offsets = {sc["id"]: {"role": sc.get("role"), "start": round(starts[i], 3),
                          "end": round(starts[i] + probe_dur(aligned[i]), 3)}
               for i, sc in enumerate(script["scenes"])}
    (out / "scene_offsets.json").write_text(json.dumps(offsets, indent=1))
    (out / "full_narration.wav")  # narr stays in work/; copy for reference
    import shutil; shutil.copy(narr, out / "full_narration.wav")
    d = probe_dur(final)
    progress(f"DONE: {final}  duration={d:.1f}s  size={final.stat().st_size/1e6:.1f}MB")

if __name__ == "__main__":
    main()
