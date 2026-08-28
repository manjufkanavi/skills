---
name: voice-bridge
description: "Voice-to-voice communication — send a voice note to Hermes, get back a voice response. Pipeline: Telegram audio → Whisper STT → Omlx LLM → Kokoro TTS → Telegram voice clip."
version: 1.0.0
author: Agent + Teknium
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [voice, tts, stt, speech, telegram, audio, kokoro, whisper]
---

# Voice Bridge Skill

Send voice notes from Telegram → get voice responses back. Fully local inference.

```
Telegram Voice → Whisper → Text → LLM → Text → Kokoro → Telegram Voice
```

## Quick Start

1. **Send a voice note** to Hermes in Telegram
2. Hermes auto-detects it's audio, runs the voice_bridge pipeline
3. You get back a **voice clip** (not text) as the response

## How It Works

When this skill is loaded and the user sends a voice note (audio file attachment), do this:

### Step 1: Download & Prepare Audio
1. Get the voice message file path from the Telegram message context
2. Convert to 16kHz mono WAV using ffmpeg:
   ```bash
   ffmpeg -y -i input.m4a -ar 16000 -ac 1 -acodec pcm_s16le /tmp/whisper_input.wav
   ```

### Step 2: Transcribe with Whisper
Run the voice_bridge script:
```bash
python3 ~/.hermes/skills/voice-bridge/scripts/voice_bridge.py \
  --input /path/to/audio.m4a \
  --output /tmp/voice_response.wav \
  --voice af_heart \
  --transcript /tmp/transcript.txt
```

### Step 3: Get LLM Response
The pipeline automatically calls your local LLM (Omlx on port 1234) and generates a TTS response.

### Step 4: Send Voice Response
Take the output audio file and send it back as a **voice message** on Telegram:
- Use `send_message` with `MEDIA:/tmp/voice_response.wav` or
- Save as .oga for better compression: `--format oga`

## Voice Options

Available Kokoro voices (from `~/.lmstudio/models/mlx-community/Kokoro-82M-bf16/VOICES.md`):

| Voice | Gender | Language |
|-------|--------|----------|
| `af_heart` | Female | English US |
| `af_bella` | Female | English US |
| `af_alloy` | Female | English US |
| `af_aoede` | Female | English US |
| `af_sarah` | Female | English US |
| `af_sky` | Female | English US |
| `am_adam` | Male | English US |
| `am_michael` | Male | English US |

**Default voice:** `af_heart`

## Kokoro Model Quirks

### Voice Embedding Shape

Kokoro voice embeddings from `voices-v1.0.bin` have shape `(510, 1, 256)` — 510 time steps.
The ONNX model expects `(1, 256)` for the `style` input. Always collapse with `mean(axis=0)`:

```python
voice_emb = k.voices[voice]  # (510, 1, 256)
style = voice_emb.mean(axis=0).astype(np.float32)  # (1, 256)
```

### ONNX vs Safetensors

The Kokoro model from LM Studio is safetensors (MLX format). **kokoro-onnx requires ONNX format**.
The ONNX model was downloaded from `onnx-community/Kokoro-82M-ONNX` on HuggingFace.
The safetensors model (`kokoro-v1_0.safetensors`) will NOT work with kokoro-onnx — it fails with a protobuf parsing error.

### Phoneme Limit

Kokoro has a 510-phoneme context length. LLM responses longer than ~400 chars will be truncated at sentence boundary. This is built into `voice_bridge.py`.

### ONNX Runtime Type Mismatch

The ONNX model expects `input_ids` as `int64` and `speed` as `float32`. The kokoro-onnx library auto-converts, but if writing custom inference, ensure explicit numpy types:

```python
inputs = {
    'input_ids': tokens.reshape(1, -1),        # np.int64
    'style': style.reshape(1, -1),              # np.float32
    'speed': np.array([speed], dtype=np.float32),
}
```

### Model Files Must Be Placed Permanently

Don't rely on `/tmp/` downloads. Copy model files to the skill's `assets/` directory:

```
assets/kokoro/model.onnx
assets/kokoro/tokenizer.json
assets/kokoro/tokenizer_config.json
assets/voices-v1.0.bin
```

## Configuration

Environment variables (optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://127.0.0.1:1234/v1` | Omlx API endpoint |
| `LLM_MODEL` | `Qwen3.6-35B-A3B-UD-MLX-4bit` | LLM model to use |
| `WHISPER_MODEL_PATH` | `~/.lmstudio/models/mlx-community/whisper-large-v3-turbo` | Whisper model |
| `DEFAULT_VOICE` | `af_heart` | Kokoro voice name |
| `DEFAULT_SPEED` | `1.0` | Speech speed (0.5-2.0) |
| `SYSTEM_PROMPT` | (built-in) | LLM system prompt |

## Supported Audio Formats

Telegram voice notes can arrive as:
- `.oga` (Opus) — most common
- `.m4a` (AAC) — some clients
- `.ogg` (Ogg Vorbis) — direct uploads
- `.wav`, `.mp3` — manual uploads

The pipeline auto-converts any format to 16kHz mono WAV for Whisper.

## Error Handling

If any step fails:
1. **STT fails** (silence, poor audio) → Respond with text explaining it didn't hear well
2. **LLM fails** → Respond with text explaining the service is unavailable
3. **TTS fails** → Respond with text

In all failure cases, **fallback to text response** — never leave the user with silence.

## Available Voices (Full List)

Run this to see all available voices:
```bash
python3 -c "
from kokoro_onnx import Kokoro
k = Kokoro(
    '$HOME/.hermes/skills/voice-bridge/assets/kokoro/model.onnx',
    '$HOME/.hermes/skills/voice-bridge/assets/voices-v1.0.bin'
)
for v in k.get_voices():
    print(v)
"
```

See also: `references/troubleshooting.md` for detailed error diagnostics and fix recipes.

## See Also

- **kokoro-tts** — Standalone text-to-speech: generate audio from any text with configurable voice, speed, and format
- **bytesized-learning** — Manim CE animations with Kokoro TTS narration
- **media** — General audio generation (MusicGen, AudioGen, SongSee spectrograms). Voice-bridge is specifically about conversational voice input/output, not music generation.
- **hermes-agent** → Voice & Transcription section — Hermes's built-in STT/TTS providers (faster-whisper, Edge TTS) for reference.

- `mlx-whisper` — `pip install mlx-whisper` (already installed)
- `kokoro-onnx` — `pip install kokoro-onnx` (already installed)
- `kokoro` — `pip install kokoro` (already installed)
- `scipy` — for audio I/O (already installed)
- `httpx` — for LLM API calls
- `ffmpeg` — for audio format conversion (already installed)
- `numpy` — (already installed)

## Dependencies

| Package | Installed? |
|---------|-----------|
| `mlx-whisper` | ✅ |
| `kokoro-onnx` | ✅ |
| `kokoro` | ✅ |
| `scipy` | ✅ |
| `numpy` | ✅ |
| `httpx` | Check |
| `ffmpeg` | ✅ (brew) |

## Troubleshooting

- **"Voice not found"**: Use an available voice from the list above. Run `k.get_voices()` to check.
- **"Model not found"**: Verify assets exist at `~/.hermes/skills/voice-bridge/assets/`
- **"MLX failed"**: Ensure Apple Silicon (M-series) chip or CPU fallback
- **Slow response**: First TTS call loads the model (~2s). Subsequent calls are faster.
- **Silent audio**: Check Kokoro model shape handling — audio output is `(1, N)`, must flatten
