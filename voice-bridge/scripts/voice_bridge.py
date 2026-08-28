#!/usr/bin/env python3
"""
Voice Bridge: Speech-to-Speech pipeline for Hermes Agent.

Usage:
    python3 voice_bridge.py --input <audio_file> --voice <voice_name> --llm-prompt <text> [--max-seconds N]

Modes:
    --input FILE          Transcribe audio file, run LLM, return TTS audio
    --llm-prompt TEXT     Skip STT, use this text directly for LLM, return TTS audio
    --audio-input/llm-output  Combined: transcribe then respond via LLM + TTS

Output:
    Writes processed audio to --output <file> (default: stdout as wav)
    Writes transcript to --transcript <file> (if provided)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile

# === Configuration ===
SKILL_DIR = Path(__file__).parent.parent
ASSETS_DIR = SKILL_DIR / "assets"
KOKORO_MODEL = str(ASSETS_DIR / "kokoro" / "model.onnx")
VOICES_FILE = str(ASSETS_DIR / "voices-v1.0.bin")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3.6-35B-A3B-UD-MLX-4bit")
WHISPER_MODEL_PATH = os.getenv(
    "WHISPER_MODEL_PATH",
    str(Path.home() / ".lmstudio/models/mlx-community/whisper-large-v3-turbo"),
)
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "af_heart")
DEFAULT_SPEED = float(os.getenv("DEFAULT_SPEED", "1.0"))
SAMPLE_RATE = 24000  # Kokoro native sample rate
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful AI assistant communicating via voice. Keep your responses concise, natural, and conversational. Answer questions directly and engagingly.",
)

# === Whisper STT ===
def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio file using mlx-whisper."""
    try:
        import mlx_whisper
    except ImportError:
        return None, "mlx-whisper not installed"

    try:
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=WHISPER_MODEL_PATH,
            verbose=False,
            fp16=True,
        )
        transcript = result.get("text", "").strip()
        if not transcript:
            return None, "No speech detected in audio"
        return transcript, None
    except Exception as e:
        return None, f"Whisper transcription failed: {e}"


def convert_to_whisper_format(input_path: str, output_path: str) -> bool:
    """Convert any audio file to 16kHz mono WAV for whisper."""
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-ar", "16000",
                "-ac", "1",
                "-acodec", "pcm_s16le",
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return False
        return True
    except Exception as e:
        print(f"FFmpeg conversion error: {e}", file=sys.stderr)
        return False


# === Kokoro TTS ===
def text_to_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED,
) -> tuple[np.ndarray, int]:
    """Convert text to speech using Kokoro ONNX."""
    from kokoro_onnx import Kokoro, Tokenizer
    from kokoro_onnx.config import SAMPLE_RATE as KOKORO_SR

    # Load model (cached)
    if not hasattr(text_to_speech, "_kokoro"):
        k = Kokoro(KOKORO_MODEL, VOICES_FILE)
        t = Tokenizer(espeak_config=None)
        text_to_speech._kokoro = (k, t)
    else:
        k, t = text_to_speech._kokoro

    # Tokenize to phonemes
    phonemes = t.tokenize(text)
    tokens_arr = np.array([0, *phonemes, 0], dtype=np.int64)

    # Get voice embedding (mean across sequence dim)
    voice_emb = k.voices[voice]  # (510, 1, 256)
    style = voice_emb.mean(axis=0).astype(np.float32)  # (1, 256)

    # Build ONNX inputs
    inputs = {
        "input_ids": tokens_arr.reshape(1, -1),
        "style": style.reshape(1, -1),
        "speed": np.array([speed], dtype=np.float32),
    }

    # Generate
    audio = k.sess.run(None, inputs)[0]
    audio_flat = audio.flatten()  # (1, N) -> (N,)

    return audio_flat, KOKORO_SR


def save_audio(audio: np.ndarray, sample_rate: int, output_path: str, fmt: str = "wav") -> str:
    """Save audio to file, converting format if needed."""
    # Save as WAV first
    wav_path = output_path.rsplit(".", 1)[0] + ".wav"
    wavfile.write(wav_path, sample_rate, (audio * 32767).astype(np.int16))

    # Convert to desired format if needed
    if fmt == "oga" or fmt == "ogg":
        oga_path = output_path.rsplit(".", 1)[0] + ".oga"
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", wav_path,
                "-c:a", "libopus", "-b:a", "64k",
                "-application", "voip",
                oga_path,
            ],
            capture_output=True,
            timeout=30,
        )
        return oga_path
    elif fmt == "m4a":
        m4a_path = output_path.rsplit(".", 1)[0] + ".m4a"
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", wav_path,
                "-c:a", "aac", "-b:a", "96k",
                m4a_path,
            ],
            capture_output=True,
            timeout=30,
        )
        return m4a_path
    return wav_path


# === LLM API ===
def call_llm(text: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    """Call local LLM via Omlx-compatible API."""
    import httpx

    try:
        response = httpx.post(
            f"{LLM_BASE_URL}/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "max_tokens": 500,
                "temperature": 0.7,
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"I couldn't process that: {e}"


# === Main Pipeline ===
def run_pipeline(
    audio_input: str | None = None,
    text_input: str | None = None,
    output_path: str = "/tmp/voice_bridge_output.wav",
    transcript_path: str | None = None,
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED,
    system_prompt: str = SYSTEM_PROMPT,
) -> dict:
    """
    Full pipeline: STT → LLM → TTS.
    
    Args:
        audio_input: Path to audio file (m4a, ogg, wav, etc.)
        text_input: Direct text prompt (skip STT)
        output_path: Where to save the TTS output audio
        transcript_path: Where to save the STT transcript
        voice: Kokoro voice name
        speed: Speech speed multiplier
        system_prompt: LLM system prompt
    
    Returns:
        dict with keys: transcript, llm_response, output_path, duration_seconds
    """
    if audio_input and text_input:
        return {"error": "Provide either --input or --llm-prompt, not both"}

    # Step 1: Get text (from audio or direct)
    text = text_input
    transcript = None

    if audio_input:
        # Convert to 16kHz mono WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            whisper_input = tmp.name

        if not convert_to_whisper_format(audio_input, whisper_input):
            return {"error": f"Failed to convert audio: {audio_input}"}

        # Transcribe
        transcript, err = transcribe_audio(whisper_input)
        os.unlink(whisper_input)

        if err:
            return {"error": err}

        text = transcript

    # Step 2: Call LLM
    llm_response = call_llm(text, system_prompt)

    # Truncate LLM response to fit Kokoro's 510-phoneme limit
    # Rough estimate: ~2 phonemes per English character, so ~250 chars
    max_chars = 400
    if len(llm_response) > max_chars:
        # Find a good breaking point (end of sentence)
        truncated = llm_response[:max_chars].rsplit(' ', 1)[0]
        llm_response = truncated.rstrip('.') + '...'

    # Step 3: TTS
    try:
        audio, sr = text_to_speech(llm_response, voice, speed)
        duration = len(audio) / sr
    except Exception as e:
        return {"error": f"TTS failed: {e}"}

    # Step 4: Save output
    # Determine format from extension
    ext = output_path.rsplit(".", 1)[-1].lower() if "." in output_path else "wav"
    if ext not in ("wav", "oga", "ogg", "m4a"):
        ext = "wav"
    output_file = save_audio(audio, sr, output_path, fmt=ext)
    duration = len(audio) / sr

    if transcript_path:
        with open(transcript_path, "w") as f:
            f.write(transcript or text)

    return {
        "transcript": transcript or text,
        "llm_response": llm_response,
        "output_path": output_file,
        "duration_seconds": round(duration, 2),
        "voice": voice,
    }


# === CLI ===
def main():
    parser = argparse.ArgumentParser(description="Voice Bridge: STT → LLM → TTS pipeline")
    parser.add_argument("--input", help="Audio file to transcribe")
    parser.add_argument("--llm-prompt", help="Direct text prompt (skip STT)")
    parser.add_argument("--output", default="/tmp/voice_bridge_output.wav", help="Output audio path")
    parser.add_argument("--transcript", help="Save transcript to file")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Kokoro voice name")
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED, help="Speech speed")
    parser.add_argument("--system-prompt", default=None, help="LLM system prompt")
    parser.add_argument("--format", choices=["wav", "oga", "m4a"], default="wav", help="Output format")
    args = parser.parse_args()

    result = run_pipeline(
        audio_input=args.input,
        text_input=args.llm_prompt,
        output_path=args.output,
        transcript_path=args.transcript,
        voice=args.voice,
        speed=args.speed,
        system_prompt=args.system_prompt or SYSTEM_PROMPT,
    )

    if "error" in result:
        print(json.dumps({"status": "error", "message": result["error"]}), file=sys.stderr)
        sys.exit(1)

    print(json.dumps({"status": "success", **result}, indent=2))


if __name__ == "__main__":
    main()
