# Solvarch RAG Architecture

## Components

| Component | Port | Role |
|-----------|------|------|
| oMLX | 8000 | Local Qwen model server (OpenAI-compatible) |
| Solvarch Gateway | 8008 | FastAPI gateway exposing `qwen-vanilla` and `solvarch-rag` |
| Open WebUI | 3000 | UI for side-by-side demo |

## Data Flow

```
User Query
    │
    ├─► qwen-vanilla ──► oMLX (direct) ──► Answer
    │
    └─► solvarch-rag ──► RaftRetriever ──► passages
                                    │
                                    ▼
                              build_prompt() ──► oMLX ──► Answer + Evidence
```

## Corpus

- **Source**: `data/corpus_index.jsonl` — 437 AWS Well-Architected design documents
- **Format**: JSONL with `passage_id`, `doc_id`, `text`, `pillar`, `services`, `preview`
- **Also**: `data/raft_records.jsonl` — RAFT training records

## Retrieval Pipeline (RaftRetriever)

1. **Query transforms** — multi-query expansion, step-back abstraction, pillar routing
2. **BM25** — lexical matching on tokenized text
3. **Dense** — `all-MiniLM-L6-v2` embeddings, FAISS inner product
4. **RRF fusion** — k=60 constant, merges sparse + dense scores
5. **Cross-encoder rerank** — `BAAI/bge-reranker-base`, threshold gate at -4.0
6. **Top-K** — default 3 passages returned

## Gateway Endpoints

- `GET /healthz` — health check, shows oMLX reachability and retriever status
- `GET /v1/models` — lists `qwen-vanilla` and `solvarch-rag`
- `POST /v1/chat/completions` — accepts OpenAI-compatible chat format

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `QWEN_BASE_URL` | `http://127.0.0.1:8000/v1` | oMLX endpoint |
| `QWEN_BACKEND_MODEL` | `Qwen2.5-Coder-3B-Instruct-MLX-8bit` | Model name forwarded to oMLX |
| `SOLVARCH_TOP_K` | `5` | Number of retrieved passages |
| `SOLVARCH_RAG_TIMEOUT_SECONDS` | `180` | RAG pipeline timeout |
| `SOLVARCH_DEMO_API_KEY` | `***` | API key for gateway auth |
