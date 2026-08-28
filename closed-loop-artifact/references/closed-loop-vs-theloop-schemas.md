# Schema Differences — closed-loop-artifact vs theloop

## The Problem

`closed-loop-artifact` and `theloop` use different spec formats. `closed-loop-artifact`'s spec format is **outdated** — the actual implementation lives in `theloop` with its own `judge_spec.json` schema.

## closed-loop-artifact spec (outdated, do not use)

```json
{
  "viewBox": "0 0 400 300",
  "threshold": 0.8,
  "criteria": [
    {"name": "3 bars increasing", "type": "bars_increasing"},
    {"name": "x-axis labels", "type": "text_in_region", "region": [160, 550, 620, 565], "min_dark_ratio": 0.02}
  ]
}
```

This format is referenced in the `closed-loop-artifact` SKILL.md but **does not work** with the actual judge scripts. The `verify_artifact.py` script this format targets does not exist.

## theloop judge_spec.json (current, use this)

```json
{
  "run_id": "my_run",
  "adapter": "svg",
  "max_iters": 5,
  "score_threshold": 0.75,
  "visual_judge": {
    "enabled": true,
    "fallback_to_ascii": false,
    "merge_strategy": "visual_authoritative",
    "svg_fix_format": "exact"
  },
  "criteria": [
    {
      "id": "bars",
      "description": "Bars visible and increasing",
      "look_for": "Dark rectangles getting taller left to right",
      "weight": 1.0,
      "visual_threshold": 0.80,
      "blocking": true
    }
  ]
}
```

## Mapping guide

| closed-loop-artifact field | theloop equivalent |
|---------------------------|-------------------|
| `threshold` | `score_threshold` |
| `criteria[].name` | `criteria[].id` |
| `criteria[].type` | (no equivalent — use `description` + `look_for`) |
| `criteria[].region` | (no equivalent — judge visually) |
| N/A | `criteria[].visual_threshold` |
| N/A | `criteria[].blocking` |
| N/A | `criteria[].weight` |

## Recommendation

When running the closed-loop loop, **always use the `theloop` judge_spec.json schema**. The `closed-loop-artifact` skill's spec examples are for documentation only.
