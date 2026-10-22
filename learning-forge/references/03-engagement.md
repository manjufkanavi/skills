# Stage 3 — Engagement: the engine that kills boredom

## Format arcs (pick the template)
| format | duration | structure |
|---|---|---|
| `pulse` | 60 s | hook(8) → friction(14) → hero(26, opens loop) → payoff(10) → cta(3) — 5 scenes |
| `lesson` | 3–6 min | hook(10) → promise+map(15) → beat1(40) → beat2(45) → worked example(50) → trap/misconception(35) → quiz(15) → recap(25) → cta(5) — 9 scenes |
| `deep_dive` | 10–20 min | 3–4 chapters, each a lesson arc; two voices; ≥2 live demos |

The numbers are TARGETS. Asymmetry is the point: the critic requires
std(scene durations)/mean > 0.18 and forbids 3+ adjacent equal scenes.
Tune the arc to the content — a 12 s quiz is boring, a 20 s worked-example
reveal is not.

## The five hook types (write 3 candidates, pick 1)
1. **Dissonance** — "You've used @ for years. You've never actually seen what it does."
2. **Surprising result** — "Three lines of code just made my function 40× slower. Here's why."
3. **Open question / loop** — "What does @ do? The docs won't tell you, and it's not what you think."
4. **Failure story** — "Your code works in the tutorial. It breaks the moment you add this."
5. **Stakes / contrast** — "The difference between junior and senior Python is one symbol."

Hook rules: ≤2 sentences, ≤16 words, zero jargon (the topic's own technical
name is a jargon in the hook — use a concrete object or a behavior instead),
and it must VISUALLY do something in frame one (a symbol slamming in, a crash
burst, a door closing). The critic enforces ≤18 words + a curiosity marker.

## Re-hooks (a fresh micro-curiousity every 30–40 s)
A re-hook is any beat that re-opens curiosity mid-video: a question, "here's
the catch", a contrast, a number, a reversal, a "but". In `script.json`, re-hook
lines should contain one of: ? / but / twist / surprise / catch / wait / except /
however / here's / problem. The critic counts them (lessons: ≥3 total and ≥1 per
40 s of runtime — dense enough to re-engage, sparse enough not to whine).

## Open loops
Declare every loop you open in `script.json`:
```json
"open_loops": [
  {"promise": "the trap that breaks inspect()", "opened_in": 5, "closed_in": 7}
]
```
Critic rule: every opened loop must be closed in a LATER scene. A video that
opens 3 loops and closes 2 feels abandoned — that is exactly how learners tune out.

## Promise upfront
Scene 2 (lesson/deep_dive) states the outcome in doing-language and shows the
map: "Three ideas. The sugar. The wrapper. The trap." Chips appear as the
words land. This is the viewer's contract — break it and retention collapses.

## Dual coding (the line-level law)
Every line in script.json has a `visual` field describing what CHANGES on screen
while that line is spoken. Rules:
- a line whose visual is "diagram stays static" is a FAIL
- consecutive lines should not repeat the same visual action verbatim
- the aha line of each beat gets the boldest visual change (color flip,
  transform, stamp, count jump)

## Prosody (per line)
- default `speed: 1.0`; emphasis lines `0.95` + `pause_before_ms: 250`
- never 3 consecutive lines with similar word counts (the critic requires
  sentence-length CV ≥ 0.25)
- one second voice (e.g. am_adam) for at least one beat in lesson/deep_dive —
  a different voice IS a pattern interrupt; use it for the quiz or a skeptic beat

## The trap beats (your favorite tool)
The misconception/trap scene is where the video earns its "better than a
tutorial" reputation:
1. show the WRONG thing working (green, calm)
2. let it fail (red burst, the error card)
3. name the mechanism that caused it
4. fix it (green again) and say the lesson in one line

## Ending
Recap = the golden rule as 2–3 stacked cards, not a bullet list. CTA ≤5 s,
one action ("build your own @timed in the next exercise"). No "thanks for
watching, don't forget to like and subscribe" — that is retention suicide on a
learning platform.

## script.json shape (contracts/script.schema.json)
```json
{
  "topic": "...", "format": "lesson", "target_seconds": 240,
  "title_candidates": ["…", "…", "…"],
  "description": "one platform description sentence",
  "voice": {"main": "af_bella", "second": "am_adam"},
  "music": true,
  "open_loops": [{"promise": "...", "opened_in": 5, "closed_in": 7}],
  "scenes": [
    {"id": "Scene01_Hook", "role": "hook", "duration_target": 10, "voice": "main",
     "lines": [
       {"text": "You've used @ for years.", "speed": 1.0, "pause_before_ms": 0,
        "visual": "a big @ slams into center, dust burst", "claims": []},
       {"text": "You have never actually seen what it does.", "speed": 0.95,
        "pause_before_ms": 250, "visual": "the @ cracks open like an egg; glow spills out",
        "claims": ["cl3"]}
     ]}
  ]
}
```
Scene ids must be valid Python class names — they become the Manim classes.
