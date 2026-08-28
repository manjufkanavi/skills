---
name: script-audio-generator
description: "Generates character dialogue audio from a movie/script — offline scene-break, speaker + gender detection, auto voice-casting to Kokoro voices per mood. Integrates with the generic cinematographer scene breakdown."
tags: [audio, tts, movie-script, dialogue, voice-casting, kokoro, offline]
---

# Script Audio Generator — Scene Dialogue → Character Voice Audio

Turn a movie/short-story script into per-character dialogue audio. Fully **offline**, English-only,
no LLM/LLM-CLI/network: scene-break → dialogue extraction → speaker + gender detection → auto
voice-casting per mood → Kokoro audio.

## When to use

Use for: movie scripts, story/dialogue text where multiple characters speak. Builds dialogue per
character and casts the right Kokoro voice (gendered) + mood-derived speed, then renders audio.

## Key constraints (read before touching code)

- **Kokoro has NO pitch/tone knobs** — only `voice` + `speed`. "Tone" = voice choice (plus optional
  embedding-blend, see references/vocals.md). "Pitch" is not controllable; it maps to gendered voice
  selection. Do NOT invent knobs that don't exist.
- **English only.** Kokoro is phoneme-based for English/Indian-English; pure non-Latin dialogue
  sounds poor. For Kannada/Hindi, use `kannada-tts` (AI4Bharat) instead — not this skill.
- **Offline.** Scene-break, dialogue extraction and gender detection are pure-Python heuristics.
  Do NOT add agy/LLM coupling here — it would break the offline contract.

## Pipeline (all local)

1. **Scene-break** — structural heuristics (sentence/paragraph breaks, transition connectors),
   language-agnostic. Reuses the same logic as `cinematographer` so scene boundaries line up with
   that skill's output.
2. **Dialogue extraction** — regex pull quoted speech and resolve each line to a speaker tag or
   nearest preceding name. Unattributed quotes become `unknown`.
3. **Character + gender detection** — collect proper-noun characters; infer male/female from
   pronouns and a small name table.
4. **Voice-casting** — each character → gendered Kokoro voice; scene `mood` → speed (see
   references/vocals.md). Both are auto-detected; override with `--cast`.
5. **Audio generation** — reuse `scripts/tts.py` from the `kokoro-tts` skill (segment → generate →
   concat). Per-scene audio + a `master` file.

## Quick Start

```bash
# From inline text (auto-detects speakers, casts voices per mood)
python3 ~/.hermes/skills/script-audio-generator/scripts/audio_gen.py --text \
  "\"Are you coming?\" Dev asked. She hesitated, then shook her head. \"I can't,\" she whispered."

# From a file
python3 ~/.hermes/skills/script-audio-generator/scripts/audio_gen.py --file script.txt

# Read a cinematographer scenes.json and generate audio for those exact scenes
python3 ~/.hermes/skills/script-audio-generator/scripts/audio_gen.py \
  --cinematographer prompts/<slug>/scenes.json

# Override casting: Dev→am_adam (US male), Priya→af_heart (female)
python3 ~/.hermes/skills/script-audio-generator/scripts/audio_gen.py --file script.txt \
  --cast "Dev:am_adam,Priya:af_heart"

# Output format / speed
python3 ~/.hermes/skills/script-audio-generator/scripts/audio_gen.py --file script.txt \
  -f mp3 --output-dir audio/
```

## Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--text` | — | Direct script text (mutually exclusive with --file / --cinematographer) |
| `--file` | — | Path to a .txt/.md script file |
| `--cinematographer` | — | Path to a `scenes.json` from the generic cinematographer skill (one scene per file) |
| `--cast` | auto-detect | Comma map of character→voice, e.g. `"Dev:am_adam,Priya:af_heart"` |
| `--style` | cinematic | Visual style hint passed through to cinematographer scenes.json (cinematic, anime, realistic, watercolor, painterly, theatrical, noir) |
| `--max-scenes` | 12 | Max scenes to process |
| `--output-dir` | prompts/ | Output directory (writes `<slug>/`) |
| `--format` | wav | Output format: `wav` or `mp3` (per-scene + master) |
| `--force` | False | Re-generate if output exists |

## Output Structure

```
<output-dir>/<slug>/
  scenes.json       # per-scene: dialogue, speaker, detected gender, cast voice, speed
  audio/scene_01.wav   # per-scene combined dialogue (wav or mp3)
  audio/master.wav    # full script audio concatenated across scenes
  manifest.md         # human-readable cast + dialogue summary
```

## Integration with the generic cinematographer skill

- **Input**: read `cinematographer`'s `<slug>/scenes.json`. Each scene already carries
  `characters`, `emotional_target`/mood, and a `text_segment`. This skill maps mood→speed and
  characters→voices directly from those fields. Scene boundaries therefore line up between the two
  skills — cinematographer produces visuals for a scene, this skill produces its dialogue audio.
- **Fallback**: if no scenes.json is given, break the script into scenes with the same structural
  heuristics (so counts match within ~1 scene).

## Limitations (honest)

- Dialogue extraction is heuristic. It handles quoted speech with a preceding speaker tag
  (`Dev:` / `"..." — Dev said`) and infers speakers from the nearest preceding capitalized name.
  Unattributed quotes → `unknown`; overlapping/unclear attribution may be misassigned. For ambiguous
  scripts, pass `--cast` to force voices and eyeball the manifest.
- Gender detection uses pronouns + a small name table — not exhaustive for invented names.

## See Also

- **cinematographer** — offline scene breakdown + 5s video prompts (visual counterpart).
- **kokoro-tts** — the TTS engine reused here (voice/speed, tuning).
- **kannada-tts** — use this for Kannada dialogue instead of Kokoro.
