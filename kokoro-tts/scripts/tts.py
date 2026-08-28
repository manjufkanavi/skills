#!/usr/bin/env python3
"""Kokoro TTS — standalone text-to-speech.

Usage:
    python3 tts.py "Hello world" -o output.wav
    python3 tts.py "Hello" -v af_heart -s 1.2 -f mp3 -o output.mp3
    echo "Hello" | python3 tts.py -o output.wav
    python3 tts.py --list-voices
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SKILL_DIR = Path(__file__).resolve().parent.parent
VOICE_BRIDGE_ASSETS = Path.home() / ".hermes" / "skills" / "voice-bridge" / "assets"
MODEL_PATH = VOICE_BRIDGE_ASSETS / "kokoro" / "model.onnx"
VOICES_PATH = VOICE_BRIDGE_ASSETS / "voices-v1.0.bin"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def split_sentences(text: str, max_chars: int = 380) -> list[str]:
    """Split text into segments under max_chars, breaking at sentence boundaries."""
    # First split on sentence-ending punctuation
    raw_segments = re.split(r'(?<=[.!?])\s+', text.strip())
    segments: list[str] = []
    for seg in raw_segments:
        if len(seg) <= max_chars:
            segments.append(seg)
        else:
            # Hard split on whitespace for oversize segments
            words = seg.split()
            current: list[str] = []
            current_len = 0
            for w in words:
                if current_len + len(w) + 1 > max_chars and current:
                    segments.append(" ".join(current))
                    current = [w]
                    current_len = len(w)
                else:
                    current.append(w)
                    current_len += len(w) + 1
            if current:
                segments.append(" ".join(current))
    return segments


def list_voices() -> None:
    """Print available Kokoro voices."""
    if not MODEL_PATH.exists():
        print(f"Error: model not found at {MODEL_PATH}", file=sys.stderr)
        sys.exit(1)
    if not VOICES_PATH.exists():
        print(f"Error: voices file not found at {VOICES_PATH}", file=sys.stderr)
        sys.exit(1)

    try:
        from kokoro_onnx import Kokoro
    except ImportError:
        print("Error: kokoro-onnx not installed", file=sys.stderr)
        sys.exit(1)

    k = Kokoro(str(MODEL_PATH), str(VOICES_PATH))
    voices = k.get_voices()
    print("Available Kokoro voices:")
    for v in voices:
        print(f"  {v}")


def generate_audio(
    text: str,
    voice: str,
    speed: float,
    model_path: Path,
    voices_path: Path,
) -> tuple:
    """Generate audio from text using Kokoro. Returns (audio_array, sample_rate)."""
    try:
        import numpy as np
        from kokoro_onnx import Kokoro
    except ImportError:
        print("Error: kokoro-onnx not installed", file=sys.stderr)
        sys.exit(1)

    if not model_path.exists():
        print(f"Error: model not found at {model_path}", file=sys.stderr)
        sys.exit(1)
    if not voices_path.exists():
        print(f"Error: voices file not found at {voices_path}", file=sys.stderr)
        sys.exit(1)

    k = Kokoro(str(model_path), str(voices_path))

    # Validate voice
    available = k.get_voices()
    if voice not in available:
        print(f"Error: voice '{voice}' not found. Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    # Generate audio
    audio, sr = k.create(text, voice=voice, speed=speed)

    # Flatten output: (1, N) -> (N,)
    audio = audio.flatten()

    return audio, sr


def save_wav(audio, sr: int, path: Path) -> None:
    """Save audio array as WAV file."""
    try:
        from scipy.io import wavfile
    except ImportError:
        print("Error: scipy not installed", file=sys.stderr)
        sys.exit(1)

    wavfile.write(str(path), sr, audio.astype("float32"))


def concat_wav_files(file_list: list[str], output: Path) -> None:
    """Concatenate multiple WAV files using ffmpeg."""
    import subprocess

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for fpath in file_list:
            f.write(f"file '{fpath}'\n")
        concat_list = f.name

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", concat_list, "-c", "copy", str(output)],
            check=True,
            capture_output=True,
        )
    finally:
        os.unlink(concat_list)


def wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    """Convert WAV to MP3 using ffmpeg."""
    import subprocess

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path),
         "-codec:a", "libmp3lame", "-q:a", "2", str(mp3_path)],
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Kokoro TTS — generate speech from text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("text", nargs="?", help="Text to speak (or read from stdin)")
    parser.add_argument("-o", "--output", default="output.wav", help="Output file path (default: output.wav)")
    parser.add_argument("-v", "--voice", default="im_nicola", help="Kokoro voice name (default: im_nicola, male Indian)")
    parser.add_argument("-s", "--speed", type=float, default=0.85, help="Speech speed 0.4–2.0 (default: 0.85, natural pace)")
    parser.add_argument("-f", "--format", choices=["wav", "mp3"], default="wav", help="Output format (default: wav)")
    parser.add_argument("-l", "--list-voices", action="store_true", help="List available voices and exit")
    parser.add_argument("--max-segment", type=int, default=380, help="Max chars per segment (default: 380)")

    args = parser.parse_args()

    if args.list_voices:
        list_voices()
        return

    # Get text
    if args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("Error: no text provided (use argument or stdin)", file=sys.stderr)
        sys.exit(1)

    output = Path(args.output)
    if not output.suffix:
        output = output.with_suffix(".wav")

    # Split into segments
    segments = split_sentences(text, max_chars=args.max_segment)
    if not segments:
        print("Error: text is empty after splitting", file=sys.stderr)
        sys.exit(1)

    # Generate audio per segment
    temp_dir = Path(tempfile.mkdtemp(prefix="kokoro_tts_"))
    wav_files: list[str] = []

    for i, seg in enumerate(segments):
        seg_file = temp_dir / f"seg_{i:03d}.wav"
        print(f"[{i+1}/{len(segments)}] Generating: {seg[:60]}...", end=" ", flush=True)
        try:
            audio, sr = generate_audio(seg, args.voice, args.speed, MODEL_PATH, VOICES_PATH)
            save_wav(audio, sr, seg_file)
            wav_files.append(str(seg_file))
            print(f"✓ ({seg_file.stat().st_size} bytes)")
        except Exception as e:
            print(f"✗ {e}", file=sys.stderr)
            # Clean up temp files
            for f in wav_files:
                try:
                    os.unlink(f)
                except OSError:
                    pass
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            sys.exit(1)

    # Concatenate segments
    if len(wav_files) == 1:
        final_wav = temp_dir / "final.wav"
        import shutil
        shutil.copy(wav_files[0], str(final_wav))
    else:
        final_wav = temp_dir / "final.wav"
        concat_wav_files(wav_files, final_wav)

    # Convert to target format if needed
    if args.format == "mp3":
        final_mp3 = output.with_suffix(".mp3") if output.suffix == ".mp3" else output
        wav_to_mp3(final_wav, final_mp3)
        output = final_mp3
    else:
        import shutil
        shutil.copy(str(final_wav), str(output))

    # Cleanup
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    print(f"\nDone: {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
