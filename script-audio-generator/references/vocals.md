# Script Audio Generator — Voice Casting & Mood→Speed Reference

Kokoro has **no pitch/tone controls** (only `voice` + `speed`). This table is how the skill
approximates "correct tone and pitch" for dialogue:

- **Tone** → chosen voice (gendered) + optional embedding-blend (harshness reducer).
- **Pitch** → not controllable; only expressible through gendered voice selection.

## Voice Selection by Gender (auto-detected)

Default voices are **Indian English** (`if_sara` female, `im_nicola` male) to match the user's
preferred accent. Override per character with `--cast`.

| Detected gender | Default voice | Alternatives (Indian) | Alternatives (US / other) |
|-----------------|---------------|------------------------|----------------------------|
| Male            | `im_nicola`   | `if_sarath`, `am_jacob`| `am_adam`, `am_michael`, `r_ali` |
| Female          | `if_sara`     | `af_lily`, `am_ruth`   | `af_heart`, `af_alloy`, `af_bella`, `am_ruth` |

Pick from the full voice list printed by:
```bash
python3 ~/.hermes/skills/kokoro-tts/scripts/tts.py --list-voices
```

## Mood → Speed (scene-level)

Kokoro reads `speed` as a tempo multiplier. Derived from each scene's detected emotion so pacing
tracks the drama (`0.82` slow/solemn … `1.15` frantic).

| Emotional target (from scene)        | Speed | Feel                                   |
|--------------------------------------|-------|----------------------------------------|
| serene, tranquil, calm, peaceful     | 0.85  | relaxed, contemplative                 |
| tender, loving, nostalgic            | 0.87  | soft, warm                             |
| melancholic, somber, tearful         | 0.82  | slow, heavy                            |
| hopeful, wistful, yearning           | 0.88  | gentle lift                            |
| neutral (default)                    | 0.9   | natural pace                           |
| joyful, celebratory, excited         | 0.98  | upbeat                                 |
| tense, anxious, suspenseful          | 1.05  | rushed, nervous                        |
| fear, dread, frightened              | 1.08  | jittery                                |
| anger, rage, aggressive, intense     | 1.12  | sharp, fast                            |
| panic, frantic                       | 1.15  | very fast                              |

If the scene emotion is unknown, fall back to `0.9`. Match this table's keys against
`cinematographer`'s scene `emotional_target` / mood strings.

## Tone via Embedding-Blend (optional)

From `kokoro-tts/references/tuning.md`: averaging a voice's embedding across time steps reduces
harshness. Toggle with `--blend` — the skill auto-enables it for intense/angry lines (which are
otherwise grating) and disables it for soft scenes where you want clarity.

```python
from kokoro_onnx import Kokoro
import numpy as np
k = Kokoro(model_path, voices_path)
style_emb = k.voices["af_heart"].mean(axis=0).astype(np.float32)  # (1, 256)
audio, sr = k.create(text, voice=style_emb, speed=0.9)   # softer tone
```

> **Quirk (from `kokoro-tts/references/quirks.md`):** voice lookup returns a numpy array whose
> truth value is ambiguous — always use `is None`, not `if voice_emb:`.

## Gender Detection Heuristics (offline)

1. **Pronoun tracking** — scan dialogue; if a character is referred to by `she/her` → female,
   `he/him` → male. Most reliable signal; accumulate votes per character.
2. **Name table** — fall back to a built-in first-name→gender lexicon for names not tracked via
   pronouns. Covers common Indian + Western English names (script is English).
3. **Ambiguous / unknown** — leave gender unset; the skill then picks a default voice and marks it
   `unknown` in the manifest for you to eyeball.
