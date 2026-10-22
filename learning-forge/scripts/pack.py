#!/usr/bin/env python3
"""learning-forge platform pack: turn the finished video into learning-platform artifacts.

Reads:  script.json, pedagogy.json, out/final.mp4, out/scene_offsets.json, out/subtitles.srt
Writes: out/chapters.json, out/metadata.json, out/thumbnail.png
Validates: out/quiz.json (agent-authored; must cite pedagogy claim ids)

Everything a learning platform needs in one folder:
  final.mp4 + subtitles.srt + chapters.json + thumbnail.png + quiz.json + metadata.json
"""
import argparse, json, re, subprocess
from pathlib import Path

ROLE_LABEL = {
    "hook": "The Hook", "friction": "Why the Old Way Breaks", "hero": "The Breakthrough",
    "sugar": "Under the Hood", "wrapper": "The Mechanism", "example": "Real Example",
    "twist": "The Trap", "misconception": "The Trap", "quiz": "Your Turn",
    "recap": "The Golden Rule", "cta": "Next Step",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    a = ap.parse_args()
    proj = Path(a.project).resolve()
    out = proj / "out"
    script = json.loads((proj / "script.json").read_text())
    ped = json.loads((proj / "pedagogy.json").read_text())
    offsets = json.loads((out / "scene_offsets.json").read_text())

    # chapters
    chapters = []
    for s in script["scenes"]:
        o = offsets.get(s["id"])
        if not o:
            continue
        chapters.append({
            "title": s.get("chapter_title") or ROLE_LABEL.get(s.get("role"), s["id"]),
            "start": round(o["start"], 2), "end": round(o["end"], 2),
        })
    (out / "chapters.json").write_text(json.dumps({"topic": script.get("topic"),
        "chapters": chapters}, indent=1))

    # metadata
    known_ids = {c["id"] for c in ped.get("claims", [])} | {m["id"] for m in ped.get("misconceptions", [])}
    src = sorted(ped.get("sources", []), key=lambda s: -s.get("authority", 0))[:5]
    tags = sorted({w for c in ped.get("claims", []) for w in re.findall(r"[A-Za-z]{4,}", c.get("claim", ""))
                   if w.lower() not in {"that", "this", "with", "when", "will", "from", "they", "have"}})[:8]
    metadata = {
        "topic": script.get("topic"),
        "format": script.get("format"),
        "duration_seconds": round(sum(c["end"] - c["start"] for c in chapters), 1),
        "titles": script.get("title_candidates", [script.get("topic", "Untitled")][:3] or [script.get("topic")]),
        "description": script.get("description",
            f"{ped.get('objective', script.get('topic'))} — a {script.get('format')} from the learning-forge pipeline."),
        "tags": tags,
        "audience": ped.get("audience", "beginner"),
        "prerequisites": ped.get("prerequisites", []),
        "learning_objective": ped.get("objective"),
        "sources": [{"title": s.get("title"), "url": s.get("url")} for s in src],
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=1))

    # thumbnail: frame at 45% into the hero scene (the aha moment)
    hero = next((s for s in script["scenes"] if s.get("role") in ("hero", "sugar", "wrapper")), script["scenes"][2] if len(script["scenes"]) > 2 else script["scenes"][0])
    o = offsets[hero["id"]]
    t = o["start"] + 0.45 * (o["end"] - o["start"])
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}",
                    "-i", str(out / "final.mp4"), "-frames:v", "1", str(out / "thumbnail.png")], check=True)

    # quiz validation (agent-authored quiz.json)
    quiz_path = proj / "quiz.json"
    if quiz_path.exists():
        quiz = json.loads(quiz_path.read_text())
        qs = quiz.get("questions", [])
        ok = len(qs) >= 3
        for q in qs:
            ok &= len(q.get("options", [])) == 4 and 0 <= q.get("answer", -1) < 4
            ok &= q.get("explanation", "").strip() != ""
            cited = q.get("claims", [])
            ok &= bool(cited) and all(c in known_ids for c in cited)
        if ok:
            (out / "quiz.json").write_text(json.dumps(quiz, indent=1))
            print(f"quiz: {len(qs)} questions validated -> out/quiz.json")
        else:
            print("quiz: VALIDATION FAILED (need >=3 MCQs, 4 options, answer, explanation, cited claim ids)")
    else:
        print("quiz: no quiz.json in project dir — author one (3+ MCQs citing claim ids)")

    files = ["final.mp4", "subtitles.srt", "chapters.json", "metadata.json", "thumbnail.png", "quiz.json"]
    print("\nPLATFORM PACK MANIFEST")
    for f in files:
        p = out / f
        print(f"  {'OK ' if p.exists() else 'MISSING'} {f}" + (f" ({p.stat().st_size/1e6:.1f}MB)" if p.exists() else ""))

if __name__ == "__main__":
    main()
