---
name: raft-aws-wellarchitected-honest-benchmark
description: Worked example of building an honest retrieval benchmark from a document-QA dataset (oracle document as gold), using the RAFT AWS Well-Architected dataset (1,671 question/oracle_context/cot_answer triples).
tags: [rag, retrieval, benchmark, honest-eval, raft, aws, document-qa, oracle-gold]
---

# Honest Retrieval Benchmark from a Document-QA Dataset

## Why this matters

Most RAG benchmarks are **leaky**: queries are derived from the corpus docs (title + summary),
so MRR/NDCG sit at 0.55–1.0 and measure nothing about real queries. When a dataset already pairs
each question with its **oracle document** and **oracle answer**, you get a *non-leaky* held-out
benchmark for free — no need to hand-generate queries.

## The RAFT AWS Well-Architected dataset

Source: `https://huggingface.co/datasets/jjovalle99/raft-dataset-aws-wellarchitected`
Single parquet file (`data/train-00000-of-00001.parquet`), ~1,671 rows, all `type: general`.

Row schema (pyarrow):

| field | type | meaning |
|---|---|---|
| `id` | string | e.g. `seed_task_0` |
| `type` | string | task type (all `general` in current split) |
| `question` | string | comprehension question about a whitepaper |
| `context` | struct<sentences, title> | retrieved context; `title` is `placeholder_title`, `sentences` holds the doc text |
| `oracle_context` | string | the full source whitepaper (best retrieval unit) |
| `cot_answer` | string | chain-of-thought golden answer |
| `instruction` | string | `<DOCUMENT>…` prepended doc |

Key structural facts:
- Each question is **paired with exactly one oracle document** → that doc is the gold for retrieval.
- The golden **answer** is the span wrapped in `##begin_quote## … ##end_quote##` inside `cot_answer`
  (which itself starts with `##Reason:`). Extract that span — don't grade the full CoT.
- Task class: **domain reading-comprehension / faithful QA**, not architecture decision support.
  Correctness = "answer supported by + extracted from the oracle doc", not "which service to pick".

## The pipeline (corpus → honest eval → generation)

1. **Parse** the parquet → records `{id, question, oracle_context, answer_span}`.
2. **Dedup** whitepapers by content hash; **chunk** (`~1000` chars, `~160` overlap) → passages.
3. **Index** passages (BM25 + dense `bge-large-en-v1.5` / `all-mpnet-base-v2` → RRF → cross-encoder rerank → gate).
4. **Retrieval eval**: query = each `question`, gold = its `oracle_document`. Report MRR@10,
   hit_rate@10, NDCG@10, recall@20 — because queries are independent of chunking, these are real.
5. **Grounding**: check no service/claim in the model answer is unsupported by retrieved context.
6. **Answer grading**: BERTscore / entity/fact match + pillar coverage vs the extracted answer span.
7. (Optional) **Ablate**: BM25-only, dense-only, hybrid, +rerank, +context-compression.

## Gotchas learned

- `context.title` is a placeholder (`placeholder_title`) — use `oracle_context`, not `context.title`.
- `context.sentences` is nested `list<list<str>>`; flatten and join before indexing.
- `cot_answer` is noisy (reasoning + quoted span). Extract the `##begin_quote##…##end_quote##`
  span; strip `##Reason:` and the `##` markers.
- `instruction` duplicates the doc with a `<DOCUMENT>` prefix (usable, but redundant).

## Companion script

`scripts/inspect_parquet_schema.py` — inspects any HF parquet schema, flattens struct/list fields,
dumps a sample row. Self-heals a missing `pyarrow` by printing the `uv` install command.
