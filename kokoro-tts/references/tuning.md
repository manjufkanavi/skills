# Kokoro TTS — Tuning for Natural Speech

## The Problem

Raw Kokoro output at speed 1.0 with default text often sounds robotic, rushed, or unnatural. This guide covers how to fix it.

## Tuning Knobs

### 1. Speed (most impactful)

| Speed | Effect |
|-------|--------|
| `1.0` | Default — can sound rushed/robotic |
| `0.95` | Slightly slower — noticeable improvement |
| `0.90` | Natural pace — recommended default |
| `0.85` | Deliberate, clear — best for complex content |
| `0.80` | Very slow — may sound artificial |
| `0.70` | Too slow — robotic |

**Rule of thumb:** `0.85–0.95` is the sweet spot for human-like speech.

### 2. Voice Selection

Different voices have different naturalness profiles:

| Voice | Naturalness | Best For |
|-------|------------|----------|
| `af_heart` | High | Conversational, warm |
| `af_alloy` | High | Clear, articulate |
| `af_bella` | Medium | Default, general purpose |
| `af_aoede` | Medium | Expressive |
| `am_adam` | Medium | Authoritative |
| `am_michael` | Medium | Professional |
| `if_sara` | Medium | Indian English |
| `im_nicola` | Medium | Indian English |

### 3. Text Formatting (controls pauses)

Kokoro reads punctuation as pause cues:

| Punctuation | Pause Length | Use Case |
|-------------|-------------|----------|
| `,` (comma) | Short (~0.3s) | Natural breath points |
| `.` (period) | Medium (~0.5s) | End of sentence |
| `...` (ellipsis) | Long (~0.8s) | Dramatic pause, breath |
| `—` (em dash) | Medium (~0.5s) | Interruption, aside |
| `!` / `?` | Medium (~0.5s) | End of sentence |

**Example transformation:**

```
Before: "India is a land of incredible diversity. Did you know it has the world's highest post office."
After:  "India is a land of incredible diversity. Did you know... it has the world's highest post office, nestled in the Himalayas."
```

### 4. Custom Voice Style (advanced)

Blend voice embeddings for smoother tone:

```python
from kokoro_onnx import Kokoro
import numpy as np

k = Kokoro(model_path, voices_path)
voice_emb = k.voices["af_heart"]
style = voice_emb.mean(axis=0).astype(np.float32)  # (1, 256)
audio, sr = k.create(text, voice=style, speed=0.9)
```

This averages the voice embedding across time steps, reducing harshness.

### 5. Audio Post-Processing

After generation, use ffmpeg to enhance:

```bash
# Normalize volume
ffmpeg -i input.wav -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 24000 output.wav

# Add slight reverb for warmth
ffmpeg -i input.wav -af "aecho=0.1:0.9:1000:0.3" -ar 24000 output.wav

# High-pass filter to remove rumble
ffmpeg -i input.wav -af "highpass=f=80" -ar 24000 output.wav
```

## Quick Reference Card

```bash
# Human-like default
python3 tts.py "text" -v af_heart -s 0.9

# Indian accent, natural
python3 tts.py "text" -v im_nicola -s 0.85

# Clear, professional
python3 tts.py "text" -v am_adam -s 0.9

# Warm, conversational
python3 tts.py "text" -v af_heart -s 0.9

# Authoritative
python3 tts.py "text" -v am_michael -s 0.9
```

## Common Mistakes

1. **Speed 1.0** — sounds rushed. Always try 0.85–0.95 first.
2. **No punctuation** — Kokoro needs commas and periods for natural pauses.
3. **Long segments** — split at sentence boundaries (handled automatically by `--max-segment`).
4. **Wrong voice for accent** — use `if_sara`/`im_nicola` for Indian English, not US voices.
5. **Ignoring text formatting** — the text you feed Kokoro directly controls its prosody.

## See Also

- `references/quirks.md` — API gotchas, shape handling, ONNX types
- `voice-bridge/references/troubleshooting.md` — Error diagnostics