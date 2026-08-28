# Solvarch Training Report Template

**Date:** YYYY-MM-DD  
**Model:** BaseModel + LoRA  
**Project:** Solvarch — AWS Architecture Fine-Tuning  

---

## 1. Training Configuration

| Parameter | Value |
|-----------|-------|
| Base Model | [model name] |
| Training Data | [dataset description] |
| LoRA Rank | [rank] |
| LoRA Alpha | [alpha] |
| LoRA Dropout | [dropout] |
| Learning Rate | [lr] |
| Batch Size | [batch_size] |
| Max Sequence Length | [seq_len] |
| Epochs | [epochs] (total_steps steps) |

---

## 2. Training Metrics

| Epoch | Steps | Train Loss | Eval Loss | Perplexity | Time (s) |
|-------|-------|------------|-----------|------------|----------|
| 1 | — | — | — | — | — |
| 2 | — | [loss] | — | — | [time] |
| 3 | [steps] | [loss] | [eval_loss] | [ppl] | [time] |

**Best Eval Loss:** [value]  
**Final Train Loss:** [value]  

---

## 3. Benchmark Results

### 3.1 Base vs Fine-Tuned Comparison

| Metric | Base Model | Fine-Tuned | Improvement |
|--------|-----------|------------|-------------|
| Validation Loss | [base_loss] | [ft_loss] | [+/- delta] |
| Perplexity | [base_ppl] | [ft_ppl] | [+/- delta] |

### 3.2 Interpretation

[Comment on whether improvement is significant, expected for LoRA rank, domain adaptation quality, etc.]

---

## 4. Validation Results

### 4.1 Sample Inference Testing

| Sample | Prompt | Quality | Services Found | Well-Architected Pillars |
|--------|--------|---------|----------------|--------------------------|
| 1 | [prompt summary] | [rating] ([score]) | [count] | [X/6] |
| 2 | [prompt summary] | [rating] ([score]) | [count] | [X/6] |
| 3 | [prompt summary] | [rating] ([score]) | [count] | [X/6] |

### 4.2 Aggregate Metrics

| Metric | Value |
|--------|-------|
| Average Quality Score | [avg] |
| Average Well-Architected Coverage | [avg]% |
| Average AWS Services per Response | [avg] |
| Quality Distribution | [X Excellent, Y Good, Z Needs Improvement] |

### 4.3 Well-Architected Pillar Coverage

| Pillar | Coverage Rate |
|--------|---------------|
| Security | ✅/⚠️ |
| Reliability | ✅/⚠️ |
| Performance Efficiency | ✅/⚠️ |
| Operational Excellence | ✅/⚠️ |
| Cost Optimization | ✅/⚠️ |
| Sustainability | ✅/⚠️ |

---

## 5. Conclusions

1. [Finding 1]
2. [Finding 2]
3. [Finding 3]
4. Future improvements:
   - [Suggestion 1]
   - [Suggestion 2]

---

## 6. Artifacts

- Training Script: [path]
- Benchmark Script: [path]
- Sample Generation: [path]
- Validation Script: [path]
- Training Config: [path]
- Benchmark Results: [path]
- Sample Outputs: [path]
- Validation Report: [path]
