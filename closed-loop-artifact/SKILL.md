---
name: closed-loop-artifact
description: Run a self-correcting closed loop to produce and refine an artifact (SVG, chart, diagram, or markdown doc) against an explicit spec — plan, write the artifact, render it, judge it against the acceptance criteria, and iterate until it passes a threshold. Runs entirely in the executing model — the same model plans, writes, renders, judges, and iterates. No pi coding agent, no LiteLLM/Ollama proxy, no external model, no routing. Use when the user wants a self-correcting, spec-driven graphic or document that improves over iterations and stops when it meets the spec.
category: creative
---

# closed-loop-artifact — self-correcting in-model loop

A single closed loop the **executing model performs itself**: plan → write the artifact → render it → judge it against the spec → iterate. Every role (planner, writer, judge) is the same model running this skill. There is no sub-agent, no external model, and no routing to any proxy. You do the looping.

This is the class-level skill. The repo-specific `theloop` skill wraps this same loop for the theloop package; use it when you want that package's exact adapters, otherwise use this one directly.

## The loop

1. **Parse the spec.** Read the adapter, the iteration budget (`max_iters`), the pass threshold (`score_threshold`), and the explicit acceptance criteria. Default adapter is `svg`; `doc` produces a markdown artifact and skips rendering.
2. **Plan.** Write one short plan: which artifact, what it must contain to satisfy each acceptance criterion, and how you will judge each one.
3. **Iterate** from iteration 1 to `max_iters`:
   1. **Write the artifact.** Author the artifact yourself. For `svg`/`web`, emit one self-contained `<svg>`. For `doc`, emit the markdown artifact. Do not shell out to an external coding agent.
   2. **Render it.** For `svg`/`web`, rasterize to a PNG (e.g. `cairosvg` or `rsvg-convert`) so you can judge it visually. Skip for `doc`. Save the artifact and its render under a per-run directory (`runs/<id>/`).
   3. **Judge it.** Score the artifact 0–1 against each acceptance criterion. Be strict; a `1.0` is rare.
   - For the `theloop` workflow: use `scripts/visual_judge.py` (dual-judge: visual authoritative + ASCII fallback). Write scores to a JSON file, then run `--ingest` to produce `critique.json`. See `references/theloop-vs-closed-loop.md` for schema differences.
   - For simple geometric checks: hand-score from the rendered PNG using vision.
   - `scripts/verify_artifact.py` is NOT available — do not attempt to run it. The visual judge is the authoritative scorer.
   4. **Decide.** If the overall score is at or above `score_threshold`, stop and deliver. Otherwise write a one-line critique (what is wrong) and continue.
4. **Deliver.** Output the best artifact (SVG source + rendered PNG for `svg`), the final score, the iteration count, and the per-criterion breakdown. Deliver the highest-scoring artifact, not the last.

## Rules

- The executing model is the only actor. It plans, writes, renders, judges, and iterates. No sub-agent, no external model, no proxy, no routing.
- Judge against the spec's acceptance criteria only, not against taste or style. State which criterion each score maps to.
- Stop as soon as one iteration meets the threshold. Do not burn the iteration budget when the artifact already passes.
- Preserve the best artifact across iterations. Deliver the highest-scoring one.
- Keep each iteration cheap: a short plan, a single artifact, one render, one score. Fix the specific gap rather than rewriting the whole artifact.

## Adapters

- `svg` (default): write one `<svg>`; render to PNG; judge the render.
- `web`: same as `svg`, but the artifact may reference external CSS/JS; still render to PNG for judging.
- `doc`: produce a markdown artifact; no rendering; judge the text directly.

## The judge script

`scripts/verify_artifact.py` is the deterministic judge. Run it each iteration to score the artifact from real pixels/text against the spec, so your own 0–1 scores are anchored to ground truth:

```bash
python scripts/verify_artifact.py runs/<id>/artifact.svg --spec runs/<id>/spec.json
```

`spec.json` (coordinates are in the SVG `viewBox`; the script scales them to pixels):

```json
{
  "viewBox": "0 0 400 300",
  "threshold": 0.8,
  "criteria": [
    {"name": "3 bars increasing", "type": "bars_increasing"},
    {"name": "x-axis labels", "type": "text_in_region", "region": [160, 550, 620, 565], "min_dark_ratio": 0.02},
    {"name": "title at top", "type": "text_in_region", "region": [0, 0, 400, 40], "min_dark_ratio": 0.002}
  ]
}
```

Criteria types: `bars_increasing` (dark bar heights strictly increasing left→right), `text_in_region` (dark-pixel ratio in a `region` [x0,y0,x1,y1] vs `min_dark_ratio`), `text_present` (substring in a `doc` artifact). Exit code is 0 when overall ≥ threshold, else 1; a JSON report prints to stdout.

> New deterministic criteria (`exact_rect`, `exact_circle`, `exact_color`, `text_ocr`, `proportion_ratio`, `overlap_free`, `grid_alignment`) — and their exact `spec.json` schema, plus the `_overlap_free` stale-global-binding fix — are documented in `references/judge-schema-and-overlap-free-fix.md`.

> **Important:** The `verify_artifact.py` script referenced in this skill does NOT exist. Use `visual_judge.py` from the `theloop` skill instead. Schema differences are documented in `references/closed-loop-vs-theloop-schemas.md`.

## Example (in-model)

Spec: *SVG bar chart, 3 increasing bars, x-labels X1/X2/X3, title "Monthly Sales"*, `max_iters: 4`, `score_threshold: 0.8`.

1. Plan: 3 increasing bars, axis labels, a title.
2. Iter 1: write the SVG (no title), render, score 0.67 (bars ✓, labels ✓, title missing). Critique: add the title.
3. Iter 2: write the SVG with the title, render, score 1.0. Meets threshold → stop.
4. Deliver: the SVG source + rendered PNG, score 1.0, one iteration used.

See `references/in-model-loop.md` for the exact run (scores, measured bar heights, the routing lesson) from the session that built this skill.