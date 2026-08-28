# Visual Spot-Check for Kannada Reel Clips

After video generation, verify clips actually show the intended scenes **before** stitching. The video stage resumes (skips existing `clip_NN.mp4`), so stale clips from a prior topic can slip in silently.

## Extract a frame (fps-independent)
```bash
# Pull one frame at ~2s from a clip
ffmpeg -y -i clips/clip_01.mp4 -ss 2 -frames:v 1 clips/clip_01_frame.png
```

## Inspect it
`vision_analyze(image_url="...local path...")` often **fails to load a local file path** — nothing gets attached. Instead, deliver the frame as a photo in the chat and view it:
```
send_message(target='telegram:<chat>', message='clip_01 check', media=['~/.hermes/skills/kannada-reel/clips/clip_01_frame.png'])
```
Then inspect the attached photo.

## Validation checklist
- **Count:** 12 `clip_NN.mp4` files.
- **Duration:** each ~5s (`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 clips/clip_01.mp4`).
- **Dimensions:** vertical 832×480 (`ffprobe -v error -select_streams v:0 -show_entries stream=width,height clips/clip_01.mp4`).
- **Content:** matches the script line / cinematographer prompt for that clip.

## Fix off-topic / corrupt clips
```bash
rm clips/clip_03.mp4          # remove just the bad one (others resume)
# or clear all: rm clips/clip_*.mp4
python3 main.py --stage video --prompts-file <prompts> --output-dir clips/ --model 1.3b
```
Never ship clips whose prompts don't match the current topic.
