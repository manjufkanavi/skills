---
name: kannada-tts
description: "Kannada Text-to-Speech using AI4Bharat Indic-TTS (FastPitch + HiFiGAN). Converts Kannada text to natural-sounding speech in WAV format."
version: 1.0.0
author: [manjufkanavi]
license: Apache-2.0
platforms: [macos, linux]
compatibility: "Requires Python 3.11+ with PyTorch and Coqui TTS (installed in skill venv). Model files are ~1.4 GB for Kannada."
prerequisites:
  commands: ["python3"]
  python_packages:
    - TTS
    - soundfile
    - numpy
    - scipy
    - torch
metadata:
  hermes:
    tags:
      - text-to-speech
      - tts
      - kannada
      - indic
      - ai4bharat
      - speech-synthesis
    category: speech
---

# Kannada TTS

Convert Kannada text to natural-sounding speech using **AI4Bharat Indic-TTS** (FastPitch + HiFiGAN).

## Overview

This skill wraps the AI4Bharat Indic-TTS model for Kannada language. It loads a pre-trained **FastPitch** (duration/pitch-controlled text-to-mel) and **HiFiGAN** (neural vocoder) to produce high-quality speech.

| Property | Value |
|----------|-------|
| Model | FastPitch + HiFiGAN (AI4Bharat) |
| Language | Kannada (kn) |
| Sample Rate | 22050 Hz |
| Output Format | WAV |
| Model Size | ~1.4 GB |

## Usage

### Script

```bash
# From the skill directory — female speaker (default)
.venv/bin/python3 scripts/synthesize.py --text "ನಿಮ್ಮ ಕನ್ನಡ ಪಠ್ಯ" --output output.wav

# Male speaker
.venv/bin/python3 scripts/synthesize.py --text "ನಿಮ್ಮ ಕನ್ನಡ ಪಠ್ಯ" --speaker male --output output.wav

# MPS (Apple Silicon GPU) acceleration
.venv/bin/python3 scripts/synthesize.py --text "ನಿಮ್ಮ ಕನ್ನಡ ಪಠ್ಯ" --speaker female --output output.wav --device mps

# From a text file
.venv/bin/python3 scripts/synthesize.py --text-file input.txt --output output.wav

# Send output to Telegram (example with user's chat ID)
.venv/bin/python3 scripts/synthesize.py --text "ನಿಮ್ಮ ಕನ್ನಡ ಪಠ್ಯ" --speaker female --output /tmp/tts_output.wav --device mps
# Then send via nanobot message tool: message(channel="telegram", chat_id="5349625423", media=["/tmp/tts_output.wav"])
```

### Parameters

| Argument | Description |
|----------|-------------|
| `--text` | Kannada text string to synthesize |
| `--text-file` | Path to a file containing Kannada text |
| `--speaker` | Speaker name: `female` or `male` (default: female) |
| `--output` | Output WAV file path (default: output.wav) |
| `--device` | Device: cpu, cuda, or mps (default: cpu) |

### Programmatic

```python
import os, sys
sys.path.insert(0, "scripts")
from synthesize import load_synthesizer, synthesize_text, save_wav

synth = load_synthesizer(device="cpu")
wav, sr = synthesize_text(synth, "ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಿ?")
save_wav(wav, "hello.wav", sr)
```

## How It Works

1. **Text Normalization** — The Coqui TTS pipeline normalises Kannada text (handles numerals, punctuation)
2. **FastPitch Inference** — Converts character sequence to mel spectrogram with duration and pitch prediction
3. **HiFiGAN Vocoder** — Converts mel spectrogram to raw waveform
4. **Output** — Saves as 22050 Hz mono WAV

## Model Details

The model was trained by AI4Bharat as part of the Indic-TTS project. It uses:
- **FastPitch**: A feed-forward Transformer that predicts mel spectrograms with explicit duration and pitch control
- **HiFiGAN**: A GAN-based neural vocoder for high-fidelity waveform generation
- **Speakers**: Dual speaker (female, male), Kannada language

## Files

```
skills/kannada-tts/
├── SKILL.md                    # This file
├── scripts/
│   └── synthesize.py           # Inference script
├── models/
│   └── kn/
│       ├── fastpitch/
│       │   ├── best_model.pth  # FastPitch weights
│       │   ├── config.json     # FastPitch config
│       │   └── speakers.pth    # Speaker embeddings
│       └── hifigan/
│           ├── best_model.pth  # HiFiGAN weights
│           └── config.json     # HiFiGAN config
└── .venv/                      # Python 3.11 virtual env (uv)
```

## Notes

- First run loads ~1.4 GB of model weights into memory (takes ~10–20s on CPU, a few seconds on MPS/GPU)
- The synthesizer internally handles sentence splitting for long texts
- Use `--device mps` on Apple Silicon for GPU acceleration (requires torch with MPS support) — ~0.6s for 10s of speech
- `Synthesizer.tts()` requires a valid `speaker_name` ("female"/"male"); default is "female"
- FastPitch model defines speakers: `{'female': 0, 'male': 1}`
