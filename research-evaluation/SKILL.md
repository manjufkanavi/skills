---
name: research-evaluation
description: Critical evaluation framework for assessing ML/AI research projects on academic rigor, demo readiness, and contribution validity. Covers structured assessment of training data, fine-tuning results, evaluation methodology, documentation completeness, and prioritized improvement plans.
version: 1.0.0
tags: [evaluation, review, demo-readiness, research-critique, benchmark-audit]
---

# Research Evaluation — Critical Assessment Framework

Structured evaluation of ML/AI research projects for academic rigor, demo readiness, and contribution validity. Use when reviewing completed or near-completed projects (M.Tech dissertation, PhD progress, project demos).

## Evaluation Dimensions

### 1. Research Framing & Documentation
- Is the problem statement clear, well-scoped, and grounded in literature?
- Does the abstract match what was actually delivered?
- Are there separate abstract, midsem, and final reports? (Identical abstract + midsem = missing work)
- Is the plan of work tracked against actual progress?

### 2. Training Data Quality
- **Volume**: Is the dataset sufficient for the model size? (Rule of thumb: 3B models need 10K+ examples for meaningful adaptation; <1K means the model is essentially still guessing)
- **Distribution**: Check train vs eval set distributions match. Large gaps indicate overfitting risk.
- **Validation**: Were schema validation, authenticity checks, and merge validation performed?
- **Token distribution**: Average token count vs max sequence length — check for truncation issues.

### 3. Fine-Tuning Results Interpretation
- **Loss interpretation**: A cross-entropy loss of ~14 for a 3B model after few epochs means perplexity ~1.29M — the model is still essentially guessing. Loss improvement of <1% is statistically negligible.
- **Convergence**: Train loss ≈ Eval loss = good (no overfitting). Train loss << Eval loss = overfitting risk.
- **LoRA rank**: Rank 16 on a 3B model affects only ~0.05% of parameters. Consider rank 32+ for stronger adaptation.
- **Epoch count**: For LoRA on small datasets (<1000 samples), train for 10-20 epochs, not 3.
- **Perplexity**: Report perplexity alongside loss. Perplexity of 1M+ means the model is barely better than random at next-token prediction.

### 4. Evaluation Methodology Audit
- **Dataset scope**: Does the evaluation cover ALL claimed pillars/domains? (Claiming 6 pillars but evaluating only 3 = 50% scope gap)
- **Sample size**: 20 queries across 3 pillars is insufficient for statistical validity. Minimum 10 per pillar, ideally 60+.
- **Metric design**:
  - Substring matching for factuality is fragile — synonyms and case variations fail
  - Binary decision quality (has trade-off keywords → 0.7, else 0.4) is not a real rubric
  - Hallucination detection must use proper set operations, not substring matching
  - Inverted scores (1.0 = hallucination found) are confusing — document clearly
- **Baseline comparisons**: Are ALL baselines from the spec actually run? (vanilla, RAG-only, fine-tuned, frontier)
- **Ablation studies**: Missing RAG-only vs fine-tuned vs fine-tuned+RAG comparison = incomplete contribution
- **Inter-rater reliability**: If human review is used, report agreement metrics

### 5. Demo Readiness Checklist

**P0 — Critical (must fix before any demo):**
- [ ] No empty/minimal responses — add retry logic, temperature tuning, fallback mechanism
- [ ] Evaluation covers all claimed domains/pillars (not just a subset)
- [ ] All baselines from the spec have been executed and reported
- [ ] No complete query failures (response = "")

**P1 — Important (should fix for strong demo):**
- [ ] Retrain with more epochs or higher LoRA rank if loss is high (>10)
- [ ] Implement and run RAG-only baseline for ablation
- [ ] Fix hallucination detection methodology
- [ ] Add error analysis — what types of queries fail most?

**P2 — Nice to have (distinction-level polish):**
- [ ] Statistical significance testing (confidence intervals, p-values)
- [ ] Proper inter-rater reliability for human review
- [ ] Comprehensive final report with limitations section
- [ ] Distribution analysis of train vs eval sets

### 6. Common Failure Modes (New Additions)

- **Empty response failures**: Model produces zero output on some queries. Causes: temperature too high, generation timeout, insufficient training. Fix: add retry with lower temperature, response validator, fallback to RAG-only mode.
- **Hallucination rates >50%**: Model invents services/concepts not in the training corpus. Fix: improve retrieval grounding, add constraint enforcement, increase training data diversity.
- **Constraint satisfaction <60%**: Model ignores required constraints. Fix: add explicit constraint checking in prompt, use structured output formatting.
- **Training data mismatch**: Eval set has different domain distribution than train set. Fix: stratified splitting, domain-balanced eval set.
- **Missing ablation studies**: No comparison between pipeline components. Fix: always run vanilla, RAG-only, fine-tuned, and combined baselines.
- **Inference failures**: Empty responses, timeout errors, API failures. Fix: add retry logic, timeout handling, fallback models.

### 7. Prioritized Action Plan Template

When presenting findings, use this structure:
1. **Verdict**: Ready / Not ready / Needs X days of work
2. **P0 fixes**: Critical issues that break the demo
3. **P1 fixes**: Important issues that weaken credibility
4. **P2 fixes**: Nice-to-have improvements for distinction
5. **Time estimate**: Realistic timeline for each priority level

### 8. When to Flag Issues

| Issue | Severity | Demo Impact |
|-------|----------|-------------|
| Empty responses on any query | P0 | Critical — evaluator sees model broken |
| Evaluation covers <80% of claimed scope | P0 | Major — incomplete contribution |
| Hallucination rate >50% | P0 | Critical — model untrustworthy |
| Loss >10 with <10 epochs | P1 | Major — model not properly trained |
| Missing ablation studies | P1 | Moderate — incomplete contribution claim |
| No final report | P1 | Major — incomplete documentation |
| Sample size <10 per pillar | P1 | Moderate — weak statistical basis |
| Binary/simple metrics only | P2 | Minor — acceptable for M.Tech level |
| Missing inter-rater reliability | P2 | Minor — expected at M.Tech level |

## Related Skills
- `phd-research-scholar` — For conducting research (this skill evaluates completed work)
- `benchmark-construction` — For building evaluation benchmarks
- `testing` — For running and orchestrating tests

## Support Files
- `references/ml-project-evaluation-patterns.md` — Concrete benchmarks: training loss interpretation for Qwen2.5-Coder-3B, LoRA rank vs parameter coverage, hallucination detection methodology, empty response failure patterns, evaluation dataset sizing guidelines, ablation study checklist, and demo readiness test script.

## Pitfalls
- **Don't confuse loss improvement with quality improvement**: A 0.026% loss reduction is negligible. Look at actual output quality, not just numbers.
- **3 sample outputs ≠ statistical evidence**: Always use the full benchmark for evaluation claims.
- **Empty responses are the #1 demo risk**: An evaluator watching a live demo will see broken model behavior. Fix these first.
- **Evaluation scope must match claims**: If the abstract says "6 pillars" but the benchmark only has 3, this is a major gap.
- **Hallucination rate is inverted**: In the evaluation harness, `hallucination_rate = 1.0` means hallucination WAS found (bad). Document this clearly.
- **Substring matching misses semantic matches**: "AWS Lambda" ≠ "lambda" in lowercase matching. Use proper entity extraction.