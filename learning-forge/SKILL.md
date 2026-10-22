---
name: learning-forge
description: "Use when building engaging learning videos for a learning platform (e.g. 'make a video about X', 'create a lesson on X', 'produce an explainer for the course'). Self-contained pipeline: web research → pedagogy design → engagement-driven script (hooks, re-hooks, open loops, prosody) → Manim render + Kokoro voice + music → engagement QC critic → platform pack (SRT, chapters, thumbnail, quiz, metadata). Three formats: 60s pulse, 3-6 min lesson, 10-20 min deep dive."
version: 1.0.0
platforms: [linux, macos, windows]
---

# Learning Forge

End-to-end production of **engaging** learning videos. Fully self-contained:
every script, template, contract, and asset this pipeline needs lives inside
this skill. It reuses NO other skill.

## When to use

- "Make a video / lesson / explainer about <topic>"
- "Create learning content for the platform on <topic>"
- "Turn this research into a video" (bring your own sources; start at stage 2)

## The Ten Engagement Laws (non-negotiable)

Videos fail when everything is uniform. Every run must satisfy:

1. **3-second law** — the first frame + first ≤16 words contain a pattern interrupt (surprise, contradiction, open question, stakes). No "Hello, today we'll learn about…", no logo cards, no title-then-intro.
2. **Asymmetric pacing** — scene lengths must vary (std/mean > 0.18). Never five equal 12s scenes. The hero scene is the longest.
3. **Re-hooks** — a fresh micro-curiousity (question, twist, "here's the catch", a number) every 15–25 s of runtime.
4. **Open loops** — open ≥1 in the first third, resolve ALL of them by the end. Track them explicitly in `script.json`.
5. **Promise upfront** — within the first 30 s, say what the viewer will be able to *do* at the end.
6. **Dual coding** — every narration line pairs with a visual ACTION. A static diagram under talking is a FAIL.
7. **Concrete over abstract** — numbers, names, real code, physical objects. No abstract-noun soup.
8. **Vocal variety** — vary sentence length (CV ≥ 0.25); emphasis lines slow to 0.95× with a 250 ms pre-pause; use the second voice for at least one beat in lesson/deep_dive.
9. **One idea per scene, one accent color per idea.**
10. **Payoff by the end** — close on the golden rule + a ≤5 s CTA.

Full rules, hooks taxonomy, and format arcs: `references/03-engagement.md`.

## Pipeline (six stages, run in order)

```
topic → 1 RESEARCH → 2 PEDAGOGY → 3 SCRIPT → 4 PRODUCE → 5 CRITIC → 6 PACK
        (research.py)  (you)      (you)      (produce.py) (critic.py, both phases) (pack.py)
```

All project work happens in `projects/<slug>/`. Never write into the skill root.

### Stage 0 — Setup (once)
```bash
bash scripts/setup.sh            # builds .venv (manim+kokoro-onnx), ensures Kokoro weights
```
Kokoro weights live in `assets/kokoro/` (gitignored). If absent, setup copies from
a local source or downloads them.

### Stage 1 — RESEARCH (scripts/research.py)
```bash
python3 scripts/research.py "decorators in python" --max-pages 25 \
  --out projects/decorators-python/research
```
Writes `research/pages.json` (authority-weighted, education-tuned queries,
serialized TinyFish calls). If no `TINYFISH_API_KEY`, do the research yourself
with web tools and write `pages.json` in the same shape.
Guide: `references/01-research.md`.

### Stage 2 — PEDAGOGY (you, the agent)
Read `references/02-pedagogy.md` + `research/pages.json`, then write
`projects/<slug>/pedagogy.json` (schema: `contracts/pedagogy.schema.json`):
objectives, prerequisites, ≥3 misconceptions (sourced), ≥2 analogies (each with
a `where_it_breaks`), ≥1 real worked example, claims with source ids.
Skip if the user supplied sources — fold them into `sources[]`.

### Stage 3 — SCRIPT (you, the agent)
Pick a **format** from `templates/` (arc-pulse / arc-lesson / arc-deep-dive) and
write `projects/<slug>/script.json` (schema: `contracts/script.schema.json`):
scenes with `duration_target` (asymmetric!), per-line `text`/`speed`/
`pause_before_ms`/`visual`/`claims`, `open_loops`, `voice` per scene,
`title_candidates`, `music: true`.
Then run the script critic:
```bash
python3 scripts/critic.py --project projects/<slug> --phase script
```
FAIL? Fix the script, re-run. (Max 2 iterations; then relax the weakest
constraint deliberately and note it.)

### Stage 4 — CODE + PRODUCE
Write `projects/<slug>/script.py` (Manim CE scenes; class names MUST equal
scene ids in script.json). Use `scripts/helpers/components.py` and the visual
rules in `references/04-visual.md`. No LaTeX/MathTex — Text-only is the norm.
Then:
```bash
python3 scripts/produce.py --project projects/<slug> --quality qm   # 720p30
# qh for 1080p60 delivery master, ql for fast drafts
```
produce.py: per-line Kokoro prosody → soft music bed (ducked) → Manim render →
**no-freeze alignment** (slow push-in, never a frozen frame) → stitch →
loudnorm −16 LUFS → `out/final.mp4` + `out/subtitles.srt` + `out/scene_offsets.json`.
Audio design details: `references/05-audio.md`. ffmpeg internals: `references/06-production.md`.

### Stage 5 — CRITIC (media) + Stage 6 — PACK
```bash
python3 scripts/critic.py --project projects/<slug> --phase media
python3 scripts/pack.py --project projects/<slug>
```
Also author `projects/<slug>/quiz.json` (3+ MCQs citing claim ids) before pack.
Pack writes `out/chapters.json`, `out/metadata.json`, `out/thumbnail.png` and
validates the quiz. **The `out/` folder is the deliverable.**

## Formats at a glance

| format | duration | scenes | word budget | use for |
|---|---|---|---|---|
| `pulse` | 60 s ±2 | 4–7 | ~140 | one idea, one aha |
| `lesson` | 3–6 min | 6–12 | ~2.4 wps | platform course units |
| `deep_dive` | 10–20 min | 10–22 | ~2.4 wps | flagship content, 2 voices |

## Self-containment

- `scripts/` — setup, research, produce, critic, pack, helpers (all internal)
- `assets/kokoro/` — Kokoro-82M ONNX + voices (copied in; gitignored)
- `references/` — research, pedagogy, engagement, visual, audio, production, troubleshooting
- `templates/` — the three format arcs
- `contracts/` — JSON schemas for pedagogy.json and script.json
- `projects/` — per-topic workspaces (gitignored; media is big)

Do NOT import from or reference any other skill. If a capability is missing,
add it here.

## References

| file | when to read |
|---|---|
| `references/01-research.md` | stage 1 (query design, authority, TinyFish pacing, fallback) |
| `references/02-pedagogy.md` | stage 2 (pedagogy.json construction rules) |
| `references/03-engagement.md` | stage 3 (hooks, re-hooks, open loops, pacing, arcs) |
| `references/04-visual.md` | stage 4 (Manim patterns, palettes, typography, 0.22 gotchas) |
| `references/05-audio.md` | stage 4 (Kokoro API, prosody, music, loudness, SRT) |
| `references/06-production.md` | stage 4/6 (ffmpeg, no-freeze, platform pack, delivery sizes) |
| `references/07-troubleshooting.md` | whenever anything breaks |
