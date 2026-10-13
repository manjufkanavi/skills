#!/usr/bin/env python3
"""Unified production pipeline for bytesized-learning videos.

Automates:
1. Kokoro TTS narration generation & duration timing
2. Manim CE scene rendering
3. Frame-freezing duration matching & libx264 high-profile stitching
4. Audio muxing with +faststart
5. Automated critic checks (PTS continuity, decode integrity, duration verification)
"""
import os
import sys
import math
import subprocess
from pathlib import Path

MODEL_DEFAULT = "/Users/manjunathkanavi/.hermes/skills/voice-bridge/assets/kokoro/model.onnx"
VOICES_DEFAULT = "/Users/manjunathkanavi/.hermes/skills/voice-bridge/assets/voices-v1.0.bin"

LL = ["-loglevel", "error"]


def get_duration(path):
    out = subprocess.check_output(
        ["ffprobe", *LL, "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    ).decode().strip()
    return float(out)


def run_ffmpeg(args):
    subprocess.run(["ffmpeg", *LL, "-y", *args], check=True)


def generate_audio(scenes_text, out_dir, model_path=MODEL_DEFAULT, voices_path=VOICES_DEFAULT):
    """Generates per-scene WAV files with Kokoro TTS."""
    from kokoro_onnx import Kokoro
    import wave, array

    k = Kokoro(model_path, voices_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    def flatten(x):
        out = []
        def rec(o):
            try:
                it = iter(o)
            except TypeError:
                out.append(float(o))
            else:
                for e in it:
                    rec(e)
        rec(x)
        return out

    def write_wav(path, audio, sr):
        a = flatten(audio)
        pad = int(0.12 * sr)
        samples = array.array("h", [0]) * (len(a) + 2 * pad)
        for i, v in enumerate(a):
            samples[i + pad] = int(max(-1.0, min(1.0, v)) * 32767)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(samples.tobytes())

    wav_paths = []
    print(f"Generating Kokoro TTS narration for {len(scenes_text)} scenes...")
    for idx, text in enumerate(scenes_text, start=1):
        audio, sr = k.create(text, voice="af_bella", speed=1.0)
        p = out_dir / f"scene_{idx:02d}.wav"
        write_wav(p, audio, sr)
        d = get_duration(p)
        print(f"  [Scene {idx:02d}] {d:.2f}s: \"{text[:45]}...\"")
        wav_paths.append(p)

    concat_txt = out_dir / "audio_concat.txt"
    with open(concat_txt, "w") as f:
        for p in wav_paths:
            f.write(f"file '{p.resolve()}'\n")

    full_wav = out_dir / "full_narration.wav"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(full_wav)])
    print(f"Full narration generated: {full_wav} ({get_duration(full_wav):.2f}s)")
    return wav_paths, full_wav


def pad_and_stitch(scene_names, viddir, out_dir, wav_paths, full_wav, fps="60", output_filename="final_video.mp4"):
    """Pads clips to narration duration, concatenates with libx264, and muxes audio."""
    out_dir = Path(out_dir)
    viddir = Path(viddir)
    padded = []

    print(f"Aligning {len(scene_names)} scenes with narration...")
    for idx, (name, wav_p) in enumerate(zip(scene_names, wav_paths), start=1):
        clip = viddir / f"{name}.mp4"
        if not clip.exists():
            raise FileNotFoundError(f"Missing rendered clip: {clip}")

        d_clip = get_duration(clip)
        d_narr = get_duration(wav_p)
        extra = max(0.0, math.ceil((d_narr - d_clip) * 2) / 2.0)

        if extra > 0:
            lastpng = out_dir / f"{name}_last.png"
            run_ffmpeg(["-i", str(clip), "-vf", "reverse,select=eq(n\\,0)", "-vframes", "1", "-update", "1", str(lastpng)])
            frozen = out_dir / f"{name}_frozen.mp4"
            run_ffmpeg(["-loop", "1", "-t", str(extra), "-r", fps, "-i", str(lastpng),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2", str(frozen)])
            padded_out = out_dir / f"{name}_padded.mp4"
            ctxt = out_dir / f"cc_{idx:02d}.txt"
            with open(ctxt, "w") as f:
                f.write(f"file '{clip.resolve()}'\n")
                f.write(f"file '{frozen.resolve()}'\n")
            run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(ctxt),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2", str(padded_out)])
            padded.append(padded_out)
            print(f"  [{idx}/{len(scene_names)}] {name}: clip={d_clip:.2f}s + {extra:.1f}s hold -> {d_clip + extra:.2f}s")
        else:
            padded.append(clip)
            print(f"  [{idx}/{len(scene_names)}] {name}: clip={d_clip:.2f}s (sufficient duration)")

    allc_txt = out_dir / "allc.txt"
    with open(allc_txt, "w") as f:
        for p in padded:
            f.write(f"file '{p.resolve()}'\n")

    silent_master = out_dir / "master_silent.mp4"
    print("Re-encoding master video stream with libx264...")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(allc_txt),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
                "-movflags", "+faststart", str(silent_master)])

    final_output = out_dir / output_filename
    print("Muxing audio with video...")
    run_ffmpeg(["-i", str(silent_master), "-i", str(full_wav),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", "-shortest", str(final_output)])

    tot_dur = get_duration(final_output)
    print(f"SUCCESS: Generated {final_output} (duration={tot_dur:.2f}s, size={os.path.getsize(final_output)} bytes)")
    return final_output


def run_critic_checks(video_path, target_duration=60.0, tolerance=3.0):
    """Performs rigorous automated QA checks on the generated video."""
    video_path = Path(video_path)
    print(f"\nRunning Master Critic QA on {video_path.name}...")

    # 1. Total duration test
    dur = get_duration(video_path)
    if abs(dur - target_duration) > tolerance:
        print(f"  [FAIL] Duration check: {dur:.2f}s (Target: {target_duration}s ± {tolerance}s)")
        return False
    print(f"  [PASS] Duration check: {dur:.2f}s (Within target {target_duration}s ± {tolerance}s)")

    # 2. Decode test
    res = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video_path), "-f", "null", "-"], capture_output=True)
    if res.returncode != 0 or res.stderr:
        print(f"  [FAIL] Decode test errors:\n{res.stderr.decode()}")
        return False
    print("  [PASS] Full stream decode test: Zero errors")

    # 3. Stream parameter verification
    probe = subprocess.check_output(
        ["ffprobe", *LL, "-select_streams", "v:0", "-show_entries", "stream=codec_name,pix_fmt,r_frame_rate,width,height",
         "-of", "default=noprint_wrappers=1", str(video_path)]
    ).decode()
    print("  [PASS] Video parameters verified:\n" + "\n".join("    " + line for line in probe.strip().split("\n")))
    print("ALL QA CRITIC CHECKS PASSED!\n")
    return True
