---
name: retrieval-engineering
description: >
  Build, evaluate, and optimize hybrid retrieval pipelines — BM25, dense vector
  search (FAISS), rank fusion (RRF), cross-encoder reranking, and metadata filtering.
  Covers index building, query engines, evaluation metrics, and performance tuning.
version: 1.0.0
tags: [retrieval, rag, bm25, faiss, reranking, ranking, search]
---

# Retrieval Engineering — Hybrid Retrieval Pipelines

Complete workflow for building, evaluating, and tuning hybrid retrieval pipelines
combining sparse (BM25) and dense (embedding-vector) retrieval with rank fusion and
reranking.

## Workflow

### 1. Corpus Preparation

1. **Source**: Gather all documents (markdown, PDFs, etc.) into a single directory.
2. **Clean**: Remove noise files (CLI refs, SDK docs, stubs, glossaries) — use corpus
   validation scripts if available (e.g., `scripts/corpus_validate.py`).
3. **Metadata**: Build a category index mapping each document to pillars, services,
   tags, or other filterable attributes.
4. **Index directory**: Create `indexes/bm25/` and `indexes/faiss/` subdirectories.

### 2. Build Indexes

**BM25 (Whoosh)** — lexical keyword retrieval:

```python
from retrieval.index_builder import BM25IndexBuilder
from retrieval.index_builder import CorpusReader

reader = CorpusReader("corpus/", "category_index.json")
bm25 = BM25IndexBuilder("indexes/bm25")
count = bm25.build(reader)  # returns doc count
```

**Dense (FAISS + sentence-transformers)** — semantic vector retrieval:

```python
from retrieval.index_builder import DenseIndexBuilder

dense = DenseIndexBuilder("indexes/faiss", "all-MiniLM-L6-v2")
dense.build(reader)  # embeds + stores in FAISS
```

Key models:
- **`all-MiniLM-L6-v2`** (384-dim, 22M params) — fast, good for Apple Silicon
- **`all-mpnet-base-v2`** (768-dim) — better quality, larger
- **`BAAI/bge-small-en-v1.5`** — strong multilingual option

### 3. Load Indexes for Querying (CRITICAL)

**Never recreate an index builder without calling `build()`** — it only exists during
the build step. After building, load with `from_dir()`:

```python
# WRONG — creates empty builder, no index loaded:
bm25 = BM25IndexBuilder("indexes/bm25")
# bm25.reader does not exist

# CORRECT — loads existing index for querying:
bm25 = BM25IndexBuilder.from_dir("indexes/bm25")
# bm25.reader exists and is searchable

# For dense index:
dense = DenseIndexBuilder.load("indexes/faiss", "all-MiniLM-L6-v2")
```

### 4. Build Retrieval Engine

Combine BM25 + Dense with Reciprocal Rank Fusion (RRF):

```python
from retrieval.engine import HybridRetrievalEngine

engine = HybridRetrievalEngine()
results = engine.retrieve(
    query="multi-AZ RDS failover",
    pillar="reliability",        # optional metadata filter
    services=["RDS"],             # optional metadata filter
    k=10                          # number of results
)
```

### 5. Cross-Encoder Reranking (Optional)

For higher precision on top-K results:

```python
# In config.yaml:
# retrieval:
#   rerank: true
```

**Performance note**: Cross-encoders are slow (~200ms/query). For batch evaluation
(100+ queries), disable reranking or cache the reranker to avoid reloading the model
per query.

### 6. Evaluate Retrieval Quality

Use standard IR metrics. See `references/evaluation-methodology.md` for evaluation
patterns. Typical metrics:

| Metric | What it measures |
|---|---|
| **MRR@10** | Mean reciprocal rank — is the top result relevant? |
| **NDCG@10** | Normalized discounted cumulative gain — is ranking quality good? |
| **Recall@100** | Fraction of all relevant docs found in top 100 |
| **Precision@10** | Fraction of top-10 results that are relevant |
| **MAP@10** | Mean average precision across top 10 |

**Self-retrieval eval** (quick sanity check): use each document's title as query,
measure how well the system retrieves that same document and its pillar-peers.

### 6b. Honest Held-Out Benchmarking

Self-retrieval and curated queries can be **leaky** — if the query is derived FROM the
document (title + summary + services concatenated), the numbers are inflated (observed leaky
MRR ≈ 0.55–1.0) and say nothing about real queries. For a realistic score:

1. **Reuse** pre-built indexes (no rebuild): `BM25IndexBuilder.from_dir(<dir>)` and
   `DenseIndexBuilder.load(<dir>, <model>)`.
2. **Query set** = external natural-language questions (e.g. `Query:` lines from
   fine-tuning JSONL, held-out user prompts, hand-written questions) — NOT derived from
   corpus docs.
3. **Gold** = corpus docs that name the services/entities the query references (defined from
   the external query, not from corpus metadata).
4. Compute MRR@10, MAP@10, Precision@10, NDCG@10, Recall@100, and **hit_rate@10** (fraction of
   queries retrieving ≥1 relevant doc in top-10 — most discriminative signal when gold sets
   are broad).
5. **Run a coverage-gap check**: count fine-tune/reference services the corpus does not index;
   if many have zero docs, recall is capped by coverage, not retrieval quality.

See `references/honest-benchmarking.md` for the full technique and a worked example.

### Document-QA datasets (oracle document as gold)

Some datasets pair each query with its **oracle document** and an **oracle answer** (e.g. the
RAFT AWS Well-Architected dataset: 1,671 `(question, oracle_context, cot_answer)` triples).
This is the ideal input for an honest benchmark — and it is *not* leaky, because the query is
a comprehension question independent of how the corpus was chunked.

- Treat each oracle document (deduplicated, chunked) as the corpus; treat each **question** as
  a held-out query and its **oracle document** as the single gold. Compute MRR@10 / hit_rate@10
  / NDCG@10 — these now measure *real* retrieval, not self-retrieval.
- The golden **answer** is usually a quoted span inside `cot_answer` (RAFT wraps it in
  `##begin_quote## … ##end_quote##`). Extract that span, don't grade the full chain-of-thought.
- Grade answers with BERTscore / entity/fact match + pillar coverage, plus a grounding check
  that no service/claim in the answer is unsupported by the retrieved context.
- Worked schema + fields: see `references/raft-aws-wellarchitected-honest-benchmark.md`.

### 7. Tune

Iterate on these parameters:
- **k_sparse / k_dense** — how many candidates each retriever provides
- **k_fusion (RRF constant)** — rank aggregation window (default 60)
- **k_final** — final results returned
- **Embedding model** — swap for better semantic coverage
- **rerank** — toggle cross-encoder for precision vs. latency tradeoff

## File Structure Template

```
retrieval/
├── __init__.py
├── config.yaml          # All parameters externalized
├── requirements.txt
├── index_builder.py     # BM25 + Dense index builders
├── engine.py            # HybridRetrievalEngine with RRF + rerank
├── evaluate_stable.py   # Fast eval (no reranker)
├── indexes/
│   ├── bm25/            # Whoosh index files
│   └── faiss/           # FAISS index + model
└── evaluation/
    └── evaluation_results.json
```

## Key Pitfalls

- **Leaky self-derived queries**: if the query is built FROM the document it must retrieve
  (title + summary + services concatenated), the benchmark is leaky — the system trivially
  retrieves the source doc, inflating MRR/NDCG/Precision (~0.55–1.0) while measuring nothing
  about real queries. Always validate with EXTERNAL held-out queries (see
  `references/honest-benchmarking.md`).
- **BM25IndexBuilder needs `from_dir()` to load existing indexes**: `BM25IndexBuilder(dir)`
  creates a builder but doesn't open an existing index. Use `BM25IndexBuilder.from_dir(dir)`
  for post-build querying. The `.reader` attribute only exists on loaded instances.
- **Cross-encoder reloads per query**: If you instantiate a new engine (or reranker)
  inside a batch evaluation loop, the model loads fresh each time → timeouts. Either
  disable reranking (`rerank: false` in config) or reuse a single engine instance.
- **Python 3.14 + pip**: Use `uv pip install --system` or `pip install --break-system-packages`
  on macOS with Python 3.14+ (system-managed Python).
- **Whoosh 2.7.4 `writer.commit()` returns None**: Check `ix.doc_count()` instead to
  verify documents were indexed.
- **Config path resolution**: Scripts run from subdirectories (e.g., `retrieval/`) need
  `ROOT = Path(__file__).resolve().parent.parent` to resolve project-relative paths.
  Hardcoding `"markdown/corpus"` from `retrieval/` fails. Always resolve against `__file__`.

## References

- `references/evaluation-methodology.md` — Evaluation patterns: self-retrieval vs. curated
  queries, metric interpretation, and common evaluation setups
- `references/honest-benchmarking.md` — Honest held-out benchmarking: leaky-self-query pitfall,
  reuse pre-built indexes, external-query gold, coverage-gap analysis, and metric interpretation
- `references/raft-aws-wellarchitected-honest-benchmark.md` — Worked example: building an honest
  retrieval benchmark from a document-QA dataset (oracle doc as gold). Companion script:
  `scripts/inspect_parquet_schema.py`.

## Reporting Retrieval Results

When presenting retrieval results in a mid-semester or benchmark deck, include:
- IR metrics table (MRR@10, NDCG@10, Precision@10, Recall@100, MAP@10)
- Per-query latency benchmarks (single query, batch eval, with/without reranker)
- Self-retrieval interpretation: perfect precision means target doc is always #1, but limited recall is expected when many docs share the same pillar
- Note when reranking was disabled and what improvement cross-encoder would add

See `benchmark-construction` skill's `references/midsem-presentation-pattern.md` for the full presentation template.


## Consolidated RAG / Retrieval Workflows (absorbed sibling skills)

> Sibling skills consolidated here; full detail retained in archived packages at `~/.hermes/skills/.archive/<name>/`.

### `rag-corpus-augmentation` — Improve a retrieval pipeline
Measure and improve a retrieval / RAG pipeline by curating and augmenting the corpus. See archived `rag-corpus-augmentation/`.

### `rag-retrieval-audit` — Audit retrieval quality
Audit and improve a retrieval / RAG pipeline's retrieval effectiveness. See archived `rag-retrieval-audit/`.

### `benchmark-construction` — Build evaluation benchmarks
Design, build, and run held-out evaluation benchmarks for a retrieval/RAG system. See archived `benchmark-construction/`.
