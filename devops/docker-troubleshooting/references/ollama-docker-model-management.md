# Ollama Docker Model Management

## Ollama in Docker — Critical Patterns

### Container Execution

Ollama runs as `ollama/ollama:latest` in Docker. The `ollama` CLI is NOT installed on the host — all model operations must go through `docker exec` or the HTTP API.

```bash
# Model operations inside the container
docker exec ollama ollama pull qwen2.5:7b
docker exec ollama ollama list
docker exec ollama ollama show qwen2.5:7b

# Direct API access (works from any context)
curl -s http://10.0.0.7:11434/api/pull -d '{"name":"qwen2.5:7b","stream":false}'
curl -s http://10.0.0.7:11434/api/tags
curl -s http://10.0.0.7:11434/api/show -d '{"name":"qwen2.5:7b"}'
```

### Bridge IP Pattern

Ollama's Docker bridge IP is NOT `127.0.0.1` or `localhost` when accessed from other containers:

```bash
# Find the IP
docker inspect ollama --format '{{.NetworkSettings.IPAddress}}'
# Result: 10.0.0.7 (example — always verify)

# Other containers must use: http://10.0.0.7:11434
# NOT: http://localhost:11434
```

### API vs Library Name Resolution Failure

**Session pattern (2026-08-11):** A model (`oamazonasgabriel/lfm2.5-2.6b`) appeared in `ollama.com/search` results but failed with `pull model manifest: file does not exist` via both `docker exec ollama pull` and the `/api/pull` endpoint.

**Diagnosis flow:**
1. Search for model on `https://ollama.com/search?q=<query>`
2. Extract the model name from the search result URL (e.g., `/library/oamazonasgabriel/lfm2.5-2.6b`)
3. Test with `curl -s "https://ollama.com/library/<name>"` — if it returns HTML (page) instead of model metadata, the model doesn't exist
4. Try alternative namespaces or tags

**Common mismatch examples:**
- `oamazonasgabriel/lfm2.5-2.6b` — search shows it but API says "not found"
- `lfm2.5` exists, `lfm2.5:2.6b` does NOT
- Model families may have different sizes under different namespaces

### Model Blob Cleanup

When `ollama rm` doesn't work (CLI not in PATH), manually remove blob files:

```bash
# Find the model's blob digest
docker exec ollama ollama show lfm2.5:latest 2>/dev/null | grep "sha256"
# Or from API:
curl -s http://10.0.0.7:11434/api/show -d '{"name":"lfm2.5:latest"}' | grep -o 'sha256-[a-f0-9]*'

# Remove the blob
sudo rm -f /root/.ollama/models/blobs/sha256-<digest>
```

## Session Reference: LFM2.5 Model Issue (2026-08-11)

User wanted LFM2.5-2.6B but only `lfm2.5` (8B) and `lfm2.5-thinking` (8B) exist on the Ollama library. The `oamazonasgabriel/lfm2.5-2.6b` namespace from a web search did not resolve on the Ollama server.

Workaround used: Keep the 8B model, optimize with custom parameters (`num_ctx`, `num_batch`, `num_predict`, `temperature`, `top_k`) via a Modelfile wrapper.