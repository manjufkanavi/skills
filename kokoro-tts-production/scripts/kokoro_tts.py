#!/usr/bin/env python3
"""Synthesize speech audio from any text via the live public Kokoro TTS API.

Endpoint: https://kokoro.iacgenie.com/v1/audio/speech (Cloudflare Tunnel ->
nginx :80 -> kokoro-1:8881). The API key is fetched over SSH from the
homeserver at call time — no secret is stored locally or in this repo.

Example:
    python3 kokoro_tts.py "Hello world"                       # default af_heart, MP3
    python3 kokoro_tts.py "Buongiorno" -v im_nicola -s 0.85
    python3 kokoro_tts.py --list-voices
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

DEFAULT_BASE = "https://kokoro.iacgenie.com"
SSH_HOST = "mkanavi@192.168.0.116"
SSH_KEY = "~/.ssh/home-server"
API_KEY_PATH = "/home/mkanavi/docker/kokoro/.api_key"

# Voices verified against the public API (see references/voices.md for full list).
DEFAULT_VOICE = "af_heart"


def run_ssh(command: str, timeout: int) -> subprocess.CompletedProcess | None:
    """Run a command over SSH; return CompletedProcess or None on failure."""
    cmd = [
        "ssh", "-o", f"ConnectTimeout={timeout}",
        "-i", os.path.expanduser(SSH_KEY),
        SSH_HOST, command,
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def fetch_api_key(timeout: int = 20) -> str:
    """Fetch the bearer key from the homeserver over SSH."""
    result = run_ssh(f"cat {API_KEY_PATH}", timeout)
    if result is None or result.returncode != 0:
        sys.exit(
            f"[ERROR] Could not fetch API key from {SSH_HOST} over SSH "
            f"(returncode={result.returncode if result else 'timeout'}).\n"
            f"        Ensure the homeserver is reachable and ~/.ssh/home-server exists."
        )
    key = result.stdout.strip()
    if not key:
        sys.exit("[ERROR] Fetched an empty API key — check the homeserver path.")
    return key


def fetch_voices(key: str, timeout: int = 20) -> list[dict]:
    """Fetch the live voice inventory from /v1/voices."""
    import urllib.request

    url = f"{DEFAULT_BASE}/v1/voices"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {key}", "User-Agent": "kokoro-tts-production/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("voices", [])
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"[ERROR] Could not fetch voices from {url}: {exc}")


def validate_text(text: str) -> None:
    if not text or not text.strip():
        sys.exit("[ERROR] No input text. Pass a string argument or pipe via stdin.")


def split_segments(text: str, max_chars: int = 380) -> list[str]:
    """Split text at sentence boundaries, keeping segments <= max_chars."""
    import re

    sentences = [s.strip() for s in re.split(r"(?<=[.!?。！？])\s+", text) if s.strip()]
    segments: list[str] = []
    for sentence in sentences:
        if len(sentence) <= max_chars:
            segments.append(sentence)
        else:
            parts = re.split(r"(?<=[,;:])\s+", sentence)
            buf = ""
            for part in parts:
                if len(buf) + len(part) <= max_chars and buf:
                    buf += " " + part
                else:
                    segments.append(buf)
                    buf = part
            if buf:
                segments.append(buf)
    return [s for s in segments if s]


def synthesize_one(
    key: str, text: str, voice: str, speed: float | None, model: str
) -> tuple[int, bytes]:
    """Call the speech endpoint once; return (status_code, audio_bytes)."""
    import urllib.request

    url = f"{DEFAULT_BASE}/v1/audio/speech"
    payload: dict[str, object] = {"model": model, "input": text, "voice": voice}
    if speed is not None:
        payload["speed"] = round(float(speed), 3)

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "kokoro-tts-production/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"HTTP request to {url} failed: {exc}") from exc


def handle_error(status: int, body: bytes) -> None:
    """Print a helpful message for non-2xx responses and exit."""
    detail = ""
    try:
        parsed = json.loads(body.decode("utf-8"))
        detail = str(parsed.get("detail", "") or parsed)
    except Exception:  # noqa: BLE001
        detail = body.decode("utf-8", "replace")[:200]

    messages = {
        401: "unauthorized (invalid/missing API key)",
        422: f"invalid voice id — run --list-voices to pick a valid one",
        429: "rate limit exceeded (burst > 20) — wait and retry",
        500: "server error / model load failure — retry",
    }
    msg = messages.get(status, f"HTTP {status}") + (f": {detail}" if detail else "")
    sys.exit(f"[ERROR] HTTP {status} — {msg}")


def concat_with_ffmpeg(segments: list[bytes], out_path: str) -> None:
    """Concatenate WAV/MP3 segments into a single file via ffmpeg."""
    tmpdir = os.path.dirname(out_path) or "."
    list_file = os.path.join(tmpdir, f"._kokoro_segs_{os.getpid()}.txt")
    seg_paths: list[str] = []
    with open(list_file, "w", encoding="utf-8") as fh:
        for idx in range(len(segments)):
            seg = os.path.join(tmpdir, f"._seg_{os.getpid()}_{idx}.bin")
            with open(seg, "wb") as sf:
                sf.write(segments[idx])
            seg_paths.append(seg)
            fh.write(f"file '{seg}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
         "-c", "copy", out_path],
        check=False, capture_output=True, text=True,
    )
    for seg in seg_paths:
        os.remove(seg)
    os.remove(list_file)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synthesize speech from text using the live public Kokoro TTS API."
    )
    parser.add_argument("text", nargs="?", help="Text to synthesize (or use --stdin).")
    parser.add_argument("-o", "--output", help="Output file path.")
    parser.add_argument(
        "-v", "--voice", default=DEFAULT_VOICE, help="Voice ID (default: af_heart)."
    )
    parser.add_argument(
        "-s", "--speed", type=float, default=None, help="Speed 0.25–4.0 (default: API default)."
    )
    parser.add_argument(
        "-m", "--model", default="kokoro", help="Model: tts-1, tts-1-hd, or kokoro."
    )
    parser.add_argument(
        "-f", "--format", default="mp3", choices=["mp3", "wav"], help="Output format."
    )
    parser.add_argument(
        "-l", "--list-voices", action="store_true", help="List all voices and exit."
    )
    parser.add_argument(
        "--stdin", action="store_true", help="Read text from stdin."
    )
    parser.add_argument(
        "--ssh-timeout", type=int, default=20, help="SSH connect timeout (seconds)."
    )
    parser.add_argument(
        "--max-segment", type=int, default=380, help="Max chars per segment."
    )

    args = parser.parse_args()

    if args.list_voices:
        key = fetch_api_key(args.ssh_timeout)
        voices = fetch_voices(key, args.ssh_timeout)
        print(f"Total {len(voices)} voices:\n")
        for v in sorted(voices, key=lambda x: x["id"]):
            print(f"  {v['id']:<12} — {v.get('description', '')}")
        return

    text = args.text if args.text else ""
    if not text.strip() and args.stdin:
        text = sys.stdin.read()
    validate_text(text)

    key = fetch_api_key(args.ssh_timeout)

    # Sanity-check the voice against the live inventory.
    voices = fetch_voices(key, args.ssh_timeout)
    valid_ids = {v["id"] for v in voices}
    if args.voice not in valid_ids:
        sys.exit(
            f"[ERROR] Voice '{args.voice}' not found. Run --list-voices to pick a "
            f"valid one (e.g. {sorted(valid_ids)[:5]})."
        )

    ext = args.format  # 'mp3' or 'wav'
    segments = split_segments(text, args.max_segment)

    if len(segments) == 1:
        status, audio = synthesize_one(
            key, text, args.voice, args.speed, args.model
        )
        if status != 200:
            handle_error(status, audio)
        out_path = args.output or default_output(ext)
        with open(out_path, "wb") as fh:
            fh.write(audio)
        print(f"[OK] Wrote {len(audio)} bytes -> {out_path}")
        return

    # Multi-segment: synthesize each, then concatenate.
    print(f"[INFO] {len(segments)} segments — synthesizing and concatenating…")
    chunk_bytes: list[bytes] = []
    for i, seg in enumerate(segments):
        status, audio = synthesize_one(key, seg, args.voice, args.speed, args.model)
        if status != 200:
            handle_error(status, audio)
        chunk_bytes.append(audio)

    out_path = args.output or default_output(ext)
    if len(chunk_bytes) == 1:
        with open(out_path, "wb") as fh:
            fh.write(chunk_bytes[0])
    else:
        concat_with_ffmpeg(chunk_bytes, out_path)
    print(f"[OK] Wrote concatenated audio -> {out_path}")


def default_output(ext: str) -> str:
    """Create a timestamped output file in ~/voice-memos/."""
    out_dir = os.path.expanduser("~/voice-memos")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(out_dir, f"kokoro_{stamp}.{ext}")


if __name__ == "__main__":
    main()
