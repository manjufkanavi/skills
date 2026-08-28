# Adding Narration to FastMetal-QAD Video Clips

## Overview

FastMetal-QAD clips are video-only. To create a narrated video, concatenate clips then add narration audio via ffmpeg.

## Full Workflow

### Step 1: Generate Clips

```bash
# Generate clip 1
python3 scripts/generate_video.py --prompt "prompt 1" --model 5b --output-dir /tmp/clips --clip-index 1

# Generate clip 2
python3 scripts/generate_video.py --prompt "prompt 2" --model 5b --output-dir /tmp/clips --clip-index 2
```

### Step 2: Verify Clips Are Video-Only

```bash
ffprobe -v error -show_entries stream=codec_type -of csv=p=0 /tmp/clips/clip_01.mp4
# Output: video  (no 'audio' line)
```

### Step 3: Concatenate Video Clips

```bash
ffmpeg -y \
  -i clip_01.mp4 -i clip_02.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" \
  -t 10 \
  -c:v libx264 -preset fast -crf 18 \
  /tmp/concatenated.mp4
```

**Key flags:**
- `a=0` — no audio in concat (clips have none)
- `-t 10` — trim to desired total duration
- `-crf 18` — high quality encoding

### Step 4: Generate Narration Audio (Kokoro TTS)

```bash
python3 ~/.hermes/skills/kokoro-tts/scripts/tts.py \
  "Your narration text here." \
  -v af_heart -s 0.9 -f mp3 \
  -o /tmp/narration.mp3
```

### Step 5: Add Narration to Video

```bash
ffmpeg -y \
  -i /tmp/concatenated.mp4 \
  -i /tmp/narration.mp3 \
  -filter_complex "[1:a]atrim=0:10,asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[audio]" \
  -map 0:v \
  -map "[audio]" \
  -t 10 \
  -c:v copy \
  -c:a aac -b:a 128k \
  -shortest \
  /tmp/final.mp4
```

**Key flags:**
- `atrim=0:10` — trim audio to match video duration
- `aformat=...` — convert to stereo AAC (MP4 requirement)
- `-c:v copy` — no video re-encoding
- `-shortest` — stop at the shorter stream

### Step 6: Verify Final Output

```bash
ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=codec_type,codec_name,width,height \
  -of json /tmp/final.mp4
```

Expected: duration ~10s, video (h264) + audio (aac) streams.

## Common Pitfalls

| Mistake | Error | Fix |
|---------|-------|-----|
| `concat=n=2:v=1:a=1` | "Stream specifier ':a' matches no streams" | Use `a=0` |
| Simple `-af` + complex filter | "Simple and complex filtering cannot be used together" | Put all filters in `-filter_complex` |
| Mono MP3 audio in MP4 | Works but non-standard | Convert to stereo AAC via `aformat` |
| Audio longer than video | Audio plays past video end | Use `-t` on video + `atrim` on audio |

## Session Evidence (2026-08-25)

- Generated 2 clips of Mulla Nasruddin (5B model, ~90s each)
- Clips confirmed video-only via ffprobe
- First ffmpeg attempt failed: simple `-af` + complex filter conflict
- Second attempt failed: `a=1` in concat (no audio streams)
- Fixed: `a=0` concat + separate audio add with `atrim` + `aformat`
- Final output: 10s MP4, 832×448, 24fps, h264+aac, 2.1MB
