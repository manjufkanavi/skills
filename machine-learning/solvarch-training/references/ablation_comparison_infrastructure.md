# Solvarch Comparison-Benchmark Infrastructure

The 4-configuration comparison benchmark behind the midsem / local-vs-RAG comparison.

## What exists
- `benchmark/run_ablation.py` — `run_ablation_suite()`. Runs the **same 60 prompts** from `benchmark/data/benchmark_dataset_v1.json` (60 questions: 10 per pillar — cost_optimization / reliability / performance_efficiency / security / operational_excellence / sustainability; basic 18 / intermediate 19 / advanced 23) through 4 configurations + DeepSeek reference:
  1. `vanilla_qwen2.5_coder_3b` — base Qwen, **no RAG, no LoRA** → *local model without RAG*
  2. `rag_only_qwen2.5_coder_3b` — base Qwen + retrieved corpus → *local model with RAG*
  3. `finetuned_qwen2.5_coder_3b` — LoRA adapter, no RAG
  4. `solvarch_hybrid` — LoRA + RAG
  5. DeepSeek-v4-Flash (reference only)
- Metrics per config via `benchmark/evaluation_harness.py` (`evaluate_response_enhanced`): factuality, constraint_satisfaction, hallucination_rate, relevance, weighted_score.
- Output: `benchmark/output/ablation_report.json` (per_baseline + per_query).

## Status (2026-08-21)
- **Never run** — no `ablation_report.json` has ever been produced. The midsem `benchmark_report*.json` only evaluate DeepSeek (`deepseek_v4_flash`) as a single remote baseline (60 queries), not the local-model A/B.

## Blocker: cannot run as-is
- `run_ablation.py` imports `from mlx_lm import load, generate` and `import mlx.core` — **MLX is not installed** in the project venv.
- **No Qwen2.5-Coder-3B base weights** present on disk (only LoRA adapters under `solvarch/trained-model-rag/`).
- The local inference server on `127.0.0.1:1234` (OMLX) serves **Ornith-1.5-35B-A3B-MLX-4bit, Ornith-1.5-9B-MLX-4bit, KAT-Coder-V2.5-Dev-OptiQ-4bit, Kokoro** — **none is Qwen2.5-coder-3B**. The Qwen LoRA adapters therefore can't be applied (base mismatch).

## How to run the local-without-RAG vs local-with-RAG comparison
Two paths:
- **Faithful (all 4 configs):** install MLX + download Qwen2.5-Coder-3B (MLX format), then `python benchmark/run_ablation.py --full` (~60×4 = 240 generations, ~3–4 GB model, long runtime).
- **Fast (core comparison only):** reuse the running OMLX server at `127.0.0.1:1234` and pick a coder model (e.g. `KAT-Coder-V2.5-Dev-OptiQ-4bit`) as "the local model" via an OpenAI-compatible endpoint. Delivers only vanilla(no-RAG) vs rag_only(base+RAG) — ~120 generations. Can't do the LoRA/hybrid configs (Qwen-specific adapters).

## Note on corpus
`run_ablation.py` retrieves via `solvarch/rag_pipeline.py` (`get_retriever` → `BM25Retriever`), which reads `markdown/corpus/*.md` (437 docs) — **not** the augmented `solvarch/training-data/aws_novel_services.json` (2027 json docs). To make the ablation use the "latest corpus", add the 28 novel docs to `markdown/corpus/` (→ ~465 docs) so the retriever picks them up.
