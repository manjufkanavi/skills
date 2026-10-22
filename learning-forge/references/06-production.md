# Stage 4/6 — Production mechanics (ffmpeg)

## The no-freeze law
Old pipelines padded short clips by FREEZING the last frame — the video literally
stops mid-explanation. That is the single most visible "AI video" tell.
produce.py instead extracts the last frame and applies a **slow push-in**
(`zoompan z='min(zoom+0.0012,1.18)'` over the deficit, capped at +18% zoom):
a deliberate Ken Burns beat, not a glitch.

## Render
- Iterate at `ql` (854×480@15) while writing scenes.
- `qm` (1280×720@30) is the default DELIVERY quality: ~1.5–2.5 Mbps after
  crf 18, fast to render, Telegram-friendly.
- `qh` (1920×1080@60) for platform masters: 30–120 s/scene, use for final.
- Output lands in `media/videos/<script-stem>/<qdir>/<SceneId>.mp4`.

## Stitch & mux (always re-encode; never `-c copy` across synthetic clips)
```
ffmpeg -f concat -safe 0 -i allc.txt -c:v libx264 -preset fast -crf 18
  -pix_fmt yuv420p -profile:v high -level 4.2 -movflags +faststart master.mp4
```
mismatched SPS/PPS between clips + `-c copy` = frozen player / broken scenes.

## Delivery size budget (Telegram bot upload cap ≈ 50 MB)
| quality | ~4 min | fits? |
|---|---|---|
| 720p30 crf18 | 35–55 MB | borderline |
| 720p30 crf23 | 18–30 MB | yes |
| 540p30 crf23 | 8–15 MB | always |
If `out/final.mp4` > 48 MB, re-encode a delivery copy:
```
ffmpeg -i out/final.mp4 -vf scale=960:540 -c:v libx264 -crf 23 -preset medium
  -c:a copy -movflags +faststart out/final_telegram.mp4
```
Send the delivery copy on Telegram; keep the master for the platform.

## Platform pack (scripts/pack.py)
- `chapters.json` — from scene offsets (role → human label; set
  `chapter_title` per scene in script.json for branded names).
- `metadata.json` — titles (from `title_candidates`), description, tags
  (from claims), objective, prerequisites, top-5 sources.
- `thumbnail.png` — frame at 45% into the hero scene (the aha moment).
- `quiz.json` — YOU author it (3+ MCQs, 4 options each, `answer` index,
  `explanation`, `claims` citing pedagogy ids). pack validates + copies to out/.

## Commit
After a green run: commit the project's small artifacts if the user wants them
tracked (quiz, metadata, chapters, srt, thumbnail) — NEVER `media/`, `work/`,
or the mp4 (they are gitignored by design).
