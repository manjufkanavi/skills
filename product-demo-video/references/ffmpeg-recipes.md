# ffmpeg recipes used by product-demo-video

The scripts (`merge-scene.py`, `concat-final.py`, `render-card.py`) wrap these.
Keep the recipes in sync if you edit the scripts.

## Scene merge (webm + mp3 → mp4)

```
vdur = ffprobe -v error -show_entries format=duration -of csv=p=0 scene.webm
adur = ffprobe -v error -show_entries format=duration -of csv=p=0 scene.mp3
```

Video chain (always, for concat compatibility):
```
scale=W:H:force_original_aspect_ratio=decrease,
pad=W:H:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=FPS
```
Audio chain (always): `aformat=sample_rates=44100:channel_layouts=stereo`

Length rule — scene length = max(vdur, adur):
- `adur > vdur + 0.3` → append `tpad=stop_mode=clone:stop_duration={adur-vdur}` to the video chain (freeze last frame)
- `vdur > adur + 0.3` → append `apad,atrim=0:{vdur}` to the audio chain (silence tail)

Caption bar (optional, rendered by render-card.py, RGBA PNG, transparent above the bar):
```
ffmpeg -y -i scene.webm -i scene.mp3 -i cap.png \
  -filter_complex "[0:v]VCHAIN[v1];[v1][2:v]overlay=x=0:y=H-CAPH:enable='lt(t,DUR)'[vout];[1:a]ACHAIN[aout]" \
  -map "[vout]" -map "[aout]" -c:v libx264 -preset veryfast -crf 24 -pix_fmt yuv420p -r FPS \
  -c:a aac -b:a 128k -movflags +faststart scene.mp4
```
(Without caption: filter is `[0:v]VCHAIN[vout];[1:a]ACHAIN[aout]`.)

Notes:
- Playwright webms are VP8/VP9 in WebM with variable frame rate — the `fps` filter normalizes.
- `yuv420p` is required for Telegram/HTML5 inline playback.
- `+faststart` (moov atom up front) makes Telegram stream the video while uploading.

## Intro title card

```
render-card.py card --text "TITLE" --sub "subtitle" --w 1280 --h 720 --out intro-card.png
ffmpeg -y -loop 1 -i intro-card.png -f lavfi -i anullsrc=r=44100:cl=stereo -t 2.5 \
  -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 128k -movflags +faststart intro.mp4
```

## Concatenate

All inputs share the normalized encoding → stream copy:
```
printf "file '%s'\n" intro.mp4 scene_01.mp4 scene_02.mp4 > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy final.mp4
```
If `-c copy` fails ("non-monotonic DTS"/decoder errors), re-encode each clip first:
`ffmpeg -i clip.mp4 -c:v libx264 -crf 24 -pix_fmt yuv420p -r 30 -c:a aac -b:a 128k clip2.mp4`

## 50 MB size budget (Telegram bot upload limit)

UI screencasts at 720p compress well (≈0.5–1.5 MB/min with libx264 crf 24).
Ladder:
1. crf 24 (default)
2. crf 27, full res
3. 960x540, crf 27, audio 96k
Still over → split the video into parts in Telegram, or shorten the scenario.

## Audio specs

- Kokoro outputs 24 kHz mono; the `aformat` step up-mixes to 44.1 kHz stereo for AAC.
- MP3 (narration) → AAC 128 kbps in the merged scene.
