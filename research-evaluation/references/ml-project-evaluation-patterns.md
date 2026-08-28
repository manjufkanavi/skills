# ML Project Evaluation — Concrete Patterns & Benchmarks

Session-specific detail from evaluating Solvarch (Qwen2.5-Coder-3B + LoRA fine-tuning for AWS architecture decision support).

## Training Loss Benchmarks for Qwen2.5-Coder-3B

| Training State | Expected Loss Range | Perplexity | Interpretation |
|---------------|---------------------|------------|----------------|
| Random initialization | ~10-12 | ~20K-160K | Model hasn't learned anything |
| After 1-3 epochs on <1K samples | ~14 | ~1.3M | Still essentially guessing |
| After 10+ epochs on 1K samples | ~8-10 | ~3K-22K | Beginning to learn patterns |
| After 20+ epochs on 10K samples | ~4-6 | ~55-403 | Meaningful adaptation |
| After 20+ epochs on 50K+ samples | ~2-4 | ~8-55 | Strong domain adaptation |

**Key insight**: A loss of 14.06 with perplexity 1.29M means the model is barely better than random at next-token prediction. The 0.026% improvement over base is statistically negligible.

## LoRA Rank vs Parameter Coverage

| Rank | Approx. Trainable Parameters | % of 3B Model | Expected Adaptation Strength |
|------|----------------------------|---------------|------------------------------|
| 8 | ~2.4M | 0.08% | Very weak — barely detectable |
| 16 | ~4.8M | 0.16% | Weak — may not converge on small data |
| 32 | ~9.6M | 0.32% | Moderate — reasonable for 1K-5K samples |
| 64 | ~19.2M | 0.64% | Strong — good for 5K+ samples |
| 128 | ~38.4M | 1.28% | Very strong — risk of overfitting on small data |

## Hallucination Detection — Proper Methodology

**Wrong (substring matching):**
```python
if "lambda" in response.lower():
    services_found.append("Lambda")
```
Fails on: "AWS Lambda", "Lambda function", case variations, partial matches.

**Right (set operations with normalization):**
```python
gold_services = {"AWS Lambda", "Amazon API Gateway"}
response_lower = response.lower()
found = {svc for svc in gold_services if svc.lower() in response_lower}
factuality = len(found) / len(gold_services)
```

**Hallucination detection:**
```python
# Check if model recommends services that should NOT be recommended
hallucinated = {svc for svc, reason in rejected_services if svc.lower() in response_lower}
# Return 0.0 if hallucinated (good = no hallucination)
# Return 1.0 if not hallucinated (bad = hallucination found)
```

## Empty Response Failure — Common Causes & Fixes

| Cause | Fix |
|-------|-----|
| Temperature too high (>0.8) | Lower to 0.1-0.3 |
| Generation timeout | Increase max_tokens, add retry |
| Model not trained enough | Retrain with more epochs |
| Input too long for context window | Truncate, use RAG-only |
| API/network error | Add retry with exponential backoff |

**Fix pattern:**
```python
for attempt in range(3):
    response = generate(model, prompt, temperature=0.2)
    if len(response) > 100:  # Minimum sensible response
        break
    temperature = min(temperature + 0.1, 0.5)  # Gradually increase
else:
    response = fallback_rag_only(prompt)  # Fallback
```

## Distribution Mismatch Detection

Check train vs eval set for each dimension:
- Industry distribution (Gini coefficient >0.3 = significant mismatch)
- Service distribution (coverage gap >10% for any service)
- Difficulty distribution (if categorized)
- Pillar/domain distribution (must match claims exactly)

**Fix:** Stratified splitting ensures eval set mirrors train distribution within ±5%.

## Evaluation Dataset Sizing Guidelines

| Model Size | Minimum Queries | Ideal Queries | Queries Per Pillar |
|------------|----------------|---------------|-------------------|
| <1B | 30 | 50 | 5-8 |
| 1-3B | 50 | 100 | 10-15 |
| 7-13B | 100 | 200 | 15-30 |
| 70B+ | 200 | 500 | 30-80 |

**Rule of thumb**: Minimum 10 queries per pillar/domain to get meaningful per-domain statistics.

## Ablation Study Checklist

Every PEFT/RAG project should report:
- [ ] Vanilla base model (no fine-tuning, no RAG)
- [ ] RAG-only (retrieval-augmented, no fine-tuning)
- [ ] Fine-tuned only (no RAG)
- [ ] Fine-tuned + RAG (combined)
- [ ] Frontier model baseline (GPT-4/Claude/strongest available)

Each baseline should be evaluated on the SAME benchmark dataset with the SAME metrics.

## Demo Readiness — Live Test Script

Before any live demo, run these checks:
1. Test every benchmark query — no empty responses
2. Test each pillar at least once
3. Test each baseline at least once
4. Verify all API keys and model endpoints
5. Have a fallback plan (pre-generated responses, RAG-only mode)
6. Time the demo — 20 queries should take <5 minutes
7. Have a "what if it fails" slide ready