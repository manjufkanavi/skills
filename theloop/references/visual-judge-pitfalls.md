# Visual Judge Pitfalls — theloop

## stdin piping timeout

**Problem:** `echo '<json>' | python3 scripts/visual_judge.py ... --ingest` times out waiting for terminal consent/approval on the pipe.

**Workaround 1 — redirect from file:**
```bash
cat scores.json | python3 scripts/visual_judge.py img.png spec.json --ingest --iter 1 --out critique.json
```

**Workaround 2 — write critique.json directly:**
Skip the `--ingest` step entirely. Write the `critique.json` by hand with the structure from the SKILL.md. This is often faster than debugging pipe issues.

## judge_spec.json schema (theloop vs closed-loop-artifact)

| Field | `theloop` (judge_spec.json) | `closed-loop-artifact` (spec.json) |
|-------|----------------------------|-----------------------------------|
| Threshold key | `score_threshold` | `threshold` |
| Criterion ID | `id` | `name` |
| Criterion desc | `description` + `look_for` | `type` + `region` |
| Per-criterion threshold | `visual_threshold` | none (uses global) |
| Blocking | `blocking: bool` | none |
| Weight | `weight: float` | none |
| Judge script | `visual_judge.py` | `verify_artifact.py` (NOT available) |

**Use `judge_spec.json` for theloop.** The `closed-loop-artifact` skill's spec format is outdated for the actual implementation.

## svg_fixes validation

The `--ingest` step validates every `svg_fix` entry against the "exact" format. Vague fixes are rejected. Valid formats:
- Contains angle brackets: `<element attr='value'/>`
- Contains `attr="value"` pattern
- Contains known SVG attribute names (`stroke-width`, `fill`, `font-size`, etc.) with a value change

Example of valid fix: `"Change stroke-width from 2 to 5 on all <circle stroke='#FFD700'>"`
Example of invalid fix: `"Make the borders more visible"` — rejected, not exact enough.
