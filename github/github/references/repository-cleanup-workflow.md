# Repository Cleanup & Restructuring (commit + push)

Massively trimming or reorganizing a git repo (dropping legacy artifacts, restructuring folders,
then committing + pushing) requires a **verify-first loop** — because a move or delete can silently
break hardcoded path references in the code that must survive.

## The verify-first loop

1. **Dry-run first** — preview every delete/add before touching anything:

   ```bash
   git add -A --dry-run | grep -E 'add|modify|delete' | awk '{print $NF}' | sort | uniq -c
   ```

2. **Confirm keep-code path references resolve AFTER deletion.** Many pipelines hardcode corpus
   paths (e.g. `data/raft_records.jsonl`, `data/corpus_index.jsonl`). Spot-check:

   ```bash
   python3 -c "import os;print(all(os.path.exists(p) for p in ['data/raft_records.jsonl','data/corpus_index.jsonl']))"
   ```

3. **Delete legacy directories only after `git grep` confirms nothing references them** (e.g.
   `solvarch/`, the old `markdown/` scraped corpus). Spot-check against HEAD:

   ```bash
   git grep -n "solvarch/training-data" origin/main | head   # if hits, keep or update refs
   ```

4. **Execute deletions + moves** (move report deliverables into a `reports/` folder:
   `reports/abstract/`, `reports/midsem/`, `reports/final/`).

5. **Verify the tree** is what you intended:

   ```bash
   find . -maxdepth 3 -not -path './.git/*' | sort
   ```

6. **Commit with a `-F` message file** (avoids shell-quoting pitfalls with long bodies), then push:

   ```bash
   git commit -F /tmp/commit_msg.txt
   git push origin main
   ```

7. **Verify the REMOTE tree, not just local HEAD:**

   ```bash
   git ls-remote origin main                        # remote SHA
   git cat-file -e "origin/main:<path>" && echo present
   ```

## git-LFS gotcha (large files: parquet, PDF, PPTX)

Git-LFS may be **globally configured** (`git config --list | grep filter` shows
`filter.lfs.clean=git-lfs clean -- %f`, `filter.lfs.required=true`) **without any `.gitattributes`
rule applying it**. In that case large files are stored as **normal git objects with real content** —
commits and pushes work fine, no LFS pointers.

But some files can end up stored as **empty (0-byte) blobs** if a clean filter strips them. Always
verify what actually landed in the index before committing:

```bash
# Stage, then inspect the blob sizes git stored:
git add -A
git ls-files -s | awk '{print $4, $5}'   # mode, type
git cat-file -s <blob-sha>               # byte size of the stored object

# Empty-content hashes worth knowing by heart:
#   e69de29bb2d1d6434b8b29ae775ad8c2e48c5391  = the canonical empty (0-byte) blob
#   50a2212749ea9280d0fb78cbde096f2bc5645574  = another empty-content hash
# A 17 MB parquet / 700 KB PDF that shows a real size (e.g. 17713755, 740366 bytes) is a normal
# object — commit + push carries it correctly.
```

**Diagnosis commands:**

```bash
git config --list | grep -iE 'filter|lfs|autocrlf|clean|smudge'   # is LFS globally configured?
git check-ignore -v <file>                                        # which .gitignore rule matches (none -> not ignored)
git cat-file -s <blob-sha>                                       # byte size actually stored
git ls-remote origin main                                        # confirm remote has the new commit SHA
```

**Decision rule:** if `git cat-file -s <blob>` returns a **non-zero** size, the file is a normal
object and the commit/push is correct — no `.gitattributes` LFS rule means git-lfs does not
interfere. If a file unexpectedly shows **0 bytes** (empty-blob hash) despite having content on
disk, a clean filter stripped it — re-add with `git add --no-filter <path>` and re-inspect before
committing.

## Post-cleanup sanity checklist

- [ ] Legacy paths absent from the remote tree (`git cat-file -e origin/main:<legacy-path>` fails cleanly).
- [ ] Key deliverables present on the remote tree (`data/…`, `reports/…`, pipeline code).
- [ ] `.gitignore` still excludes `venv/`, `__pycache__/`, `*.npy`, checkpoints — and does NOT accidentally ignore `data/` or `reports/`.
- [ ] New `README.md` documents the reorganized layout + how to reinstall deps to re-run.
