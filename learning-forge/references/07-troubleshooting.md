# Troubleshooting

## Setup / environment
- **`manimpango` build failure** → use a python ≤3.12 venv (setup.sh picks
  python3.11). Manim's C deps do not build on 3.14.
- **Kokoro load error** → weights missing: `bash scripts/setup.sh` copies
  `assets/kokoro/*` from a local source or downloads voices from HF.
- **`kokoro_onnx` import error** → package name is `kokoro-onnx` (pip) /
  `kokoro_onnx` (import). On a machine without the skill .venv, produce.py
  falls back to system python3 if it has kokoro_onnx.
- **No LaTeX installed** → fine. Avoid MathTex; use Text. (If a topic truly
  needs equations: `brew install --cask mactex` once.)

## TTS
- **510-phoneme limit** → lines >~400 chars must be split (produce.py does this
  at 300 chars). If you write custom TTS, split at sentence boundaries first.
- **chipmunk voice** → that is `speed < 0.9`. Keep 0.95–1.05.
- **wrong voice embedding rank** → pass voice NAME strings, not embeddings,
  unless you know the (1,256) shape rule.
- **monotone** → add prosody (speed 0.95 + pause_before_ms 250 on emphasis
  lines) or a second voice. Flat 1.0 everywhere = the old boring pipeline.

## Manim
- **`Write() TypeError` on Text** → FadeIn. (See 04-visual gotchas.)
- **`NameError: CENTER`** → 0.22 removed it; use cardinal align_to.
- **scene renders but black** → background set in setup(), not construct().
- **text clips in boxes** → auto_card / scale_to_fit_width; boxes derive from
  text, never the reverse.
- **`-qh` too slow** → iterate at -ql; render -qm for delivery.

## ffmpeg
- **player freezes after scene 1** → you `-c copy`'d clips with mismatched
  SPS/PPS. Re-encode every concat (produce.py always does).
- **audio/video out of sync after padding** → use the push-in tail
  (produce.py); never mix `-shortest` with padded clips of different rates.
- **loudness spikes** → one-pass loudnorm can pump; if the critic's loudness
  check fails, re-run produce with `--no-music` and mix a flat pad at −28 dB.
- **403 from TinyFish** → rate limit: 60 s wait, one retry (research.py does
  this). Never parallelize.

## Critic failures (how to iterate)
- `hook_strength` FAIL → rewrite the hook from a DIFFERENT hook type (03-engagement).
- `pacing_variance` FAIL → change 2–3 duration_targets so no two adjacent match.
- `rehook_density` FAIL → add a question/twist line in the two longest scenes.
- `open_loops` FAIL → every opened loop needs a later scene that pays it off.
- `word_budget` FAIL → cut the longest lines first (they are usually the boring ones).
- `no_dead_zones` (media) FAIL → your Manim scene had a long wait; shorten
  self.wait() to ≤1.5 s or add a slow camera push (zoompan) in that window.
- Two consecutive FAIL rounds on the same check → relax deliberately: fix the
  two worst, document the rest in the run summary. Do not loop forever.

## Git / skills repo
The skills repo default branch is `main`. Push with `git push origin HEAD`
(NOT origin/master). Stage only the paths you changed — the working tree has
unrelated curator drift.
