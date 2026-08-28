---
name: solvarch-training
description: Solvarch QLoRA fine-tuning project - training pipeline, model checkpoints, evaluation, and benchmarking.
---

# Solvarch QLoRA Fine-Tuning Project

## Project Overview
Fine-tuned Qwen2.5-Coder-3B-Instruct-8bit on AWS architecture dataset using QLoRA via MLX on Apple Silicon.

## Model Locations
- **Base Model:** `/Users/manjunathkanavi/.models/Qwen2.5-Coder-3B-Instruct-8bit/`
- **Trained Checkpoints:** `/Users/manjunathkanavi/.hermes/git_clone_dir/project_work/solvarch/trained-model/`
  - `final/` — Final model adapters (all 72 LoRA layers)
  - `best/` — Best validation checkpoint (eval_loss: 14.0730)
  - `epoch-2/` — End of Epoch 2 checkpoint
  - `epoch-3/` — End of Epoch 3 checkpoint
  - `checkpoint-step-200/` — Step 200 checkpoint
  - `checkpoint-step-400/` — Step 400 checkpoint

## Training Summary
- **Dataset:** 800 train / 200 eval examples (formatted JSONL)
- **Epochs:** 3 (600 total steps, 200 batches/epoch)
- **Batch Size:** 4
- **Learning Rate:** 0.0002 (AdamW)
- **LoRA:** rank=16, alpha=32, dropout=0.05, targets q_proj+v_proj
- **Max Seq Len:** 1024
- **Final Train Loss:** 14.0602
- **Best Eval Loss:** 14.0730
- **Perplexity:** 1,293,634.60
- **Training Time:** ~3,061s total (~51 minutes)
- **Speed:** 0.1 steps/s on Apple Silicon GPU

## Key Files
- Training script: `train_solvarch.py`
- Benchmark script: `scripts/benchmark_model.py`
- Sample inference: `scripts/run_samples.py`
- Validation script: `scripts/validate_outputs.py` (also in skill `scripts/`)
- Training data: `training-data/formatted/train.jsonl` (800) / `eval.jsonl` (200)
- Training logs: `training-logs/run_20260819_184537.log`
- Training summary: `training-logs/training_log.json`

## Templates
- `templates/training_report_template.md` — Fill-in template for training reports
- `templates/model_card_template.md` — Fill-in template for model cards

## Skill Scripts
- `scripts/validate_outputs.py` — Run against `evaluation/sample_outputs.jsonl` to produce `evaluation/validation_report.json`
- `scripts/comprehensive_benchmark.py` — Three-way benchmark (Base vs RAG vs FT) on 200 prompts. Requires `whoosh`, `faiss-cpu`, `sentence-transformers` in venv. See `references/schema_adherence_and_error_analysis.md` for schema test patterns.

## References
- `references/schema_adherence_and_error_analysis.md` — Schema validation patterns, error analysis methodology, benchmark comparison framework
- `references/ablation_comparison_infrastructure.md` — 4-config comparison harness (`run_ablation.py`), why it was never run, and the MLX/Qwen backend blocker

## Data Pipeline
1. Raw data: `training-data/aws_architectures_training_1000.json` (1000 records)
2. Validated: `training-data/aws_architectures_validated.json` (1000 records, 252 contradictions fixed)
3. Merged: `training-data/unified_training.json` (1000 records, 0 issues)
4. Formatted: `training-data/formatted/train.jsonl` (800, 80%) / `eval.jsonl` (200, 20%)
5. Split report: `training-data/formatted/split_report.json`

## How to Run
```bash
cd /Users/manjunathkanavi/.hermes/git_clone_dir/project_work/solvarch
source .venv/bin/activate
python scripts/benchmark_model.py
```

## Evaluation & Benchmarking
### Benchmark Script
- `scripts/benchmark_model.py` — compares base vs fine-tuned model on 200 eval examples
- Runs base model eval (~100s), then fine-tuned eval (~125s), then sample inference
- Produces: loss/PPL comparison table + sample architecture generation

### Comprehensive Benchmark Script (RAG + FT + Base)
- `scripts/comprehensive_benchmark.py` — compares base vs RAG-only vs fine-tuned on 200 prompts
- Three modes: `--mode base`, `--mode rag_only`, `--mode fine_tuned`
- Produces: `trained-model/benchmark_results.json` + `trained-model/benchmark_report.md`

## Demo: Vanilla vs RAG side-by-side
To demo this model comparing a vanilla (retrieval-blind) run vs a RAG (retrieval-augmented) run, side by side, sharing one backend, see `llm-deployment/references/mlx-local-demo.md`. It covers the one-model-two-prompt-modes architecture, the MLX venv setup, and the HF-cache "No safetensors found" gotcha.
## Evaluation & Benchmarking

### Schema Adherence Test (Post-Benchmark)
After running the benchmark, validate output structure against the expected AWS architecture schema:
1. Load `trained-model/benchmark_results.json`
2. For each mode (base/rag_only/fine_tuned), check responses for:
   - `has_overview`: "overview" or "architecture design" or "architecture" in response
   - `has_services`: "service" or "configuration" or "deployment" in response
   - `has_pillars`: "well-architected" or "pillar" or pillar names in response
   - `has_data_flow`: "data flow" or "traffic flow" or "request flow" in response
   - `has_cost`: "cost" or "pricing" or "estimate" or "savings" in response
   - `has_security`: "security" or "encryption" or "compliance" or "iam" in response
3. Compute compliance rate: % of responses with all 6 sections
4. Most common missing sections are typically **data flow** (85%+) and **cost** (5-15%)

### Error Analysis (Post-Benchmark)
Systematic error analysis of benchmark outputs:
1. Load benchmark results JSON
2. For each response, check:
   - Response length < 1000 chars → flag as `short_response`
   - Missing sections → flag as `missing_sections:<list>`
   - Generic template language (high count of "service"/"configuration" keywords) → flag as `generic_template`
   - Missing required services from prompt → flag as `missing_required_services`
3. Aggregate error counts by mode and identify dominant failure modes
4. Compare error rates between base vs fine-tuned to measure improvement

### Schema Adherence Results (2026-08-19)
| Metric | Base | RAG-Only | Fine-Tuned |
|--------|------|----------|------------|
| Full Compliance (6/6) | 5% | 0% | 5% |
| 5/6 Sections | 80% | 80% | 90% |
| Most Common Missing | Data Flow (75%) | Data Flow (100%) | Data Flow (85%) |

### Error Analysis Results (2026-08-19)
| Error Type | Base | Fine-Tuned |
|------------|------|------------|
| Missing data flow | 75% | 85% |
| Generic/template | 20% | 20% |
| Missing cost section | 15% | 5% |
| Missing multiple sections | 5% | 5% |

### Benchmark Results (2026-08-19)
| Metric | Base Model | RAG-Only | Fine-Tuned | FT vs Base |
|--------|-----------|----------|------------|------------|
| Validation Loss | 14.0765 | 14.0765 | 14.0730 | -0.0035 (-0.025%) |
| Perplexity | 1,298,267 | 1,298,267 | 1,293,635 | -4,632 (-0.36%) |
| AWS Services/Response | 14.2 | 14.7 | 13.4 | -0.8 (-5.6%) |
| WA Pillars/Response | 5.2/6 | 5.2/6 | 5.3/6 | +0.1 (+1.9%) |
| Inference Time | 17.5s | 19.3s | 27.3s | +9.8s (+56%) |

**Key insight:** RAG-only outperforms fine-tuned on service coverage (14.7 vs 13.4) and speed (19.3s vs 27.3s). Fine-tuned model's strongest gain is schema compliance (90% at 5/6 sections vs 80% base) and WA pillar coverage (5.3 vs 5.2/6).

## Pitfalls
- **Checkpoint path resolution:** When loading checkpoints in scripts, NEVER use `Path(MODEL_PATH).parent.parent` — MODEL_PATH is `/Users/manjunathkanavi/.models/...` so `.parent.parent` resolves to `/Users/manjunathkanavi` (wrong). Always use `Path(__file__).parent.parent` or import `OUTPUT_DIR` from `train_solvarch.py`.
- **Comprehensive benchmark path resolution:** `scripts/comprehensive_benchmark.py` uses `Path(__file__).parent.parent.parent` to reach project root. If it fails, add explicit `PYTHONPATH` override: `PYTHONPATH=/Users/manjunathkanavi/.hermes/git_clone_dir/project_work:/Users/manjunathkanavi/.hermes/git_clone_dir/project_work/retrieval:. .venv/bin/python scripts/comprehensive_benchmark.py`
- **Missing dependencies:** The comprehensive benchmark requires `whoosh`, `faiss-cpu`, and `sentence-transformers` in the solvarch venv. Install with: `pip install whoosh faiss-cpu sentence-transformers`
- **Benchmark time:** Full benchmark takes ~230s (base eval ~100s + fine-tuned eval ~125s + inference). Plan accordingly.
- **Memory usage:** Peak ~5.6 GB during model loading. Ensure sufficient RAM.
- **JSON_CORPUS hardcoded-index bug (realistic benchmark):** `retrieval/run_realistic_benchmark.py`'s `load_corpus_services()` reads only `JSON_CORPUS[0]` and `JSON_CORPUS[1]` (hardcoded indices), so adding a third corpus file (e.g. augmented `aws_novel_services.json`) does nothing — new docs never count as gold and metrics don't move. Fix: iterate **all** files in `JSON_CORPUS` (loop over the list) instead of indexing the first two.
- **Service-name normalization:** when adding corpus docs, normalize `primary_aws_services` to clean canonical names (strip version/parenthetical suffixes like `AppStream 2.0`, `Elastic Container Service (ECS)`, `/ Route 53`) so they match the service names the benchmark queries reference — otherwise augmented docs can't become gold and the coverage gap won't shrink.

## Known Issues
- Perplexity very high (1.29M) - expected for this data type
- Gradient norm consistently 0.0 - may indicate LoRA not updating correctly
- Training speed ~0.1 steps/s (250s/step) - slow but functional
