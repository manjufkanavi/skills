# Stage 4 — Audio design (Kokoro + music + loudness)

## Kokoro (local, ONNX — no API)
```python
from kokoro_onnx import Kokoro
k = Kokoro("<skill>/assets/kokoro/model.onnx", "<skill>/assets/kokoro/voices-v1.0.bin")
audio, sr = k.create(text, voice="af_bella", speed=1.0)   # -> (np.float32, 24000)
```
API facts (0.4.7):
- The method is `create()` — `generate()` does not exist.
- `voice` takes a name (`af_bella`, `am_adam`, … 46 voices) or an embedding.
- 510-phoneme context limit ≈ 400 chars/segment → produce.py splits lines >300
  chars at sentence boundaries automatically.
- ~2–6× realtime on Apple silicon. A 4-minute lesson ≈ 1–3 min of compute.

## Prosody rules (what make the voice not feel like a lullaby)
- Base rate: af_bella at speed 1.0 ≈ 2.4 words/s. Do not chase faster;
  learners need the 145 WPM comfort zone.
- **Emphasis** = `speed: 0.95` on that line + `pause_before_ms: 250`.
  Slow-down + breath is how TTS "leans in".
- **Pauses**: produce.py adds 150 ms around every line and 350 ms between
  lines within a scene, 600 ms between scenes. These gaps are the rhythm —
  the critic's pacing variance law applies to audio too.
- **Two voices**: main = af_bella (warm, explanatory); second = am_adam
  (neutral, "student/skeptic"). Voice switches are pattern interrupts: use for
  the quiz beat, the trap question, or a counterpoint. Never more than 2 voices.

## Music bed (generated, no license issues)
produce.py synthesizes a soft ambient pad: A2+E3+A3+D4 sines → lowpass 650 Hz
→ slow tremolo → −25 dB, then ducks under the voice via sidechaincompress
(threshold 0.02, ratio 8). Result: warmth without competing with narration.
- `music: false` in script.json (or `--no-music`) for clean lecture tracks.
- If a user supplies a licensed track, drop it in as `out/music_src.wav` and
  produce.py will use it instead (same gain chain).

## Loudness
Final mix: two-input amix → `loudnorm=I=-16:TP=-1.5:LRU=-13` (streaming
standard) → AAC 192 k. The critic measures integrated loudness and requires
−16 LUFS ±3.

## SRT
produce.py emits `out/subtitles.srt` from per-line audio offsets — cue text is
the narration line, timing is measured (not estimated). Coverage must reach ≥85%
of the video (critic-checked). This is the accessibility deliverable.

## Pitfalls
- Kokoro output is mono 24 kHz — upmix happens in amix, don't pre-process.
- Never `-c copy` audio between different sample rates; re-encode aac.
- If a line synthesizes to a silent wav (rare, happens on odd punctuation),
  produce.py pads it to 0.15 s so scene timing never breaks.
