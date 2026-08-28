# OMLX Local Inference Server — Script-Calling Quirks

The OMLX local inference server listens on `127.0.0.1:1234` and exposes an OpenAI-compatible `/v1/...` API. It serves several MLX-quantized models (e.g. `Qwen2.5-Coder-3B-Instruct-MLX-8bit`, `Ornith-1.5-35B-A3B-MLX-4bit`, `KAT-Coder-V2.5-Dev-OptiQ-4bit`). List them with `GET http://127.0.0.1:1234/v1/models`.

## The `Content-Type: application/json` requirement

When calling `/v1/chat/completions` with raw `urllib` (no client library), you **must** set the `Content-Type: application/json` request header. Without it the server returns a cryptic:

```
HTTPError 422: {"error":{"message":"body: Input should be a valid dictionary or object to extract fields from","type":"invalid_request_error"}}
```

The request body **is** valid JSON — the server simply fails to parse it without the header. Fix: pass `headers={"Content-Type": "application/json"}` to `urllib.request.Request`.

### Minimal working call
```python
import json, urllib.request
URL = "http://127.0.0.1:1234/v1/chat/completions"
req = {"model": "Qwen2.5-Coder-3B-Instruct-MLX-8bit",
       "messages": [{"role": "system", "content": "..."},
                    {"role": "user", "content": question}],
       "max_tokens": 1024, "temperature": 0.1}
data = json.dumps(req).encode()
r = urllib.request.urlopen(
    urllib.request.Request(URL, data=data,
                           headers={"Content-Type": "application/json"},
                           method="POST"),
    timeout=600)
print(json.loads(r.read())["choices"][0]["message"]["content"])
```

## Practical notes
- Prefer a local OpenAI client (`openai` package, `base_url=http://127.0.0.1:1234/v1`) — it sets the header for you. Use raw `urllib` only when you can't add a dependency.
- Add a **temperature fallback loop** (0.1 -> 0.4 -> 0.7) for short/empty outputs; a 3B model occasionally returns <40 chars.
- Budget ~1-2 s per generation for a 3B 8-bit model on MLX. 60 queries x 2 configs = 120 generations ~5-15 min -> run in the background with progress output and poll.
- Model naming is case/spacing-sensitive (`Qwen2.5-Coder-3B-Instruct-MLX-8bit`) — copy from `/v1/models`, don't guess.
