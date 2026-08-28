---
name: kokoro-tts
description: "Standalone text-to-speech using Kokoro ONNX model. Generates audio from any text with configurable voice, speed, and output format."
version: 1.1.0
platforms: [linux, macos]
---

# Kokoro TTS Skill

Generate speech audio from text using the Kokoro ONNX model. Standalone — no video, no LLM, no STT.

## When to use

Use when users need: text-to-speech conversion, voice narration generation, audio file creation from text, or any scenario requiring local TTS output.

## Quick Start

```bash
# Basic usage (uses im_nicola at 0.85x speed)
python3 ~/.hermes/skills/kokoro-tts/scripts/tts.py "Hello world" -o output.wav

# Override voice and speed
python3 ~/.hermes/skills/kokoro-tts/scripts/tts.py "Hello" -v af_bella -s 1.0 -o output.wav

# MP3 output
python3 ~/.hermes/skills/kokoro-tts/scripts/tts.py "Hello" -f mp3 -o output.mp3

# From stdin
echo "Hello" | python3 ~/.hermes/skills/kokoro-tts/scripts/tts.py -o output.wav

# List available voices
python3 ~/.hermes/skills/kokoro-tts/scripts/tts.py --list-voices
```

## CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `text` | (stdin) | Text to speak (positional arg or stdin) |
| `-o` / `--output` | `output.wav` | Output file path |
| `-v` / `--voice` | `im_nicola` | Kokoro voice name (male Indian) |
| `-s` / `--speed` | `0.85` | Speech speed (0.4–2.0, natural pace) |
| `-f` / `--format` | `wav` | Output format (`wav` or `mp3`) |
| `-l` / `--list-voices` | — | List available voices and exit |
| `--max-segment` | `380` | Max chars per segment (safety margin) |

## Available Voices

| Voice | Gender | Language |
|-------|--------|----------|
| `im_nicola` | Male | Indian English |
| `af_heart` | Female | English US |
| `af_alloy` | Female | English US |
| `af_aoede` | Female | English US |
| `af_sarah` | Female | English US |
| `af_sky` | Female | English US |
| `am_adam` | Male | English US |
| `am_michael` | Male | English US |
| `if_sara` | Female | Indian English |
| `im_nicola` | Male | Indian English |
| `ff_siwis` | Female | German |
| `jf_gongitsune` | Female | Japanese |
| `jf_nezumi` | Female | Japanese |
| `jf_tebukuro` | Female | Japanese |
| `jm_kumo` | Male | Japanese |
| `zf_xiaoxiao` | Female | Chinese |
| `zf_xiaoyi` | Female | Chinese |
| `zm_yunxi` | Male | Chinese |
| ... and 30+ more | | |

**Default:** `im_nicola` (male Indian, natural pace)

## Tuning for Natural Speech

See `references/tuning.md` for full guide. Quick defaults:

| Goal | Voice | Speed | Text tip |
|------|-------|-------|----------|
| Natural, human-like | `af_heart`, `af_alloy` | `0.85–0.95` | Add commas, ellipses for pauses |
| Clear, articulate | `af_bella` | `0.9` | Short sentences, avoid run-ons |
| Indian accent | `if_sara`, `im_nicola` | `0.85` | Natural phrasing, avoid complex numbers |
| Warm, friendly | `af_heart` | `0.9` | Conversational tone |
| Authoritative | `am_adam`, `am_michael` | `0.9` | Confident pacing |

**Key insight:** Speed `0.85–0.95` consistently sounds more human than `1.0`. Text formatting (commas, ellipses, sentence breaks) directly controls Kokoro's pause behavior.

## How It Works

1. **Segment** — splits text at sentence boundaries, keeping each segment under `max_segment` chars
2. **Generate** — calls `k.create(text, voice=voice, speed=speed)` per segment
3. **Concat** — merges segments with ffmpeg
4. **Convert** — optionally converts WAV to MP3

## Model Files

Shared with `voice-bridge` skill:

| File | Path | Size |
|------|------|------|
| ONNX model | `~/.hermes/skills/voice-bridge/assets/kokoro/model.onnx` | ~325 MB |
| Voices | `~/.hermes/skills/voice-bridge/assets/voices-v1.0.bin` | ~28 MB |
| Tokenizer | `~/.hermes/skills/voice-bridge/assets/kokoro/tokenizer.json` | — |
| Tokenizer config | `~/.hermes/skills/voice-bridge/assets/kokoro/tokenizer_config.json` | — |

## Dependencies

| Package | Installed? |
|---------|-----------|
| `kokoro-onnx` | ✅ |
| `scipy` | ✅ |
| `numpy` | ✅ |
| `ffmpeg` | ✅ |

## Performance

- First call: ~2s (model load into memory)
- Subsequent calls: ~0.5–2s per segment (depends on text length)
- 510-phoneme context limit (~400 chars per segment)

## Error Handling

- Missing model/voices → prints error, exits non-zero
- Invalid voice → lists available voices, exits non-zero
- Missing package → prints install instructions, exits non-zero
- Empty text → prints usage hint, exits non-zero

## See Also

- **voice-bridge** — Voice-to-voice conversation pipeline (STT + TTS + LLM)
- **bytesized-learning** — Manim animations with Kokoro narration
- **infographic-show** — Infographic videos with Kokoro voiceover