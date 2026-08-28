# Retrieval Evaluation Methodology

Patterns for evaluating hybrid retrieval pipelines, distilled from production usage.

## Evaluation Setup

### Self-Retrieval (Sanity Check)
Use each document's title (or first 200 chars of content) as a query. Ground truth:
the document itself plus all documents sharing the same pillar/category.

```python
# For each file in corpus:
query = corpus_metadata[file_id].get("title", file_id)
results = engine.retrieve(query, pillar=pillar, services=services, k=200)
# Relevant = all docs with same pillar + self
```

**Pros**: Zero setup, covers full corpus, easy to reproduce.
**Cons**: Title queries may be too narrow; doesn't simulate real user queries.

### Curated Queries (Production-Ready)
Write 10-20 hand-crafted queries per pillar category, each targeting specific
documents with known relevance. Ground truth is explicitly defined per query.

```json
{
  "query_id": "rel-rds-001",
  "pillar": "reliability",
  "query": "How to configure automatic failover for multi-AZ RDS deployments",
  "relevant_docs": ["AWS-RDS-101", "AWS-RDS-105", "AWS-Arch-203"],
  "expected_services": ["RDS", "Route53"]
}
```

**Pros**: Realistic, matches actual user scenarios, produces actionable metrics.
**Cons**: Requires manual effort, may not cover all corpus edges.

## Metric Interpretation Guide

### MRR@10 (Mean Reciprocal Rank at 10)
- **1.0**: Perfect — every query's top result is relevant
- **0.5-1.0**: Good — correct docs usually in top 3
- **0.1-0.5**: Poor — correct docs are buried deeper
- **Interpretation**: "Is the single best answer relevant?"

### NDCG@10 (Normalized DCG at 10)
- **1.0**: Perfect ranking within top 10
- **0.7-1.0**: Good — relevant docs ranked above irrelevant ones
- **0.3-0.7**: Moderate — mixed quality ranking
- **Interpretation**: "Are the best answers listed first?"

### Recall@100
- **0.5-1.0**: Good — most relevant docs found
- **0.2-0.5**: Moderate — many relevant docs missed
- **0-0.2**: Poor — retrieval misses most relevant docs
- **Interpretation**: "Did we find enough relevant docs?"

### Precision@10
- **0.8-1.0**: Excellent — top 10 mostly relevant
- **0.5-0.8**: Good — reasonable signal-to-noise
- **0.2-0.5**: Poor — too much noise in top results

### MAP@10 (Mean Average Precision)
- **1.0**: Perfect — all relevant docs in top 10, perfectly ranked
- **0.5-1.0**: Good precision across top results
- **0-0.5**: Low average precision — missing many relevant docs

## When MRR/NDCG Are 1.0 But Recall Is Low

This is common and not necessarily a bug. It means:
1. The query document ranks #1 (good — BM25 term match + semantic similarity)
2. But many OTHER relevant documents share the same pillar and are not retrieved

**Action**: This is a recall problem, not a precision problem. Consider:
- Increasing k_dense / k_sparse
- Lowering RRF constant to widen the fusion window
- Using a different evaluation method (curated queries with known relevance sets)

## Common Evaluation Mistakes

1. **Using no ground truth**: Without relevance judgments, you can't compute MRR/NDCG
2. **Self-retrieval with no pillar filter**: Evaluates precision but not recall meaningfully
3. **One query per test**: Compute metrics across ALL queries, not just the average of a single result
4. **Skipping per-pillar breakdown**: Aggregate metrics hide per-category weaknesses
