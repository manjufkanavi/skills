# Gateway API Reference

## GET /healthz

Returns gateway health and oMLX connectivity status.

**Response:**
```json
{
  "status": "ok",
  "qwen_base_url": "http://127.0.0.1:8000/v1",
  "qwen_backend_model": "Qwen2.5-Coder-3B-Instruct-MLX-8bit",
  "qwen_reachable": true,
  "retriever_loaded": true,
  "models": ["qwen-vanilla", "solvarch-rag"]
}
```

## GET /v1/models

Returns available model IDs (OpenAI-compatible format).

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "qwen-vanilla", "object": "model", "owned_by": "solvarch-demo"},
    {"id": "solvarch-rag", "object": "model", "owned_by": "solvarch-demo"}
  ]
}
```

## POST /v1/chat/completions

Accepts OpenAI-compatible chat completion request.

**Request body:**
```json
{
  "model": "solvarch-rag",
  "messages": [{"role": "user", "content": "query text"}],
  "max_tokens": 200,
  "temperature": 0.0,
  "stream": false
}
```

**Response (non-streaming):**
```json
{
  "id": "chatcmpl-<uuid>",
  "object": "chat.completion",
  "model": "solvarch-rag",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "answer text\n\n---\n### Retrieved evidence\n1. `doc_id=...` ..."},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 0, "completion_tokens": 42, "total_tokens": 42}
}
```

**Response (streaming):** SSE format with `text/event-stream` content type.

**Error responses:**
- `400` — No user question found for RAG retrieval
- `404` — Unknown demo model
- `401` — Invalid or missing API key
- `502` — oMLX backend unreachable or returned error
