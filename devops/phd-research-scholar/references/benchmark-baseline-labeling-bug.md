# Benchmark Baseline Labeling Bug

## The Bug

In the Solvarch benchmark framework (`benchmark/config/benchmark_spec.py`), the `baseline_name` field in per-query result entries is **hardcoded to the first baseline's name** regardless of which model was actually evaluated.

### Evidence

Both `benchmark_results.json` (DeepSeek run) and `benchmark_results_qwen2.5_coder_3b.json` (Qwen2.5 run) contain:
```json
{
  "query_id": "cost-001",
  "baseline_name": "deepseek_v4_flash",   // <-- WRONG for the Qwen2.5 run
  ...
}
```

The Qwen2.5 run scored queries against `Qwen2.5-Coder-3B-Instruct-MLX-4bit` but labeled them as `deepseek_v4_flash`.

### Root Cause

The `run_single_query()` function or the result builder hardcodes `baseline_name` from the first entry in the baselines config rather than accepting it as a parameter.

### Detection Method

Always verify actual model execution by checking:
1. **Model version in scores** — Qwen2.5 typically scores lower (0.3-0.6) vs DeepSeek (0.6-0.8)
2. **Report metadata** — The `combined_data.json` file has separate `ds` and `qw` keys with correct overall scores
3. **File naming** — `*_qwen2.5_coder_3b.json` files contain Qwen2.5 runs despite wrong baseline_name
4. **Git commit messages** — Look at the commit that created the file for the actual model used

### Workaround

When scoring per-query results:
- Don't rely on `baseline_name` field — use the **filename** and **overall score ranges** to identify which baseline the data belongs to
- Always cross-reference with `combined_data.json` or separate report files
- For future benchmark runs, fix the scorer to pass `baseline_name` dynamically

## Impact

When comparing baselines, the `baseline_name` field in per-query results is unreliable. Use report-level metadata and file naming conventions instead.
