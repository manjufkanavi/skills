"""Offline plot → structured plan pass (semantic planning, done in-model by the agent).

This is NOT a heuristic sentence-splitter. It performs *understanding*: it reads the plot and
emits a structured plan — characters with bibles, beats where each 5s scene attributes who
says what, a derived theme, and per-scene visual notes. The agent (me) drives the reasoning;
this module only *serializes* that understanding into a JSON file.

Usage (invoked by the agent, not as a CLI):
    plan = build_plan_from_plot(plot_text)   # returns dict, written by caller as plan.json

The agent is expected to read the plot and fill in:
  * theme, characters (name/gender/description/bible), beats[{dialogue:[{speaker,line}]}]
Everything here does is validate + normalize that plan into the exact shape main.py needs.

No external LLM, no network — fully offline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def build_plan_from_plot(plan: dict) -> dict:
    """Validate + normalize a structured plan.

    The agent (me) is expected to fill in theme, characters[] and beats[]. This function
    validates structure, normalizes whitespace on dialogue lines, dedupes characters by name,
    and returns a clean plan dict. If the plot is empty it raises ValueError so main.py can
    fail loudly rather than emit an empty plan.

    The agent is expected to pass a *dict* with theme/characters[]/beats[] filled in (the
    product of its own in-model reading of the plot). This function only validates + normalizes.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a dict with theme/characters[]/beats[]")

    if not plan:
        raise ValueError("cannot build a plan from an empty plot")

    # --- Validate + normalize characters (dedupe by slug, keep order) ---
    seen = set()
    chars_out: list[dict] = []
    for c in plan.get("characters", []):
        name = (c.get("name") or "").strip()
        if not name:
            continue
        slug = _slugify(name)
        if slug in seen:
            continue  # dedupe — same character described twice
        seen.add(slug)
        chars_out.append({
            "name": name,
            "gender": (c.get("gender") or "").strip().lower() if \
                (c.get("gender") or "").strip().lower() in ("male", "female") else "neutral",
            "description": (c.get("description") or "").strip(),
        })
    # A plot with no named characters is not enough to drive the pipeline.
    if not chars_out:
        raise ValueError(
            "plan has no characters — the agent must identify who is in the story")

    # --- Validate + normalize beats (strip dialogue whitespace, drop empty) ---
    beats_out: list[dict] = []
    for i, b in enumerate(plan.get("beats", []), start=1):
        narr = (b.get("narration") or "").strip()
        dialogue: list[dict] = []
        for d in b.get("dialogue", []) or []:
            speaker = (d.get("speaker") or "").strip()
            line = (d.get("line") or "").strip().strip('"').strip("'").strip()
            if not speaker or not line:
                continue  # drop half-empty dialogue beats; narration-only scene still counts
            dialogue.append({"speaker": speaker, "line": line})

        # A beat needs either narration or dialogue; otherwise it's a no-op scene.
        if not narr and not dialogue:
            continue

        beats_out.append({
            "narration": narr,
            "dialogue": dialogue,
        })

    if not beats_out:
        raise ValueError(
            "plan has no usable beats — the agent must split the plot into 5s scenes")

    plan["characters"] = chars_out
    plan["beats"] = beats_out
    return plan


def write_plan(plan: dict, out_path: Path) -> None:
    """Write the plan to disk as JSON (pretty-printed, UTF-8)."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
