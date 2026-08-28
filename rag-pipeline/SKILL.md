---
name: rag-pipeline
description: Run RAG pipelines with local models — retriever + gateway + generator patterns, Solvarch-style hybrid retrieval (BM25 + dense + RRF + cross-encoder rerank).
---

# RAG Pipeline Patterns

## Quick Start — Gateway Pattern

When a project exposes a RAG gateway (FastAPI) that wraps a retriever + local model:

1. **Start the gateway** — set `PYTHONPATH` to project root so imports resolve:
   ```bash
   cd /path/to/project
   PYTHONPATH=. uvicorn app.openai_gateway:app --host 127.0.0.1 --port 8008
   ```

2. **Call with model ID** — the gateway exposes model IDs (not raw model names):
   ```bash
   # Vanilla (no context)
   curl -s http://127.0.0.1:8008/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"qwen-vanilla","messages":[{"role":"user","content":"<query>"}],"max_tokens":200}'

   # RAG (retrieves context first)
   curl -s http://127.0.0.1:8008/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"solvarch-rag","messages":[{"role":"user","content":"<query>"}],"max_tokens":200}'
   ```

3. **Verify** — check `/healthz` endpoint or `/v1/models` for available model IDs.

## Python One-Liner (No Gateway)

When you need to run retriever + generator directly without the gateway:

```bash
cd /path/to/project
python3 - <<'PY'
import httpx
from retrieval.retriever_raft import RaftRetriever
from generation.generator_omlx import build_prompt

# 1. Retrieve passages
r = RaftRetriever("data/corpus_index.jsonl")
passages = [p["text"] for p in r.retrieve("your query here", top_k=5)]
print(f"Retrieved {len(passages)} passages")

# 2. Generate with context via local model
resp = httpx.post("http://127.0.0.1:8000/v1/chat/completions", json={
    "model": "Qwen2.5-Coder-3B-Instruct-MLX-8bit",
    "messages": build_prompt("your query here", passages),
    "max_tokens": 256, "temperature": 0.0,
})
print(resp.json()["choices"][0]["message"]["content"])
PY
```

## Key Patterns

### Retriever API
```python
r = RaftRetriever("data/corpus_index.jsonl")
results = r.retrieve("query", top_k=5, pillar="reliability")
# Returns list[dict] with: passage_id, doc_id, pillar, services, score, preview
```

### Prompt Building
```python
from generation.generator_omlx import build_prompt
messages = build_prompt(question, passages)
# Returns [{"role": "system", ...}, {"role": "user", "content": "Context:\n...\n\nQuestion: ..."}]
```

### Gateway Config
- `QWEN_BASE_URL` — oMLX endpoint (default `http://127.0.0.1:8000/v1`)
- `SOLVARCH_TOP_K` — number of retrieved passages (default 5)
- `SOLVARCH_RAG_TIMEOUT_SECONDS` — RAG pipeline timeout (default 180)

## Pitfalls

- **PYTHONPATH must include project root** — otherwise `from generation.generator_omlx import build_prompt` fails with `ModuleNotFoundError`.
- **Gateway venv may not exist** — check `demo/.venv/bin/python` before running `setup_demo_env.sh`. If deps are already system-installed, skip the venv.
- **Corpus file must exist** — `data/corpus_index.jsonl` is required by the retriever. Verify it exists before starting.
- **oMLX must be running first** — the gateway calls oMLX synchronously; if oMLX is down, the gateway returns 502.
- **RAG timeout is long (180s)** — cross-encoder reranking is slow on CPU. Don't set a short timeout.

## References

- `references/solvarch-architecture.md` — Solvarch project architecture details
- `references/gateway-endpoints.md` — Gateway API reference
