# Repository Cleanup — Debugging Lessons

Session-specific lessons for producing a keep/discard plan on an accumulated repo
(`project_work`, ~2.5 GB → 24.9 MB target). These capture the traps that produced
wrong output on the first attempts.

## 1. The virtualenv-bloat trap (output dominated by one dir)

Naively walking a repo and printing every file produces output where a single
virtualenv (`retrieval/venv/`) can be 700+ MB and thousands of files. The "total"
is meaningless until you prune noise.

**Fix:** prune `.git`, `__pycache__`, `node_modules`, and any `*/venv` / `*.venv`
directory **in place** during `os.walk` (mutate `dirnames[:]`), and skip `.pyc`.
The `repo-cleanup-analyzer.py` script does exactly this — use it instead of a raw
`find` dump.

## 2. Operator-precedence bug: `ROOT/p.stat()`

Writing `sorted(paths, key=lambda p: ROOT/p.stat().st_size)` raises
`'str' object has no attribute 'stat'`. Python evaluates the method chain
`p.stat()` **before** the `/`, i.e. it computes `ROOT / (p.stat())`, but `p` is a
string so `p.stat()` itself fails.

**Fix:** parenthesize the division: `(ROOT/p).stat().st_size`.

## 3. "Walk lists the file but the path doesn't exist"

A directory walk can report `benchmark/benchmark_report.json` with a real size,
yet `Path("benchmark/benchmark_report.json").exists()` returns `False`. Two causes:

- **Path flattening:** the walk prints files from *subdirectories* (e.g.
  `benchmark/output/benchmark_report.json`) but the relative path shown drops the
  subdirectory. Locate with full-path `find` instead of root-relative assumptions:
  `find benchmark -name '*.json' -not -path '*/venv/*'`.
- **Broken symlinks:** `stat()` follows them and can succeed while `exists()`
  (which checks the target) fails. Confirm with `ls -la` / `readlink` / `realpath`.

## 4. Find deliverables by structure, not by filename

You often don't know which file holds a deliverable ("the 60 curated questions").
Rather than guess filenames, **inspect JSON structure**: load each `.json`, collect
top-level list values, and match on **list length**. The session found
`benchmark/data/benchmark_dataset_v1.json` has a top-level `questions` list of
length **60** — matched by count, not by name. The analyzer's `--find N` mode does
this automatically (it prints every JSON file containing a top-level list of
exactly N items, with the key name).

## 5. Keep/discard accounting

- Compute `grand = sum(all file sizes)` first.
- `KEEP` = explicit list of relative paths the user wants to retain (reports, the
  RAG pipeline code, the new HF corpus, new benchmark reports).
- `DISCARD` = everything else. Report reclaim % = `discard_total / grand * 100`.
- Break discard down **by top-level directory** so the plan shows the big wins
  (e.g. `solvarch/` = 6,480 `.npy` checkpoints = 633 MB; `markdown/` = 437 old docs).
- Flag `.venv`/virtualenvs as a delete+gitignore item — they should never be
  committed and often dominate the "delete" number.
