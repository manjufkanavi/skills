#!/usr/bin/env python3
"""
repo-cleanup-analyzer.py — Inventory a repository and produce a keep/discard plan.

Walks a repo (pruning virtualenvs, .git, __pycache__, node_modules), breaks down
each top-level directory by size + dominant file types, computes a grand total,
and — given a keep-set — reports what to delete and how much it reclaims.

Also has a --find N mode to locate JSON deliverables that contain a top-level list
of exactly N items (e.g. "the 60 curated questions").

Usage:
    python repo-cleanup-analyzer.py [REPO_ROOT]              # inventory only
    python repo-cleanup-analyzer.py REPO --keep keep.json    # + keep/discard split
    python repo-cleanup-analyzer.py REPO --find 60           # locate N-item JSON lists

keep.json format:
    {
      "keep": ["retrieval/retriever_raft.py", "data/raft-aws.parquet"],
      "discard_dirs": ["solvarch", "markdown"]   # optional; top-level dir names to delete wholesale
    }

Exit code 0 on success. Relies only on the Python stdlib.
"""
import os, sys, json, argparse
from collections import defaultdict
from pathlib import Path

NOISE = (".git", "__pycache__", "node_modules")
SKIP_EXTS = {".pyc"}

EXT_LABELS = {
    ".npy": "npy-checkpoints", ".md": "markdown", ".json": "json",
    ".py": "python", ".pptx": "pptx", ".pdf": "pdf", ".parquet": "parquet",
    ".png": "png", ".docx": "docx", ".html": "html", ".jpeg": "image",
    ".jsonl": "jsonl",
}


def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}PB"


def is_noise(path):
    return any(seg in NOISE for seg in path.parts) or str(path).endswith(".venv")


def analyze(root):
    """Return (root, [(relpath, size), ...]) for every non-noise file."""
    root = Path(root).resolve()
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not is_noise(Path(dirpath) / d)]
        if is_noise(Path(dirpath)):
            dirnames[:] = []
            continue
        for f in filenames:
            if f.endswith(SKIP_EXTS):
                continue
            p = Path(dirpath) / f
            try:
                files.append((str(p.relative_to(root)).replace(os.sep, "/"), p.stat().st_size))
            except OSError:
                pass
    return root, files


def summarize(files):
    by_top = defaultdict(lambda: {"size": 0, "count": 0, "ext": defaultdict(int)})
    for rel, size in files:
        top = rel.split("/", 1)[0]
        by_top[top]["size"] += size
        by_top[top]["count"] += 1
        ext = rel.rsplit(".", 1)[-1].lower() if "." in rel else "(none)"
        by_top[top]["ext"][ext] += 1
    return by_top


def dominant(extmap):
    if not extmap:
        return ""
    ext, n = max(extmap.items(), key=lambda kv: kv[1])
    return f"{EXT_LABELS.get(ext, ext)}x{n}"


def find_nitem(files, root, n):
    hits = []
    for rel, size in files:
        if not rel.lower().endswith(".json"):
            continue
        try:
            data = json.loads((root / rel).read_text())
        except Exception:
            continue
        items = list(data.values()) if isinstance(data, dict) else ([data] if isinstance(data, list) else [])
        for lst in items:
            if isinstance(lst, list) and len(lst) == n:
                key = next((k for k, v in (data.items() if isinstance(data, dict) else [])
                             if isinstance(v, list) and len(v) == n), "?")
                hits.append((size, rel, key))
                break
    return hits


def main():
    ap = argparse.ArgumentParser(description="Inventory a repo and plan keep/discard.")
    ap.add_argument("root", nargs="?", default=".", help="repo root (default: cwd)")
    ap.add_argument("--keep", help="JSON file listing keep paths + optional discard_dirs")
    ap.add_argument("--find", type=int, metavar="N",
                    help="print JSON files containing a top-level list of exactly N items")
    args = ap.parse_args()

    root, files = analyze(args.root)
    by_top = summarize(files)
    grand = sum(d["size"] for d in by_top.values())

    print("=" * 72)
    print(f"REPO INVENTORY: {root}")
    print("=" * 72)
    print(f"{'DIRECTORY':<24}{'SIZE':>10}{'FILES':>8}  DOMINANT")
    print("-" * 72)
    for top in sorted(by_top, key=lambda t: by_top[t]["size"], reverse=True):
        d = by_top[top]
        print(f"{top:<24}{human(d['size']):>10}{d['count']:>8}  {dominant(d['ext'])}")
    print("-" * 72)
    print(f"{'TOTAL':<24}{human(grand):>10}{sum(d['count'] for d in by_top.values()):>8}")

    if args.find is not None:
        hits = find_nitem(files, root, args.find)
        print("\n" + "=" * 72)
        print(f"JSON files containing a top-level list of exactly {args.find} items:")
        print("=" * 72)
        if not hits:
            print("  (none found)")
        for size, rel, key in sorted(hits, reverse=True):
            print(f"  {human(size):>9}  {rel}  (list len {args.find} @ key '{key}')")

    if args.keep:
        doc = json.loads(Path(args.keep).read_text())
        keep_paths = set(doc.get("keep", []))
        kept = [(r, s) for r, s in files if r in keep_paths]
        discarded = [(r, s) for r, s in files if r not in keep_paths]
        kept_total = sum(s for _, s in kept)
        disc_total = sum(s for _, s in discarded)

        print("\n" + "=" * 72)
        print("KEEP / DISCARD PLAN")
        print("=" * 72)
        print(f"  KEEP   : {len(kept):>6} files   {human(kept_total)}")
        print(f"  DISCARD: {len(discarded):>6} files   {human(disc_total)}")
        print(f"  NET    : reclaim {human(disc_total)} "
              f"({100.0 * disc_total / max(grand, 1):.1f}% of inventory)")

        disc_by_top = defaultdict(lambda: [0, 0])
        for r, s in discarded:
            t = r.split("/", 1)[0]
            disc_by_top[t][0] += 1
            disc_by_top[t][1] += s
        print("\n  Discard by top-level directory:")
        for t in sorted(disc_by_top, key=lambda x: disc_by_top[x][1], reverse=True):
            c, sz = disc_by_top[t]
            print(f"    {t:<22}{human(sz):>10} ({c} files)")


if __name__ == "__main__":
    main()
