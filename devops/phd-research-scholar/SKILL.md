---
name: phd-research-scholar
description: Workflow for conducting AI/ML research projects — literature review, experiment design, benchmark creation, fine-tuning, and dissertation writing. Covers RAG, SLMs, PEFT (LoRA/QLoRA/DPO), and evaluation methodology.
version: 1.0.0
tags: [research, phd, rag, slm, peft, fine-tuning, benchmark, dissertation]
---

# PhD Research Scholar — Research Workflow

Complete workflow for conducting AI/ML research on code-specialized small language models for cloud architecture decision support.

## Workflow Stages

### Stage 1: Literature Review
1. Search arXiv, Google Scholar, IEEE Xplore, ACM DL for papers matching keywords
2. Extract key findings, methods, and gaps
3. Build synthesis table (model, method, dataset, metric, result, limitation)
4. Identify research gap the project will fill

### Stage 2: Corpus Curation
1. Collect AWS Well-Architected whitepapers, service docs, pricing data
2. Download Architecture Center reference architectures
3. Collect public ADRs and Solutions Architect exam question banks
4. Chunk documents with metadata (service, region, pillar, document type)
5. Build semantic index with metadata filters

### Stage 2.5: Structured Training Data Validation
When working with structured JSON training data (not raw documents), validate against the training schema before fine-tuning.

**Common issues:**
1. **Type mismatches** — `components` field is `["EC2","S3"]` (strings) instead of `[{"service":"EC2","role":"...","configuration":"..."}]` (objects)
2. **Nested structure mismatches** — `principles` is a comma-separated string instead of a list
3. **Enum mismatches** — `industry` uses non-standard names like `"Fintech & Banking"` instead of `"Financial Services"`
4. **ID format mismatches** — `id` is `"aws-arch-1000"` (4 digits) vs regex `^aws-arch-[0-9]{3}$`
5. **Constraint violations** — `service_combination` has 10 items, schema says max 8

**Resolution:** Never discard records for enum mismatches — map them instead. Truncate lists that exceed maxItems. Update regex patterns if constraints are too narrow. Always re-validate after fixing.

**Reference:** `references/training-data-schema-validation.md` — complete workflow, code patterns, and pitfall catalog.

### Corpus Validation (run before each commit)

**Automated script:** `scripts/corpus_validate.py <corpus_dir> <output_dir>` — generates category_index.json, manifest.json, delete_noise.sh, verify_corpus.sh.

**Rebase resolver:** `scripts/rebase_rename_delete_resolver.sh <repo_root>` — resolves 45+ rename/delete conflicts when both local and remote modified the same files (e.g., corpus backup rename vs remote delete).

**Detailed noise patterns:** `references/corpus-validation-checklist.md`  
**Merge conflict resolution:** `references/merge-corpus-conflict-resolution.md`  
**Structured training data validation:** `references/training-data-schema-validation.md`

**Phase 1: Scan & Inventory**
1. Count total files in corpus directory
2. Compute size statistics (min, max, mean, median)
3. Read each file to get character count, first line (title), and content markers

**Phase 2: Noise Detection**
Mark as noise and DELETE:
- **CLI references**: "AWS CLI 2.x Command Reference" pages (e.g., `ec2`, `s3`, `iam` CLI commands)
- **SDK references**: "AWS SDK for Java/Python" pages (e.g., `AWSServiceQuotasClient`)
- **Very small files** (<500 chars): likely empty or stub content (threshold raised from 200 — even 500-900 char files often lack architecture depth)
- **Broken headings**: Files with `# None` heading AND short content (<1000 chars)
- **Welcome stubs**: "Welcome - [Service Name]" pages with <5000 chars (intro pages with no architecture detail)
- **Glossaries**: AWS Glossary entries (not useful for RAG retrieval)

**Phase 3: Classification**
Classify each kept file into:
1. **Primary pillar** (one of 6 AWS Well-Architected pillars) — assign based on keyword matching; first match wins
2. **Cross-referenced services** (list of AWS services mentioned) — multiple per file
3. **Uncategorized** — files not matching any pillar keyword (flag for manual review)

**Phase 4: Output**
Produce these deliverables:
1. **`validated_corpus_report.md`** — Full report with stats, classifications, recommendations
2. **Rebuilt `category_index.json`** — New structure with pillar categories + service categories
3. **`manifest.json`** — Summary table with pillar/service/category counts
4. **Corpus backup** — `corpus.corpus_backup.<date>/` directory
5. **Deletion script** — review before executing (e.g., `delete_noise.sh`)
6. **Verification script** — confirm correct file count after deletion

**Post-validation checklist:**
- [ ] Backup verified (original corpus preserved)
- [ ] Report reviewed and approved
- [ ] Deletion script reviewed and executed
- [ ] File count verified (should match: original − deleted_noise = valid)
- [ ] `category_index.json` validated (every kept file in at least one pillar)
- [ ] UNCERTAIN files flagged for manual pillar assignment
- [ ] Coverage gaps identified (e.g., low-count pillars needing supplementation)

**Pitfalls:**
- **Wrong-project content**: Auto-conversion or paste errors can inject slides/docs from other projects. Always verify each markdown file's header/context matches the project.
- **Redundant backup dirs**: `backup/`, `original_files_backup/`, `markdown_converted/` are almost always redundant — the primary `markdown/` directory is the source of truth.
- **PDFs vs markdown**: When both exist and markdown was converted from PDF, the markdown is the working copy. PDFs become noise — keep only if they carry unique metadata not in the markdown.
- **Always backup before delete**: Never skip the `.corpus_backup` step. Use it as a staging area, verify the cleaned state is correct, then optionally remove it later.
- **Cross-referenced services inflate totals**: A file appears in 1 pillar + N services. Pillar total = unique files; service total counts overlaps. Always verify `unique pillar-assigned files == total kept files`.
- **Silent `execute_code` blocks in cron**: When running validation scripts in cron, cron may block `execute_code` tool. Use `terminal` instead for Python scripts, or set `approvals.cron_mode: approve`.
- **Script over-aggressive on noise**: `scripts/corpus_validate.py` has known false positives:
  - `"Welcome -"` pattern matches ALL pages starting with "Welcome" (including substantive docs like "What is DynamoDB?" at 15KB and "Creating an SNS topic" at 22KB). **Fix**: use title-only check (`"welcome -" in title.lower()`) rather than content scan.
  - `"aws cli"` keyword match fires on any doc mentioning CLI in passing (e.g., the 1.7MB AWS Well-Architected Framework doc contains "aws cli" 31+ times). **Fix**: match `cli\s+\d+\.\d+` in the TITLE only, not content.
  - `"aws sdk for java/python"` matches in body text. **Fix**: match only in title, e.g., `re.search(r'sdk\s+for\s+(java|python|go|js)', title, re.I)`.
  - Always review the full delete list before executing — spot-check 10 files including any >5KB.
- **Divergent git branches on corpus validation**: When local and remote both run corpus validation independently, they diverge from the common ancestor. Local deleted X files; remote deleted Y files (possibly different). **Resolution**: `git reset --hard origin/main` to adopt the remote's (usually more thorough) validation, then re-apply any additional local changes on top. Don't try to merge two independent validations — they produce incompatible states.
- **Rename/delete conflicts with backup dirs**: When corpus cleanup deletes files while a backup simultaneously renamed them to `corpus.corpus_backup.<date>/`, git produces 18+ rename/delete conflicts (status `UD` = they renamed, you deleted). **Fix**: accept remote (`git checkout --theirs`) for content conflicts (`UU`), and `git rm --cached` for each `UD` path. If you need the remote version, `git reset --hard origin/main` then re-apply.

### Stage 3: Retrieval Pipeline
For a full implementation workflow, see the `retrieval-engineering` skill.
1. Build BM25 sparse retriever (Whoosh or Elasticsearch)
2. Build dense retriever (SBERT via sentence-transformers + FAISS)
3. Implement RRF fusion and cross-encoder reranking
4. Evaluate retrieval quality (MRR@10, NDCG@10, Recall@100)
5. Test metadata filtering by service/region/pillar

### Stage 4: Data Generation
1. Use strong teacher model (GPT-4/Claude) to generate architecture-decision dialogues
2. Apply Evol-Instruct style expansion (increase difficulty)
3. Apply OSS-Instruct style extraction from corpus
4. Quality-filter via teacher-model self-consistency
5. Rubric-based review against AWS Well-Architected pillars

### Stage 5: Fine-tuning
1. Setup Qwen2.5-Coder-3B with LoRA/QLoRA (bitsandbytes 4-bit)
2. Train on instruction-tuning dataset
3. Ablate: retrieval-aware vs retrieval-blind training
4. Optional: DPO on multi-pillar trade-off preference pairs
5. Track metrics: loss curves, validation perplexity, hardware utilization

### MLX-native fine-tuning (Apple Silicon):**
- PEFT does NOT work with MLX models — `get_peft_model(model, config)` fails with `AttributeError: 'Model' object has no attribute 'get_submodule'`
- Use MLX-native LoRA: implement manually with `mlx.nn.Linear` subclasses or use `mlx.lora` if available
- Model loading: `from mlx_lm import load` — works with `mlx-community/*` HF repos
- Generation: `generate(model, tokenizer, prompt, max_tokens)` — does NOT accept `temperature`/`top_p` kwargs; use `sampler` parameter instead
- Training loop: use `mlx.value_and_grad(model, loss_fn)()` — loss_fn must accept params and call `model.update_params(params)`
- Batch training: pad sequences manually with numpy, use `model.loss("causal_lm", ids, mask)`
- venv path: `/Users/manjunathkanavi/workspace/scripts/python_venv/` has `mlx`, `mlx-lm`, `peft`, `transformers`
- Model cache: `~/.cache/huggingface/hub/models--<repo>--<name>/` or `~/.models/<name>/`
- **Verbose epoch logging**: Add per-step logging (loss, avg_loss, grad_norm, tokens, steps/s, elapsed) and per-epoch summary (final_loss, loss_range, loss_std, epoch_time). Print epoch start/complete headers with separator lines. Store `epoch_results` list with train_loss, eval_loss, perplexity, time per epoch.
- **Performance**: Manual LoRA with `mlx.value_and_grad` is slow (~110s/step). Optimize by: increasing batch_size (2→4 halves steps), reducing epochs (5→2 saves 60%), sampling fewer batches per epoch. Default MLX device is GPU (`mlx.default_device()` → `Device(gpu, 0)`), but `mlx.set_device(mlx.gpu)` may fail — rely on default.
- **Training script patching**: When patching Python files, the patch tool can break multi-line f-strings (splits `print(f"\n{'='*60}")` across lines). Always verify syntax with `python3 -m py_compile` after patching. Fix broken f-strings by replacing line-by-line with `python3 -c` reading raw `repr()` of affected lines.

### Stage 6: Evaluation & Benchmarking
1. **Design benchmark** — Create 60 scenario-based questions (10 per AWS Well-Architected pillar). Each question has: scenario, constraints, expected services, expected concepts, gold rationale, gold_rejected_services (anti-patterns).
2. **Generate dataset** — Use `benchmark/scripts/generate_dataset.py` to create structured JSON.
3. **Run evaluation** — Use `benchmark/run_full.py` to call baseline models via OpenAI-compatible API. System prompt sets role, each question is user prompt, max_tokens=2000, temp=0.1.
4. **Score responses** — Rule-based scorer: factuality (expected services/concepts found, weight 0.30), constraint_satisfaction (constraints addressed, weight 0.25), hallucination_rate (rejected services mentioned — inverse, weight 0.20), relevance (substance/structure/actionability, weight 0.15), decision_quality (trade-off discussion, weight 0.10).
5. **Aggregate results** — Per-pillar and per-baseline aggregation with weighted scores.
6. **Compare baselines** — Run same benchmark on vanilla, RAG-augmented, fine-tuned models.
7. **Human review** — Automated metrics miss nuance. Always include expert review.

**Implementation notes:**
- `~/.nanobot/config.json` supports `env:` prefix for API keys (e.g., `"env:DEEPSEEK_API_KEY"`) to avoid hardcoding secrets.
- Python subprocess output needs `PYTHONUNBUFFERED=1` + `sys.stdout.reconfigure(line_buffering=True)` for real-time capture.
- Add `time.sleep(2)` between API calls to respect rate limits.
- Test API connectivity before running full benchmark — silent failures on bad keys.

**Verification:**
- **Task status ≠ task completion**. Always verify benchmark artifacts (JSON reports, per-query results, HTML slides) in the git repo before marking a benchmarking task done.
- Check that `per_baseline` keys in report JSON match ALL baselines asked for in the task body.
- Use `combined_data.json` or separate report files to identify which baseline produced which scores when `baseline_name` field is unreliable (see `references/benchmark-baseline-labeling-bug.md`).

### Stage 7: Dissertation
1. Write introduction (problem, motivation, contributions)
2. Write related work section (synthesis of literature)
3. Write methodology (corpus, retrieval, fine-tuning, evaluation)
4. Write results and analysis
5. Write conclusion and future work
6. Prepare supervisor/additional examiner reviews

## Key Decisions to Track

| Decision | Options | Impact |
|----------|---------|--------|
| Base model | Qwen2.5-Coder-3B (fixed) | Reproducibility, hardware constraints |
| Retrieval | BM25 + dense + reranker | Retrieval quality vs. compute cost |
| Embedding model | SBERT vs. multilingual-e5 | Language coverage, embedding quality |
| Fine-tuning | LoRA vs. QLoRA vs. full | Hardware requirements, performance |
| DPO | Optional | Quality improvement vs. schedule risk |
| Evaluation | Automated + human | Thoroughness vs. time/cost |
| Cloud target | AWS only | Scope focus, generalizability |

## Common Pitfalls

- **Scope creep**: Don't add Azure/GCP mid-project. Note as future work.
- **Over-reliance on auto-eval**: Automated metrics miss architectural nuance. Always include human review.
- **Data quality > quantity**: 1000 high-quality dialogues beat 10000 noisy ones.
- **Reproducibility**: Save every seed, config, and dataset version.
- **Schedule risk**: Aug-Sep is packed. Treat DPO as optional, add contingency weeks.
- **Cross-referenced services inflate totals**: A file appears in 1 pillar + N services. Pillar total = unique files; service total counts overlaps. Always verify `unique pillar files == total kept files`.
- **Silent `execute_code` blocks in cron**: When running validation scripts in cron, cron may block `execute_code`. Use `terminal` instead, or set `approvals.cron_mode: approve`.
- When building evaluation benchmarks, use the `benchmark-construction` skill for full workflow.
- **Corpus validation pitfalls**: See `references/corpus-validation-checklist.md` for noise patterns and classification workflow.
- **Benchmark baseline labeling bug**: The benchmark framework hardcodes `baseline_name` in per-query results (all baselines labeled as the first baseline's name). Always verify actual model execution by checking file names, overall scores, and `combined_data.json`. See `references/benchmark-baseline-labeling-bug.md`.
- **BM25IndexBuilder needs `from_dir()` for post-build loading**: `BM25IndexBuilder(dir)` does NOT load an existing index — it creates an empty builder. Use `BM25IndexBuilder.from_dir(dir)` to load for querying. The `.reader` attribute only exists on loaded instances.
- **PEFT incompatible with MLX models**: When fine-tuning MLX models, PEFT's `get_peft_model()` fails because MLX models don't have `get_submodule()`. Use MLX-native LoRA implementation instead. See the fine-tuning section for the pattern.
- **Structured training data validation**: When working with JSON training data (not documents), always validate against schema before formatting. See Stage 2.5 and `references/training-data-schema-validation.md`.
- **mlx_lm.generate parameter quirks**: The `generate()` function does NOT accept `temperature` or `top_p` directly. Pass `sampler` parameter instead, or use `stream_generate()` with proper sampler config.
- **PEFT incompatible with MLX models**: When fine-tuning MLX models, PEFT's `get_peft_model()` fails because MLX models don't have `get_submodule()`. Use MLX-native LoRA implementation instead. See the fine-tuning section for the pattern.
- **mlx_lm.generate parameter quirks**: The `generate()` function does NOT accept `temperature` or `top_p` directly. Pass `sampler` parameter instead, or use `stream_generate()` with proper sampler config.
- **Cross-encoder reloads per query in batch eval**: Instantiating new engine/retranker instances inside an evaluation loop causes fresh model loads each time → timeouts. Disable reranking (`rerank: false`) or reuse a single engine instance.
- **Python 3.14 + pip**: Use `uv pip install --system` or `pip install --break-system-packages` on macOS with Python 3.14+.
- **Config path resolution in subdirectories**: Scripts run from subdirectories (e.g., `retrieval/`) need `ROOT = Path(__file__).resolve().parent.parent` to resolve project-relative paths. Hardcoded relative paths from subdirectories fail.
## Hardware Guidelines

| Task | GPU | VRAM | Time |
|------|-----|------|------|
| Inference (3B Q4) | RTX 3060/Apple M-series | 8GB | ~1-2s/token |
| QLoRA fine-tuning | RTX 3090/4090 or Apple M2/M3 Max | 12-24GB | 2-8 hours |
| Baseline inference | Any | 4GB | ~2-3s/token |
| Embedding/indexing | Any | 4-8GB | Depends on corpus size |

## Model Selection for Baselines

When choosing frontier model baselines (GPT-4o, Claude, Gemini), use the agy CLI to check available models and pick the most recent:

```bash
agy models list  # or similar agy CLI command to enumerate available Gemini models
```

Prefer the most recently released Gemini model for state-of-the-art comparison, or whichever model you have API access to. Always document the exact model version used in evaluation reports.
