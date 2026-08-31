#!/usr/bin/env python3
"""Synthesize speech audio from any text via the live public Kokoro TTS API.

Endpoint: https://kokoro.iacgenie.com/v1/audio/speech (Cloudflare Tunnel ->
nginx :80 -> kokoro replicas). The API key is fetched over SSH from the
homeserver at call time — no secret is stored locally or in this repo.

Features:
  * Parallel synthesis across replicas (--parallel N, default 5) to use all
    available kokoro-* containers at once instead of one request at a time.
  * CPU + RAM monitoring during generation: a lightweight sampler runs on the
    homeserver and reports peak usage while audio is being synthesized.
  * Timing report: total wall-clock time plus per-request durations so you can
    see how much parallelism actually saved.

Example:
    python3 kokoro_tts.py "Hello world"                       # default af_heart, MP3
    python3 kokoro_tts.py "Buongiorno" -v im_nicola -s 0.85
    python3 kokoro_tts.py --list-voices
    python3 kokoro_tts.py "Long text…" --parallel 5            # use all replicas
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

DEFAULT_BASE = "https://kokoro.iacgenie.com"
SSH_HOST = "mkanavi@192.168.0.116"
SSH_KEY = "~/.ssh/home-server"
API_KEY_PATH = "/home/mkanavi/docker/kokoro/.api_key"

# Verified against the public API (see references/voices.md for full list).
DEFAULT_VOICE = "af_heart"


# --------------------------------------------------------------------------- #
# SSH helpers                                                                  #
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# CPU / RAM monitoring during generation                                       #
# --------------------------------------------------------------------------- #
def _make_sampler_script(sample_interval: float = 0.5, peak_file: str | None = None) -> str:
    """Return a shell script that samples peak CPU/RAM on the homeserver.

    Tracks a running max of host-wide CPU% and RAM used, writing that peak to
    `peak_file` on every tick. Because the max is monotonic, the file always
    holds the true peak even mid-run — no signal handling required. Reads CPU
    from /proc/stat and memory from `free -b` (robust across distros).

    The embedded Python string contains the unique marker "kokoro_tts_sampler"
    so it can be stopped precisely without touching unrelated processes.

    Writes JSON describing: {cpu_used, mem_total_bytes, mem_used_bytes}.
    """
    py = (
        "# kokoro_tts_sampler\n"
        "import time, json, subprocess\n"
        f"d={sample_interval}\n"
        "cpu=mem_used=mem_total=0\n"
        "while True:\n"
        "    try:\n"
        "        parts=open('/proc/stat').readline().split()[1:]\n"
        "        nums=[int(x) for x in parts]; idle=nums[3]\n"
        "        act=sum(nums[:3]); tot=idle+act\n"
        "        if tot: cpu=max(cpu, 100.0*act/tot)\n"
        "    except Exception: pass\n"
        "    try:\n"
        "        out=subprocess.check_output(['free','-b'],text=True,timeout=5).splitlines()\n"
        "        if len(out) > 1:\n"
        "            cols=out[1].split()\n"
        "            mt=int(cols[1]); mu=int(cols[2])\n"
        "            mem_total=mt\n"
        "            if mu > mem_used: mem_used=mu\n"
        "    except Exception: pass\n"
        f"    with open('{peak_file}', 'w') as fh:\n"
        "        json.dump({'cpu_used': cpu, 'mem_total_bytes': mem_total,\n"
        "                     'mem_used_bytes': mem_used}, fh)\n"
        "    time.sleep(d)\n"
    )
    return f'python3 -c "{py}" </dev/null >/dev/null 2>&1 &'


def _fmt_bytes(n: int) -> str:
    if n >= 1_073_741_824:
        return f"{n / 1073741824:.2f} GiB"
    if n >= 1_048_576:
        return f"{n / 1048576:.0f} MiB"
    return f"{n / 1024:.0f} KiB"


def start_cpu_ram_monitoring(timeout: int = 20) -> str | None:
    """Launch a background peak sampler on the homeserver.

    Returns the absolute path of the peak file, or None if launching failed
    (monitoring is best-effort and never aborts generation).
    """
    peak = "/tmp/kokoro_tts_peak.json"
    script = _make_sampler_script(peak_file=peak)
    proc = run_ssh(script, timeout)
    if proc is None or proc.returncode != 0:
        print("[INFO] Could not start CPU/RAM monitor — skipping (generation continues).",
              file=sys.stderr)
        return None
    # Give the background sampler a moment to start, then proceed.
    time.sleep(0.5)
    return peak


def report_cpu_ram_monitoring(peak: str | None, timeout: int = 20) -> None:
    """Print peak CPU/RAM if a sampler file exists; otherwise skip quietly."""
    if not peak:
        return

    # The sample file lives on the homeserver, so fetch its contents over SSH
    # *before* stopping things. Best-effort: never aborts generation if the
    # sample is missing or malformed partway through.
    out = run_ssh(f"cat {peak} 2>/dev/null", timeout)
    data: dict | None = None
    if out and out.returncode == 0 and out.stdout.strip():
        try:
            data = json.loads(out.stdout)
        except Exception:  # noqa: BLE001
            data = None

    run_ssh(f"pkill -f 'kokoro_tts_sampler' 2>/dev/null; rm -f {peak}", timeout)

    if not data:
        print("[INFO] CPU/RAM sample incomplete — no peak read.", file=sys.stderr)
        return

    cpu = data.get("cpu_used", 0.0)
    mem_total = int(data.get("mem_total_bytes", 0))
    mem_used = int(data.get("mem_used_bytes", 0))
    print(f"[MONITOR] Peak host CPU: {cpu:.1f}%  |  RAM used peak: "
          f"{_fmt_bytes(mem_used)} / {_fmt_bytes(mem_total)}")


# --------------------------------------------------------------------------- #
# Text helpers                                                                 #
# --------------------------------------------------------------------------- #
def validate_text(text: str) -> None:
    if not text or not text.strip():
        sys.exit("[ERROR] No input text. Pass a string argument or pipe via stdin.")


def split_segments(text: str, max_chars: int = 380) -> list[str]:
    """Split text at sentence boundaries, keeping segments <= max_chars."""
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


# --------------------------------------------------------------------------- #
# Synthesis                                                                    #
# --------------------------------------------------------------------------- #
def synthesize_one(
    key: str, text: str, voice: str, speed: float | None, model: str
) -> tuple[int, bytes, float]:
    """Call the speech endpoint once; return (status_code, audio_bytes, seconds)."""
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
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read(), round(time.time() - t0, 2)
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
    import subprocess

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


# --------------------------------------------------------------------------- #
# Output path                                                                  #
# --------------------------------------------------------------------------- #
def default_output(ext: str) -> str:
    """Create a timestamped output file in ~/voice-memos/."""
    out_dir = os.path.expanduser("~/voice-memos")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(out_dir, f"kokoro_{stamp}.{ext}")


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> None:
    import time

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
    parser.add_argument(
        "--parallel", type=int, default=5,
        help="Max parallel synthesis requests (matches kokoro replicas; default 5).",
    )
    parser.add_argument(
        "--monitor", action="store_true",
        help="Sample host CPU/RAM during generation (default: on when --parallel > 1).",
    )
    parser.add_argument(
        "--no-monitor", action="store_true",
        help="Disable CPU/RAM monitoring even when parallelizing.",
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

    # Decide whether to monitor CPU/RAM: on by default when parallelizing, or
    # whenever --monitor is passed explicitly. Disable with --no-monitor.
    should_monitor = args.parallel > 1 or (args.monitor and not args.no_monitor)

    peak_file = None
    if should_monitor:
        print("[INFO] Starting CPU/RAM monitor on homeserver…")
        peak_file = start_cpu_ram_monitoring(args.ssh_timeout)

    t_start = time.time()
    per_request: list[tuple[int, float]] = []

    out_path = args.output or default_output(ext)

    if len(segments) == 1:
        status, audio, dur = synthesize_one(
            key, text, args.voice, args.speed, args.model
        )
        if status != 200:
            handle_error(status, audio)
        per_request.append((1, dur))
    else:
        # Multi-segment: synthesize in parallel across replicas.
        print(f"[INFO] {len(segments)} segments — synthesizing with up to "
              f"{args.parallel} parallel requests…")
        chunk_bytes: list[bytes | None] = [None] * len(segments)
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futures = {
                ex.submit(synthesize_one, key, seg, args.voice, args.speed, args.model): i
                for i, seg in enumerate(segments)
            }
            done = 0
            for fut in as_completed(futures):
                i = futures[fut]
                status, audio, dur = fut.result()
                if status != 200:
                    handle_error(status, audio)
                chunk_bytes[i] = audio
                done += 1
                print(f"  [{done}/{len(segments)}] segment {i + 1} done ({dur}s)", flush=True)
                per_request.append((i + 1, dur))

        # handle_error() calls sys.exit(), so reaching here means all segments
        # succeeded. Concatenate them into the final file.
        concat_with_ffmpeg([c for c in chunk_bytes if c is not None], out_path)

    total_time = round(time.time() - t_start, 2)
    durations = [d for _, d in per_request]

    # Stop the monitor and report peak CPU/RAM (best-effort).
    if peak_file:
        print()
        report_cpu_ram_monitoring(peak_file, args.ssh_timeout)

    # Timing summary.
    out_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    print(f"[OK] Wrote {out_size} bytes -> {out_path}")
    if len(durations) == 1:
        print(f"[TIME] Total generation time: {total_time}s (1 request)")
    else:
        avg = sum(durations) / len(durations)
        print(f"[TIME] Total generation time: {total_time}s "
              f"({len(durations)} requests, parallel={args.parallel}, "
              f"per-request {min(durations):.2f}s–{max(durations):.2f}s, avg {avg:.2f}s)")


if __name__ == "__main__":
    main()
