---
name: theloop
description: Generate and refine an SVG or markdown artifact by running a single closed in-model loop — plan, write the artifact, render it, judge it against the spec (visual judge authoritative; ASCII as fallback), and iterate until all per-criterion visual thresholds and the global score threshold are met. Runs entirely in the executing model — no external model, no routing. Use when the user wants a self-correcting artifact (diagram, chart, scene) that improves over iterations with precise visual feedback.
category: design
---

# theloop — closed in-model loop

A single closed loop where the **executing model plays every role**: planner, writer, renderer, visual judge, and iterator. There is no sub-agent, no external model, no proxy.

> Repo-specific wrapper. The general class-level skill is `closed-loop-artifact` — use it directly for any artifact type; this `theloop` skill carries the exact adapters, scripts, and dual-judge layer. See `closed-loop-artifact/references/in-model-loop.md` for the base in-model run.

---

## The loop

1. **Parse the spec.** Load `judge_spec.json`: adapter, `max_iters`, global `score_threshold`, per-criterion `visual_threshold` values, and acceptance criteria. Default adapter: `svg`. `doc` skips rendering and visual judging.

2. **Plan.** Write one short plan: what the artifact must contain per criterion, which elements map to which criterion, and how you will judge it.

3. **Iterate** from iteration 1 to `max_iters`:

   **3-1. Read `critique.json` (iter ≥ 2).**
   At the top of every iteration after the first, read `critiqueN-1.json`:
   - Apply every `svg_fix` listed in `priority_fixes` for **failing** criteria only.
   - Follow `next_iter_directive` exactly — it names which elements to **not** change.
   - Do **not** rewrite passing elements; targeted fixes only.

   **3-2. Write the artifact.**
   Emit a single self-contained `<svg>` element (or markdown for `doc`). Do not shell out.

   **3-3. Render.**
   Rasterize to PNG via `cairosvg` (macOS: `DYLD_LIBRARY_PATH=/opt/homebrew/lib`). Save to `runs/<run_id>/iterNN.{svg,png}`.

   **3-4. Judge — visual judge (authoritative).**
   When vision is available:
   ```bash
   # Step A: emit inspection prompt
   python3 scripts/visual_judge.py runs/<id>/iterNN.png spec.json \
       --emit-prompt --iter N
   ```
   View the rendered PNG directly, then score every criterion. Pipe scores into Step B:
   ```bash
   # Step B: ingest scores → write critiqueNN.json
   echo '<scores_json>' | python3 scripts/visual_judge.py \
       runs/<id>/iterNN.png spec.json \
       --ingest --iter N --out runs/<id>/critiqueNN.json
   ```
   `final_score = visual_score` (authoritative). ASCII score stored as audit only.

   **3-4b. ASCII fallback (vision unavailable).**
   ```bash
   python3 scripts/ascii_view.py runs/<id>/iterNN.png [box x1,y1,x2,y2] [W H]
   ```
   Score each criterion from the luminance map, then ingest with `--ascii-fallback`:
   ```bash
   echo '<ascii_scores_json>' | python3 scripts/visual_judge.py \
       runs/<id>/iterNN.png spec.json \
       --ingest --ascii-fallback --iter N --out runs/<id>/critiqueNN.json
   ```
   `final_score = ascii_score`. `judge_mode = "ascii-fallback"`.

   **3-5. Check thresholds.**
   - `overall_score = average(final_score per criterion)`
   - Per-criterion gate: any `blocking` criterion with `final_score < visual_threshold` blocks delivery.
   - **Both** gates must pass simultaneously:
     - `overall_score ≥ score_threshold` **AND**
     - all blocking criteria `final_score ≥ visual_threshold`
   - → Pass: stop, deliver the best artifact.
   - → Fail: `critique.json` drives iter N+1.

4. **Deliver.** Output the best-scoring artifact (SVG source + PNG), final score, iteration count, and the last `critique.json`.

---

## Rules

1. **Single actor.** The executing model is the only actor — no sub-agent, external model, or proxy.
2. **Visual judge is authoritative.** `final_score = visual_score`. ASCII is fallback only.
3. **Spec-driven judging.** Score against acceptance criteria only — not taste or style.
4. **Exact svg_fixes.** Every `svg_fix` entry must include: element name + attribute + value. Vague instructions (e.g. "improve figure") are dropped with a warning by `visual_judge.py`.
5. **next_iter_directive names what NOT to change.** Passing criteria are explicitly listed to prevent regressions.
6. **Stop early.** As soon as ALL thresholds are met — do not burn the budget.
7. **Preserve best.** Track best-scoring artifact across iterations; deliver that, not the last.
8. **Targeted fixes.** Apply `svg_fixes` surgically; never rewrite the whole artifact when a small change will pass.

---

## Visual Thresholds

Each criterion in `judge_spec.json` carries its own `visual_threshold` and `blocking` flag.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `visual_threshold` | float 0–1 | `score_threshold` | Minimum `final_score` for this criterion |
| `blocking` | bool | `true` | If `true`, below-threshold blocks delivery |
| `weight` | float | `1.0` | Contribution to `weighted_score` |

```json
{
  "criteria": [
    { "id": "mandap",           "visual_threshold": 0.80, "blocking": true,  "weight": 1.0 },
    { "id": "bride_groom",      "visual_threshold": 0.85, "blocking": true,  "weight": 1.5 },
    { "id": "caption_text",     "visual_threshold": 0.70, "blocking": false, "weight": 0.5 }
  ]
}
```

`caption_text` above is **soft-fail**: it appears in `critique.json` with fixes but does not block delivery.

---

## `critique.json` — Inter-iteration contract

The visual judge writes `critiqueNN.json` after each iteration. The writer reads it at the top of iteration N+1.

```json
{
  "run_id": "indian_wedding",
  "iteration": 2,
  "judge_mode": "visual",
  "merge_strategy": "visual_authoritative",
  "svg_fix_format": "exact",
  "timestamp": "2026-08-22T17:14:00Z",
  "png_path": "runs/indian_wedding/iter02.png",

  "overall_score": 0.81,
  "weighted_score": 0.83,
  "global_threshold": 0.80,
  "global_threshold_met": true,
  "delivery_blocked_by": ["bride_groom"],
  "should_deliver": false,

  "criteria": [
    {
      "id": "bride_groom",
      "description": "Bride & groom in traditional Indian attire",
      "final_score": 0.72,
      "visual_score": 0.72,
      "ascii_score": null,
      "weight": 1.5,
      "visual_threshold": 0.85,
      "threshold_met": false,
      "blocking": true,
      "visual_observations": "Bride visible with red skirt. Groom has gold turban. Maang tikka too small to see. Bangles invisible at current stroke-width.",
      "svg_fixes": [
        "Add <circle cx='512' cy='320' r='6' fill='#FFD700'/> for maang tikka (current r=4 too small)",
        "Change stroke-width from 2 to 5 on all <circle stroke='#FFD700'> bangle elements",
        "Add <path d='M381,295 Q395,270 383,255' stroke='#FFD700' stroke-width='3' fill='none'/> for kalgi"
      ]
    },
    {
      "id": "mandap",
      "description": "Wedding mandap visible",
      "final_score": 0.88,
      "visual_score": 0.88,
      "ascii_score": null,
      "weight": 1.0,
      "visual_threshold": 0.80,
      "threshold_met": true,
      "blocking": true,
      "visual_observations": "Four gold pillars distinct. Canopy drape with red-gold gradient clear. String lights readable.",
      "svg_fixes": []
    }
  ],

  "priority_fixes": [
    "[bride_groom] Add <circle cx='512' cy='320' r='6' fill='#FFD700'/> for maang tikka",
    "[bride_groom] Change stroke-width 2 → 5 on all bangle <circle stroke='#FFD700'>",
    "[bride_groom] Add kalgi path <path d='M381,295 Q395,270 383,255' stroke='#FFD700' stroke-width='3'/>"
  ],

  "next_iter_directive": "CONTINUE — apply svg_fixes for: bride_groom. Do NOT change: mandap."
}
```

### Writer contract

At iteration N+1, before writing the SVG:
1. Read `next_iter_directive` — note which criteria to fix, which to leave alone.
2. For each criterion in `delivery_blocked_by`, apply every entry in its `svg_fixes` list verbatim.
3. Do not touch elements belonging to criteria **not** in `delivery_blocked_by`.

---

## Adapters

| Adapter | Artifact | Renders PNG | Visual judge |
|---------|----------|-------------|--------------|
| `svg` *(default)* | Single `<svg>` element | ✅ | ✅ (authoritative) |
| `web` | SVG + external CSS/JS | ✅ | ✅ (authoritative) |
| `doc` | Markdown document | ❌ | ❌ (text judging only) |

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/visual_judge.py` | Dual-judge core: `--emit-prompt` → inspection prompt; `--ingest` → `critique.json`; `--ascii-fallback` → ASCII mode |
| `scripts/judge_spec_template.json` | Spec template with per-criterion `visual_threshold`, `blocking`, `weight` |
| `scripts/ascii_view.py` | Luminance-map fallback: PNG → ASCII art for text-mode inspection |
| `scripts/svgwrite_adapter.py` | Structured intent JSON → exact SVG (no hand-coding) |
| `scripts/spec_to_svg.py` | Judge spec → structured intent → SVG |

---

## Pixel-perfect generation

Generate geometry **programmatically** via `svgwrite_adapter.py` (structured intent JSON → exact SVG). Trace rasters deterministically with Potrace. Clean with SVGO / svgcleaner / xmllint. See `references/pixel-perfect-svg.md`.

> **macOS/Apple Silicon:** export `DYLD_LIBRARY_PATH=/opt/homebrew/lib` before `cairosvg` or it fails silently. Venv: `~/.venvs/theloop` (Python 3.11). Install: `uv pip install --python ~/.venvs/theloop/bin/python3 cairosvg`.

> **Terminal stdin piping pitfall:** `echo '<json>' | python3 visual_judge.py ... --ingest` may timeout waiting for terminal consent on the pipe. Workaround: write scores to a temp file first, then use `python3 visual_judge.py ... --ingest < scores.json --out critique.json`, or write the `critique.json` directly by hand. See `references/visual-judge-pitfalls.md`.

> **ASCII dark-on-dark pitfall:** near-black elements on dark backgrounds collapse to the same luminance class → invisible to ASCII judge. Lighten fills or add a rim-light stroke so the element separates from the background.

---

## Example — dual-judge in-model run

**Spec:** *SVG bar chart, 3 increasing bars, labels X1/X2/X3, title "Monthly Sales"*  
`max_iters: 4`, `score_threshold: 0.80`  
Criteria: `bars` (`visual_threshold: 0.80`), `labels` (`visual_threshold: 0.80`), `title` (`visual_threshold: 0.80`)

```
Iter 1:
  Write SVG (forgot title).
  Render → iter01.png.
  Visual judge views PNG:
    bars=0.85 ✅, labels=0.82 ✅, title=0.0 ❌
  critique01.json:
    priority_fixes: ["[title] Add <text x='450' y='30' font-size='20'>Monthly Sales</text>"]
    next_iter_directive: "CONTINUE — fix: title. Do NOT change: bars, labels."
  overall=0.56 → below threshold → continue.

Iter 2:
  Read critique01.json. Apply title fix only.
  Render → iter02.png.
  Visual judge views PNG:
    bars=0.85 ✅, labels=0.83 ✅, title=0.88 ✅
  overall=0.85 ≥ 0.80, all visual_thresholds met → DELIVER.

Delivered: iter02.svg + iter02.png, score 0.85, 2 iterations used.
```
