#!/usr/bin/env python3
"""visual_judge.py — Dual-judge visual feedback layer for theloop.

The visual judge is **authoritative**: when vision is available, final_score = visual_score.
ASCII is only used as a fallback when vision is unavailable (judge_mode = "ascii-fallback").

Two-step workflow
-----------------
Step A — emit inspection prompt (model reads this, then views the PNG):

    python3 scripts/visual_judge.py \\
        runs/<id>/iterNN.png spec.json --emit-prompt --iter N

Step B — ingest model scores (piped in as JSON) → write critiqueNN.json:

    echo '<scores_json>' | python3 scripts/visual_judge.py \\
        runs/<id>/iterNN.png spec.json \\
        --ingest --iter N --out runs/<id>/critiqueNN.json

    # ASCII-fallback (vision unavailable): pipe ascii scores instead
    echo '<ascii_scores_json>' | python3 scripts/visual_judge.py \\
        runs/<id>/iterNN.png spec.json \\
        --ingest --ascii-fallback --iter N --out runs/<id>/critiqueNN.json

Merge strategy: visual_authoritative
--------------------------------------
  final_score = visual_score          (when vision available)
  final_score = ascii_score           (when --ascii-fallback)

  ascii_score is stored in critique.json for audit but never overrides visual.

Threshold gating: strict block
--------------------------------
Delivery is blocked if ANY blocking criterion's final_score < visual_threshold,
regardless of whether the overall average passes. Set "blocking": false on a
criterion for soft-fail (flagged but does not block delivery).

svg_fixes format: exact
------------------------
svg_fixes entries must be concrete SVG edits including element name, attribute,
and value. Vague instructions are rejected. Example of valid fix:
  "Add <circle cx='512' cy='320' r='6' fill='#FFD700'/> for bride maang tikka"
  "Increase bangle stroke-width from 2 to 5 on all <circle stroke='#FFD700'>"

Spec schema (judge_spec_template.json)
--------------------------------------
{
  "run_id": str,
  "adapter": "svg" | "web" | "doc",
  "max_iters": int,
  "score_threshold": float,
  "visual_judge": {
    "enabled": bool,
    "fallback_to_ascii": bool,
    "merge_strategy": "visual_authoritative",
    "svg_fix_format": "exact"
  },
  "criteria": [
    {
      "id": str,
      "description": str,
      "look_for": str,
      "weight": float,
      "visual_threshold": float,
      "blocking": bool
    }
  ]
}

Critique response JSON (model pipes during --ingest, visual mode)
-----------------------------------------------------------------
{
  "criteria": [
    {
      "id": str,
      "visual_score": float,           # 0.0–1.0; be strict, 1.0 is rare
      "visual_observations": str,      # one sentence: what you see for this criterion
      "svg_fixes": [str]               # exact SVG edits; [] if threshold already met
    }
  ]
}

Critique response JSON (ascii-fallback mode)
--------------------------------------------
{
  "criteria": [
    {
      "id": str,
      "ascii_score": float,
      "ascii_observations": str,
      "svg_fixes": [str]
    }
  ]
}
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _weighted_avg(criteria_results: list[dict]) -> float:
    total_weight = sum(c.get("weight", 1.0) for c in criteria_results)
    if total_weight == 0:
        return 0.0
    return sum(
        c.get("final_score", 0.0) * c.get("weight", 1.0)
        for c in criteria_results
    ) / total_weight


def _overall_avg(criteria_results: list[dict]) -> float:
    if not criteria_results:
        return 0.0
    return sum(c.get("final_score", 0.0) for c in criteria_results) / len(criteria_results)


def _validate_svg_fix(fix: str) -> bool:
    """
    Validate that a fix string is an 'exact' SVG edit.
    Requires at least one of:
      - angle brackets: <element ... /> or </element>
      - attribute=value syntax: attr="value" or attr='value' or attr=value
      - explicit SVG attribute name followed by a value change description
    Rejects bare natural-language phrases that happen to contain SVG words
    (e.g. "make text bigger" triggers on "text" substring — rejected).
    """
    import re
    if not fix or not fix.strip():
        return False
    # Angle bracket → clearly an SVG element/tag edit
    if "<" in fix and ">" in fix:
        return True
    # attr="value" or attr='value' pattern
    if re.search(r'\w[\w-]+=[\"\'\w#\.\-]', fix):
        return True
    # "Change X from A to B" pattern referencing a known SVG attribute name
    svg_attrs = (
        "stroke-width", "stroke", "fill", "font-size", "opacity",
        "r=", "cx=", "cy=", "rx=", "ry=", "x=", "y=", "d=",
        "width=", "height=", "transform=", "viewBox",
    )
    if any(a in fix for a in svg_attrs):
        return True
    return False



# ---------------------------------------------------------------------------
# Step A — emit inspection prompt
# ---------------------------------------------------------------------------

def emit_prompt(png_path: str, spec: dict, iteration: int) -> None:
    """Print the structured inspection prompt the model reads before viewing the PNG."""
    run_id = spec.get("run_id", "unknown")
    criteria = spec.get("criteria", [])
    threshold = spec.get("score_threshold", 0.80)
    svg_fix_format = spec.get("visual_judge", {}).get("svg_fix_format", "exact")

    lines = [
        f"{'=' * 72}",
        f"  VISUAL JUDGE — {run_id}  |  Iteration {iteration}",
        f"{'=' * 72}",
        f"  Image    : {png_path}",
        f"  Adapter  : {spec.get('adapter', 'svg')}",
        f"  Global threshold : {threshold}",
        f"  svg_fix format   : {svg_fix_format} (include element name + attribute + value)",
        "",
        "  ► VIEW THE IMAGE NOW, then score every criterion below.",
        "  ► Reply with the JSON schema shown at the bottom.",
        f"{'─' * 72}",
    ]

    for c in criteria:
        vt = c.get("visual_threshold", threshold)
        blocking = c.get("blocking", True)
        block_label = "BLOCKING" if blocking else "soft-fail"
        lines += [
            "",
            f"  CRITERION  [{c['id']}]",
            f"    visual_threshold : {vt}  ({block_label})",
            f"    Description      : {c.get('description', '')}",
            f"    Look for         : {c.get('look_for', 'See description')}",
            "",
            f"    → visual_score        : ?  (0.0 – 1.0; strict, 1.0 is rare)",
            f"    → visual_observations : ?  (one sentence: exactly what you see for this criterion)",
            f"    → svg_fixes           : []  (exact SVG edits if score < {vt}; empty list if passing)",
            f"      Format: \"<element attr='value'/> description\"  OR  \"Change <attr> from X to Y on <element>\"",
        ]

    lines += [
        "",
        f"{'─' * 72}",
        "",
        "  Reply with this JSON (replace all ? values):",
        "",
        json.dumps({
            "criteria": [
                {
                    "id": c["id"],
                    "visual_score": "?",
                    "visual_observations": "?",
                    "svg_fixes": ["<exact SVG edit> if below threshold, else remove this entry"]
                }
                for c in criteria
            ]
        }, indent=4),
        f"{'=' * 72}",
    ]

    print("\n".join(lines))


# ---------------------------------------------------------------------------
# Step B — ingest model response → critique.json
# ---------------------------------------------------------------------------

def ingest(
    png_path: str,
    spec: dict,
    response_json: str,
    iteration: int,
    ascii_fallback: bool,
    out_path: str,
) -> dict:
    """
    Ingest visual (or ascii-fallback) scores → compute thresholds → write critique.json.

    Merge strategy: visual_authoritative
      final_score = visual_score  (or ascii_score when ascii_fallback=True)
    """
    run_id = spec.get("run_id", "unknown")
    global_threshold = spec.get("score_threshold", 0.80)
    svg_fix_format = spec.get("visual_judge", {}).get("svg_fix_format", "exact")
    spec_criteria = {c["id"]: c for c in spec.get("criteria", [])}

    # Parse model response
    try:
        response = json.loads(response_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: could not parse model response JSON: {e}", file=sys.stderr)
        sys.exit(1)

    judge_mode = "ascii-fallback" if ascii_fallback else "visual"

    # Build per-criterion results
    criteria_results = []
    failed_criteria = []
    all_priority_fixes: list[str] = []
    fix_warnings: list[str] = []

    for item in response.get("criteria", []):
        cid = item.get("id", "")
        spec_c = spec_criteria.get(cid, {})

        if ascii_fallback:
            score = float(item.get("ascii_score", 0.0))
            observations_key = "ascii_observations"
            score_key = "ascii_score"
        else:
            score = float(item.get("visual_score", 0.0))
            observations_key = "visual_observations"
            score_key = "visual_score"

        # final_score = the authoritative score (visual or ascii, no merging)
        final_score = score

        visual_threshold = spec_c.get("visual_threshold", global_threshold)
        weight = spec_c.get("weight", 1.0)
        blocking = spec_c.get("blocking", True)
        threshold_met = final_score >= visual_threshold

        # Validate svg_fixes if format is "exact"
        raw_fixes = item.get("svg_fixes", [])
        validated_fixes = []
        for fix in raw_fixes:
            if svg_fix_format == "exact" and not _validate_svg_fix(fix):
                fix_warnings.append(
                    f"[{cid}] svg_fix rejected (not exact enough): {fix!r}"
                )
            else:
                validated_fixes.append(fix)

        if validated_fixes and not threshold_met:
            for fix in validated_fixes:
                all_priority_fixes.append(f"[{cid}] {fix}")

        if not threshold_met and blocking:
            failed_criteria.append(cid)

        entry = {
            "id": cid,
            "description": spec_c.get("description", ""),
            "final_score": round(final_score, 4),
            score_key: round(score, 4),
            "weight": weight,
            "visual_threshold": visual_threshold,
            "threshold_met": threshold_met,
            "blocking": blocking,
            observations_key: item.get(observations_key, ""),
            "svg_fixes": validated_fixes,
        }
        # Keep audit trail of the other score type as null
        if ascii_fallback:
            entry["visual_score"] = None
        else:
            entry["ascii_score"] = None
        criteria_results.append(entry)

    overall_score = _overall_avg(criteria_results)
    weighted_score = _weighted_avg(criteria_results)
    global_threshold_met = overall_score >= global_threshold
    delivery_blocked = bool(failed_criteria)
    should_deliver = global_threshold_met and not delivery_blocked

    # Build next_iter_directive
    passing_ids = [
        c["id"] for c in criteria_results
        if c["threshold_met"]
    ]
    if should_deliver:
        next_iter_directive = "DELIVER — all thresholds met."
    elif failed_criteria:
        do_not_touch = (
            f" Do NOT change: {', '.join(passing_ids)}." if passing_ids else ""
        )
        next_iter_directive = (
            f"CONTINUE — apply svg_fixes for: {', '.join(failed_criteria)}.{do_not_touch}"
        )
    else:
        next_iter_directive = (
            f"CONTINUE — overall score {overall_score:.2f} < threshold {global_threshold}. "
            "Improve all criteria proportionally."
        )

    critique = {
        "run_id": run_id,
        "iteration": iteration,
        "judge_mode": judge_mode,
        "merge_strategy": "visual_authoritative",
        "svg_fix_format": svg_fix_format,
        "timestamp": _ts(),
        "png_path": png_path,
        "overall_score": round(overall_score, 4),
        "weighted_score": round(weighted_score, 4),
        "global_threshold": global_threshold,
        "global_threshold_met": global_threshold_met,
        "delivery_blocked_by": failed_criteria,
        "should_deliver": should_deliver,
        "criteria": criteria_results,
        "priority_fixes": all_priority_fixes,
        "next_iter_directive": next_iter_directive,
    }
    if fix_warnings:
        critique["fix_validation_warnings"] = fix_warnings

    Path(out_path).write_text(json.dumps(critique, indent=2), encoding="utf-8")
    print(f"critique written → {out_path}")
    _print_summary(critique)
    return critique


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def _print_summary(critique: dict) -> None:
    print()
    print(f"{'VISUAL JUDGE SUMMARY':=^72}")
    print(f"  Run      : {critique['run_id']}  |  Iteration: {critique['iteration']}")
    print(f"  Mode     : {critique['judge_mode']}  ({critique['merge_strategy']})")
    print(f"  Overall  : {critique['overall_score']:.2f}  "
          f"(weighted: {critique['weighted_score']:.2f})  "
          f"threshold: {critique['global_threshold']}")
    print(f"  Decision : {'✅ DELIVER' if critique['should_deliver'] else '🔁 CONTINUE'}")
    if critique["delivery_blocked_by"]:
        print(f"  Blocked  : {', '.join(critique['delivery_blocked_by'])}")
    print()
    print(f"  {'Criterion':<30} {'Score':>6} {'VT':>6} {'Met':>5} {'Mode'}")
    print(f"  {'-'*30} {'-'*6} {'-'*6} {'-'*5} {'-'*14}")
    for c in critique["criteria"]:
        met = "✅" if c["threshold_met"] else "❌"
        mode = critique["judge_mode"]
        print(f"  {c['id']:<30} {c['final_score']:>6.2f} "
              f"{c['visual_threshold']:>6.2f} {met:>5}  {mode}")
    print()
    if critique["priority_fixes"]:
        print("  Priority fixes for next iteration:")
        for fix in critique["priority_fixes"]:
            print(f"    • {fix}")
    if critique.get("fix_validation_warnings"):
        print()
        print("  ⚠️  svg_fix validation warnings (fixes dropped):")
        for w in critique["fix_validation_warnings"]:
            print(f"    ! {w}")
    print(f"\n  Directive: {critique['next_iter_directive']}")
    print("=" * 72)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="theloop visual judge — authoritative visual scoring with JSON critique output."
    )
    ap.add_argument("png", help="Path to the rendered PNG for this iteration.")
    ap.add_argument("spec", help="Path to judge_spec.json (criteria + thresholds).")

    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--emit-prompt", action="store_true",
        help="Print the inspection prompt the model reads before viewing the PNG."
    )
    mode.add_argument(
        "--ingest", action="store_true",
        help="Read model's JSON response from stdin and produce critique.json."
    )

    ap.add_argument(
        "--iter", type=int, default=1,
        help="Current iteration number (used in critique.json and prompt header)."
    )
    ap.add_argument(
        "--ascii-fallback", action="store_true",
        help="Treat stdin scores as ASCII-judge scores (vision unavailable). "
             "final_score = ascii_score; judge_mode = 'ascii-fallback'."
    )
    ap.add_argument(
        "--out", default="critique.json",
        help="Output path for critique.json (--ingest mode only)."
    )

    args = ap.parse_args()
    spec = _load_json(args.spec)

    if args.emit_prompt:
        emit_prompt(args.png, spec, args.iter)
    else:
        response_raw = sys.stdin.read().strip()
        if not response_raw:
            print("ERROR: --ingest requires JSON piped to stdin.", file=sys.stderr)
            sys.exit(1)
        ingest(
            png_path=args.png,
            spec=spec,
            response_json=response_raw,
            iteration=args.iter,
            ascii_fallback=args.ascii_fallback,
            out_path=args.out,
        )


if __name__ == "__main__":
    main()
