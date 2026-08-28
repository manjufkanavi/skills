# Honest Held-Out Retrieval Benchmarking

Use when you need a **realistic** retrieval score (not a sanity-check/self-retrieval number),
or when you must prove whether corpus augmentation / model swaps actually improve retrieval.

## The leaky-self-query pitfall (most important)

If the **query is derived FROM the document it must retrieve** (e.g. title + summary +
services concatenated — "self-derived" queries), the benchmark is leaky: the system trivially
retrieves its own source doc, so MRR/NDCG/Precision look perfect (~0.55–1.0) while measuring
nothing about real queries.

- Observed: markdown self-derived **MRR=1.0**, json self-derived **MRR=0.55** — both inflated.
- **Fix**: use **external held-out queries** — natural-language questions *not* derived from
  any corpus document (e.g. `Query:` lines from fine-tuning JSONL, held-out user prompts, or
  hand-written questions).

## Pipeline (reuse — do not rebuild)

1. **Load pre-built indexes** instead of rebuilding:
   - BM25: `BM25IndexBuilder.from_dir(<whoosh_dir>)`
   - Dense: `DenseIndexBuilder.load(<faiss_dir>, "all-MiniLM-L6-v2")`
2. **Query set** = external natural-language questions (e.g. `Query:` lines extracted from
   fine-tuning JSONL, held-out user prompts, hand-written questions) — *not* from corpus docs.
3. **Gold** = corpus docs that name the services/entities the query references — defined from
   the **external query**, not from corpus metadata. Gold = docs whose service list intersects
   the query's named services.
4. Run hybrid RRF fusion (`k=100`, `rrf_constant=60`) and compute MRR@10, MAP@10,
   Precision@10, NDCG@10, Recall@100, and **hit_rate@10**.

## Coverage-gap analysis (the real ceiling)

Count how many services the fine-tune/reference data references that the corpus does **not**
index. If a large fraction have zero corpus docs, **no retriever can answer them** — this caps
recall regardless of index/model tuning, so measure coverage *before* tuning.

Report: total fine-tune services, corpus-known services, and
`novel_services_zero_corpus_coverage` (count + %). A 94% novel rate means the corpus must be
augmented before retrieval metrics can improve.

## Metric interpretation for honest benchmarks

- **hit_rate@10** (fraction of queries with ≥1 relevant doc in top-10) is the **most
  discriminative** signal when gold sets are broad.
- **MRR@10 / MAP@10** (~0.30–0.35 is realistic for service-centric queries) carry the signal.
- **Recall@100 is bounded by gold-set size** (a common service appears in hundreds of docs, so
  100 retrieved can't cover 800 gold docs) — report it but do NOT read low recall as a retrieval
  failure; it usually means "gold set is bigger than top-100."
- EVAL and TRAIN should agree — if they diverge, suspect split leakage.

## Worked example (illustrative — adapt paths to the project)

```python
from retrieval.index_builder import BM25IndexBuilder, DenseIndexBuilder

# 1. Reuse pre-built indexes (no rebuild)
bm25  = BM25IndexBuilder.from_dir("retrieval/indexes/whoosh_json")
dense = DenseIndexBuilder.load("retrieval/indexes/faiss_json", "all-MiniLM-L6-v2")

# 2. External query set — extract natural-language queries from an external source
queries = [extract_query_line(jsonl_entry) for jsonl_entry in external_jsonl]  # e.g. "Query:" lines

# 3. Gold defined from the external query's named services (not corpus metadata)
gold_for = lambda q: {fid for fid, svcs in corpus_services.items()
                      if set(q.named_services) & set(svcs)}

RRF_CONST, K = 60, 100
for q in queries:
    sparse = bm25.search(q.text, k=K)
    dense_res = dense.search(q.text, k=K)
    scores = {}
    for i, (fid, _) in enumerate(sparse[:K]):
        scores[fid] = scores.get(fid, 0) + 1.0 / (RRF_CONST + i + 1)
    for i, (fid, _) in enumerate(dense_res[:K]):
        scores[fid] = scores.get(fid, 0) + 1.0 / (RRF_CONST + i + 1)
    ranked = [fid for fid, _ in sorted(scores.items(), key=lambda x: -x[1])]
    gold = gold_for(q)
    # compute MRR@10, MAP@10, Precision@10, NDCG@10, Recall@100, hit_rate@10 vs gold
```

## Reproduce

```bash
cd <project_work>
retrieval/venv/bin/python3 retrieval/run_realistic_benchmark.py
# -> retrieval/evaluation/evaluation_results_realistic.json + BENCHMARK_REPORT.md
```
