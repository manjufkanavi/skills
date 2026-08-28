---
name: kannada-video-generator
description: End-to-end Kannada video generator — essay → TTS audio → cinematographic scenes → AI images → MP4 video with crossfade transitions and automatic duration enforcement.
tags: [kannada, video, essay, tts, cinematographer, image-generation, ffmpeg]
---

# Kannada Video Generator

Orchestrates the full video production pipeline from a single Kannada topic:

```
Topic → Essay (Gemini 3.1 Pro high-effort) → Prompt Evaluation → TTS Audio + Cinematographic Scenes → AI Images → MP4 Video
```

## Pipeline Steps

| Step | Skill Used | Output |
|------|-----------|--------|
| 1 | `kannada-essay` | 📄 Essay (Kannada markdown, ~2-3min read / ~100-120 words for 2-min mode) |
| 2 | `kannada-tts` | 🔊 Narration WAV audio |
| 3 | `kannada-cinematographer` OR **inline segmentation** | 🎬 Scene breakdown + image prompts (16-24 dynamic semantic segments in 2-min mode) |
| 3.5 | Evaluation | 🔍 Prompts checked against essay plot, auto-corrected |
| 4 | `comfyui` (mflux) | 🖼️ AI-generated images per segment |
| 5 | FFmpeg (xfade) | 🎥 Final MP4 video with 0.3s fast transitions |
| 6 | Duration check | ⏱ Rebuilds with shorter essay if > max-duration |

## Key Features (v3)

- **Gemini 3.1 Pro high-effort** for essay, cinematographer & segment prompts (<think> tags, deeper reasoning)
- **2-min dynamic-cut mode** — set `--max-duration 120` for a fast-paced video with 16-24 image cuts (~5-8s per cut), each synced to a sentence of narration
- **Inline essay segmentation** (2-min mode) — essay split into 16-24 semantically coherent segments via agy (LLM-based), each generating its own unique image prompt with varied camera angles, instead of broad cinematographer scenes
- **Normal-mode semantic segmentation** — essay split into 4-7 narrative units via agy (gemini-3.1-pro-high) with paragraph-level fallback, replacing the old 18-micro-cut approach and broad cinematographer scenes
- **Sentence-accurate image cuts** — each image plays for the exact per-segment audio duration, creating visual flow that matches the narration
- **3-minute essay default** (~500 words) for standard content
- **Prompt evaluation** stage verifies all image prompts against essay plot and auto-corrects mismatches
- **Image prompt enrichment** — each image prompt is enriched by merging visual description, setting, characters, and cinematography metadata from the scene breakdown for more specific, scene-accurate visuals
- **No text overlays by default** (use `--composite` to enable text overlays; raw AI-generated images are used cleanly by default)
- **Automatic duration limit** — if the assembled video exceeds `--max-duration`, the pipeline rebuilds with shorter content
- **Max 3 iterations** of the duration loop before giving up

## Usage

```bash
# Full pipeline: essay → TTS → scenes → images → video
python3 skills/kannada-video-generator/main.py \
  --topic "ಶಿಶುನಾಳ ಶರೀಫರ ತತ್ವಪದಗಳು" \
  --style philosophical --aspect 9:16 \
  --output output_video.mp4

# With text overlays (if you want the old behavior)
python3 skills/kannada-video-generator/main.py \
  --topic "ಪ್ರೀತಿ ಮತ್ತು ಆಧ್ಯಾತ್ಮಿಕತೆ" \
  --composite --theme sunset \
  --output reel.mp4

# 2-min dynamic-cut mode: 16-24 fast images, each synced to a sentence
python3 skills/kannada-video-generator/main.py \
  --topic "ಪ್ರೀತಿ ಮತ್ತು ಆಧ್ಯಾತ್ಮಿಕತೆ" \
  --style philosophical --aspect 9:16 \
  --max-duration 120 --output reel_2min.mp4

# Custom number of segments (override auto 18)
python3 skills/kannada-video-generator/main.py \
  --topic "ಪ್ರೀತಿ ಮತ್ತು ಆಧ್ಯಾತ್ಮಿಕತೆ" \
  --max-duration 120 --num-segments 12 \
  --output reel_12cut.mp4

# Skip essay generation (use existing essay file)
python3 skills/kannada-video-generator/main.py \
  --essay-file /path/to/essay.md \
  --aspect 16:9 --output video.mp4
```

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--topic` | Kannada topic for essay generation | — |
| `--essay-file` | Reuse existing essay file (skip step 1) | — |
| `--scenes-file` | Reuse existing prompts.md (skip steps 1,3) | — |
| `--audio-file` | Reuse existing TTS audio (skip steps 1,2) | — |
| `--images-dir` | Use existing images (skip steps 1,3,4) | — |
| `--style` | Essay style. Valid: philosophical, analytical, descriptive, narrative, reflective | `philosophical` |
| `--aspect` | Video aspect ratio: `16:9` or `9:16` | `9:16` |
| `--duration` | Min seconds per cut (ignored in 2-min mode where audio dictates timing) | `6.0` |
| `--num-segments` | Number of image cuts (0=auto: 18 for 2-min mode, 4 for normal) | `0` |
| `--transition` | Crossfade transition duration (auto-reduced to 0.3s in 2-min mode) | `1.0` |
| `--model` | agy model for essay + cinematographer + segmentation | `gemini-3.1-pro-high` |
| `--effort` | agy reasoning effort (low/medium/high) | `high` |
| `--max-duration` | Maximum video duration in seconds. Set to `120` for 2-min dynamic-cut mode | `300.0` (5 min) |
| `--composite` | Enable text overlays on images (default: off = raw AI images only) | False |
| `--theme` | Color theme for compositing (ocean/sunset/forest/purple/monochrome) | `purple` |
| `--output` | Output video path | `kannada_video.mp4` |
| `--work-dir` | Temp working directory (kept for debug) | auto-cleanup |

## Duration Enforcement Loop

```
1. Generate essay (~500 words normal / ~100-120 words for 2min mode)
2. TTS audio
3. Broad cinematographer scenes (normal) OR segment into 16-24 dynamic sentence-level cuts (2-min mode)
4. Evaluate prompts against essay → auto-correct
5. Generate images (equal to number of scenes/segments)
6. Assemble video with 0.3s xfade transitions
7. Check video duration
   ├── ≤ max-duration ✅ Done
   └── > max-duration 🔄 Reduce essay length, rebuild from step 1
       (Max 3 iterations)
```

## 2-Min Dynamic-Cut Mode

When `--max-duration 120` is set:

1. **Shorter essay**: ~100-120 words passed to kannada-essay (~2min TTS read)
2. **Skip broad cinematographer scenes**: Instead, essay is split into 16-24 **semantically coherent segments** via agy (LLM-based scene segmentation, each segment = one image cut)
3. **Per-segment prompts**: Each segment gets a unique Flux2 image prompt via agy (Gemini 3.1 Pro) — consecutive prompts enforce **different camera angles/shots** for dynamic editing
4. **Word-count proportional timing**: Each segment's screen time is proportional to its word count relative to the total — more content gets more screen time
5. **Fast transitions**: Crossfade reduced to **0.3s** for snappy cuts
6. **Dynamic cuts**: Images change every ~5-8 seconds, each synced to a specific sentence of narration

This produces a fast-paced video where each visual corresponds to a specific part of the essay, unlike the broad 3-5 scene approach of standard mode.

## TTS Text Preprocessing

The pipeline preprocesses Kannada text before TTS synthesis to handle model limitations:

- **Numerals** → Kannada words via `_kn_num_to_words()` (indic_numtowords + pure-Python fallback), preserving trailing Kannada suffixes with sandhi handling (e.g., 50ರಷ್ಟು → ಐವತ್ತರಷ್ಟು). Decimals are left as raw digits (indic_numtowords raises on non-integers).
- **ಕರ್ನಾಟಕ pronunciation**: FastPitch has no vocab entry for the ರ್ನ conjunct (ರ + ್ + ನ); it tokenizes ಕರ್ನಾಟಕ as ಕ-ರ-್-ನ-ಾ-ಟ-ಕ and mispronounces it. Fix: rewrite as **ಕರ್ ನಾಟಕಾ** (long final vowel, "karnatakaa") via regex in `kannada_tts_preprocess()` covering all inflected forms (ಕರ್ನಾಟಕದ, ಕರ್ನಾಟಕದಲ್ಲಿ → ಕರ್ ನಾಟಕದ, ಕರ್ ನಾಟಕದಲ್ಲಿ). A single regex `ಕರ್?್?ನಾಟಕ(ಾ)?` → `ಕರ್ ನಾಟಕಾ` + captured suffix prevents double-lengthening.
- **English acronyms** → kept and rendered letter-by-letter with spaces for emphasis (e.g., "ಹೆಚ್ ಐ ವಿ" not "HIV" as a word; VTU → ವಿ ಟಿ ಯು, QR → ಕ್ಯೂ ಆರ್)
- **% symbol** → replaced with ಶೇಕಡಾ
- **HIV handling**: `clean_essay_for_tts()` replaces both ZWNJ (ಹೆಚ್‌ಐವಿ) and full-stop (ಹೆಚ್.ಐ.ವಿ.) formats with space-separated letter-by-letter (ಹೆಚ್ ಐ ವಿ) for correct FastPitch pronunciation emphasis
- **Problematic words**: Avoid "ಸ್ವಾಗತ" (FastPitch mispronounces the ಸ್ವ conjunct); use "ನಮಸ್ಕಾರ" instead
- **Slang/loan words**: "ಡೇಟಿಂಗ್ ಆ್ಯಪ್" → "ಪರಿಚಯ ವೇದಿಕೆಗಳ" (social networking platforms) for correct pronunciation
- **`_kn_norm()`** normalizes nonstandard indic_numtowords compounds (ಇಪ್ಪತ್ತ್ಮೂರು→ಇಪ್ಪತ್ತಮೂರು, ನಲವತ್ನಾಲ್ಕು→ನಲವತ್ತನಾಲ್ಕು, ಆರುನೂರಾರು→ಆರುನೂರು ಆರು)
- **`optimize_tts_with_agy()`** (agy gemini-3.1-pro-high) runs BEFORE `kannada_tts_preprocess()` to rewrite Kannada text for FastPitch, handling numerals, acronyms, %, and problem words; its prompt documents the ಕರ್ನಾಟಕ rule as rule #6

## Word-Count Guidance

- Kannada FastPitch TTS speaks at **~1.15 words/sec** (not 2.1 as previously assumed)
- **2-min mode** (`--max-duration 120`): target **~100-120 words** so TTS stays under the 2-min limit
- **Normal mode**: ~500 words (~3-min read)
- In main.py: word_factor=1.0 (quick mode), rebuild floor=100 words, reduction factor floor=0.5

## Video Encoding

- **Codec**: H.265/HEVC for smaller file sizes
- **Preset**: `medium`
- **CRF**: `23` (good size/quality trade-off)

## Geographic Map Handling

Flux2 AI image generation cannot produce geographically accurate maps. Image prompts containing geographic map keywords are auto-detected and replaced with a broadcast studio variant (news anchor desk with map backdrop) instead.

## Scene Duration Computation

Scene durations are computed via word-count proportional distribution of the total TTS audio duration — segments with more words get proportionally more screen time, rather than equal division.

## Text-on-Image Fix (v2)

**Root cause identified:** The `composite_scenes()` function in v1 unconditionally added English titles, Kannada subtitles, kannada source text panels, and page numbers onto generated images — cluttering the visual output.

**Fix:** Compositing is now opt-in (`--composite` flag). Default behavior uses raw AI-generated images directly in the video, preserving the full visual quality of Flux-generated artwork. The old compositing behavior remains available via explicit `--composite` flag.

## Memory Considerations

- `kannada-essay` + `kannada-cinematographer` both use agy (no GPU)
- `kannada-tts` uses MPS GPU for fast inference (~0.6s for 10s audio)
- `comfyui` (mflux) loads Flux2-klein-9B (~16GB) — frees GPU memory after
- **Sequencing**: agy → TTS (MPS) → mflux (MLX) → FFmpeg. Natural order avoids GPU contention.
- **Stale process cleanup**: `generate_images()` kills stale mflux/MLX processes before each batch to prevent GPU race conditions.
- **Batch OOM limit**: Generating >15 images at 1088x1920 (9:16) on flux2-klein hits GPU OOM on 64GB M4; remaining images must be generated individually
- **Timeout fallback**: The duration rebuild loop runs inside a ~600s subprocess timeout. If the loop times out, the original video from the first run (before any rebuild) is retained at `--output` and can be delivered directly

## Known Issues

- **Visual asset cache bug (fixed)**: The `kannada-video-generator` previously reused stale images from prior runs instead of generating fresh ones per topic. Now `generate_images()` clears the images/ directory before each batch, preventing cross-topic asset leakage.
- **Kannada text rendering in compositing (fixed)**: `composite_scenes()` used Arial/Helvetica which has no Kannada glyphs, producing tofu boxes. Fixed by using NotoSansKannada.ttc for Kannada text compositing.
- **Scene key mismatch (fixed)**: `composite_scenes()` read narration from `scene["kannada_source"]` but scene segmentation produces `scene["kannada_text"]`; fallback between both keys was added.

## Dependencies

- All sub-skill dependencies (kannada-essay, kannada-tts, kannada-cinematographer, comfyui)
- `ffmpeg` (video encoding with xfade filter)
- `Pillow` / `PIL` (image compositing, optional)
- `soundfile` (audio duration check)
- `NotoSansKannada.ttc` (required for text compositing with `--composite` flag; searched in system font paths)
- Python 3 stdlib

## Workspace

**Skill directory:** `~/.nanobot/workspace/skills/kannada-video-generator/`
