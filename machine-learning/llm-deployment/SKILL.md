---
name: llm-deployment
description: Manage local LLM serving (Ollama), web UIs (OpenWebUI), and their debugging on a single VM. Covers model variants, performance tuning, deployment with nginx/cloudflared routing.
---

# LLM Deployment & Debugging

Manage local LLM serving (Ollama), web UIs (OpenWebUI), and their debugging on a single VM. Covers model variants, performance tuning, deployment on VMs with nginx/cloudflared routing.

## Ollama Model Management

### Create a local model variant from a base model
```
# 1. Write Modelfile locally, not inside container (heredocs fail through SSH)
# 2. Use docker cp to get it into the container
cat > /tmp/modelfile <<'EOF'
FROM base-model:latest
TEMPLATE {{ .Prompt }}
PARAMETER num_ctx 4096
PARAMETER num_batch 512
PARAMETER num_predict 512
PARAMETER temperature 0.5
PARAMETER top_k 50
PARAMETER repeat_penalty 1.05
PARAMETER num_thread 8
EOF
docker cp /tmp/modelfile ollama:/tmp/modelfile
docker exec ollama ollama create custom-variant -f /tmp/modelfile
```

**CRITICAL — TEMPLATE directive**: Must be a SINGLE LINE in Modelfile. Multi-line templates fail with `Error: no Modelfile or safetensors files found`. Do NOT use heredocs inside `docker exec` — always use `docker cp`.

### PERFORMANCE: The num_ctx bottleneck
The single biggest latency factor is `num_ctx`. Default Ollama auto-sets based on available VRAM (often 128,000). On CPU-only machines:

| num_ctx | Impact |
|---------|--------|
| 128000 | ~5s load time, massive memory, slow prefill |
| 8192 | ~3s load, good balance for most use |
| 4096 | ~2s load, fastest, sufficient for most chat |

**Rule**: Set `num_ctx` to the minimum your use case needs. Never leave the default on CPU.

### Delete a model
```
docker exec ollama ollama rm model-name
```

## Ollama Docker Restart & Migration

### Ollama 0.32+ directory structure change
```
# OLD structure (pre-0.32):
/root/.ollama/models/blobs/      ← GGUF files
/root/.ollama/models/manifests/  ← manifest files

# NEW structure (0.32+):
/root/.ollama/blobs/            ← GGUF files
/root/.ollama/manifests/        ← manifest files
```

If migrating to a new Ollama version, models appear as empty (`ollama list` returns nothing) because the new version looks in `models/` but the data is at the top level. **Fix**:
```
docker exec ollama bash -c '
  mkdir -p /root/.ollama/models/manifests/registry.ollama.ai/library
  cp -r /root/.ollama/manifests/registry.ollama.ai/library/* /root/.ollama/models/manifests/registry.ollama.ai/library/
  cp /root/.ollama/blobs/* /root/.ollama/models/blobs/ 2>/dev/null
'
docker restart ollama
```

### Ollama 0.32+ command change
The container entrypoint changed from `server` to `serve`:
```
# OLD:  ollama/ollama:latest  server
# NEW:  ollama/ollama:latest  serve
```

### Running with optimization env vars
```
docker run -d --name ollama --restart unless-stopped \
  -v /home/mkanavi/ollama_models:/root/.ollama \
  -p 11434:11434 \
  -e OLLAMA_HOST=0.0.0.0:11434 \
  -e OLLAMA_ORIGINS=* \
  -e OLLAMA_KEEP_ALIVE=-1 \
  -e OLLAMA_NUM_THREADS=8 \
  ollama/ollama:latest serve
```

## OpenWebUI Integration

### Docker networking: OpenWebUI ↔ Ollama
See `references/docker-networking-checklist.md` for the full diagnostic procedure when OpenWebUI cannot reach Ollama. Key pitfall: using the host's external IP (e.g., `http://192.168.0.118:11434`) as `OLLAMA_BASE_URL` — the container can't route back to that IP. Use the Ollama container's bridge IP instead (e.g., `http://10.0.0.7:11434`), or put both containers on a user-defined network.

### Model selection
After creating a custom variant, set it as the default in OpenWebUI admin settings. The model will appear in the dropdown automatically.

### "Does not support tools" message
**Root cause**: The GGUF model's metadata includes `capabilities: [completion, tools, thinking]`. OpenWebUI detects `tools` and sends tool definitions. The model doesn't implement actual tool-calling → UI shows notification.

**Fix**: This is a UI notification only — the model responses are correct. Disable tools via OpenWebUI Settings → Tools → Integrations, or configure per-model in Admin Panel → AI → Models.

### The `PARSER lfm2-thinking` issue (legacy)
Some models embed `PARSER lfm2-thinking` in their template layer, routing all streaming output to a `thinking` field instead of `content`. OpenWebUI's renderer only reads `content`. Fix by creating a clean local variant with `TEMPLATE {{ .Prompt }}` that overrides the template. The thinking capability stays in GGUF metadata but the content field will still be populated.

## Docker Networking: OpenWebUI → Ollama Connectivity

### The `OLLAMA_BASE_URL` pitfall
When the OpenWebUI container cannot reach Ollama, the most common cause is using the **host's external IP** (e.g., `http://192.168.0.118:11434`) as the `OLLAMA_BASE_URL`. From inside a Docker container, this external IP may be unreachable because the container's network can't route back to the host's external interface.

**Diagnose**:
```bash
# Get Ollama container IP on the bridge network
docker inspect ollama --format '{{range .NetworkSettings.Networks}} {{.IPAddress}}{{end}}'
# Expected: 10.0.0.7 (or similar)

# Test reachability from inside OpenWebUI
docker exec open-webui curl -s --connect-timeout 3 http://10.0.0.7:11434/api/tags
```

**Fix options**:
1. **Use Ollama's bridge IP** (quick fix):
   Recreate open-webui with `-e OLLAMA_BASE_URL=http://10.0.0.7:11434` (IP from above).
2. **Use a user-defined network** (cleaner, long-term):
   ```bash
   docker network create iacgenie
   docker network connect iacgenie ollama
   docker network connect iacgenie open-webui
   # Then OLLAMA_BASE_URL=http://ollama:11434 works (DNS resolves on user-defined networks)
   ```

### Docker bridge DNS limitation
**The default `bridge` network does NOT support cross-container DNS resolution** between containers on different bridge subnets or when created on different Docker network configurations. `http://ollama:11434` fails with `Could not resolve host: ollama` even when both containers appear on `bridge`.

**Rule**: Use a user-defined network (`docker network create`) for multi-container LLM stacks, or use the bridge IP directly.

### Recreate container with correct env
If OLLAMA_BASE_URL is baked into a running container:
```bash
docker stop open-webui && docker rm open-webui
docker run -d --name open-webui -p 4000:8080 \
  -e OLLAMA_BASE_URL=http://10.0.0.7:11434 \
  -e USE_OLLAMA_DOCKER=false \
  -e ENABLE_SIGNUP=false \
  ghcr.io/open-webui/open-webui:main
```

## Hermes Gateway + Local LLM Integration

### Config key pitfall: `base_url` vs `inference_url`
The Hermes config.yaml model resolution reads `model.default.base_url` — **NOT** `inference_url`. Using `inference_url` leaves the endpoint empty, so the ollama/custom runtime can never resolve → "Provider authentication failed".

**Diagnose**:
```bash
# Quick check: does the runtime see the base_url?
python3 -c "
import sys; sys.path.insert(0, '/home/mkanavi/.hermes/venv/lib/python3.12/site-packages')
from hermes_cli.config import load_config
c = load_config()
print('base_url:', c.get('model', {}).get('default', {}).get('base_url'))
"
# If empty → the URL key is wrong
```

**Fix**: Change the key in config.yaml:
```yaml
# WRONG (inference_url is silently ignored)
model:
  default:
    provider: ollama
    model: LFM2.5-1.2B-Instruct:32k
    inference_url: http://localhost:11434/v1

# CORRECT (base_url is read by the runtime)
model:
  default:
    provider: ollama
    model: LFM2.5-1.2B-Instruct:32k
    base_url: http://localhost:11434/v1
```

**Why this happens**: The Hermes runtime resolution in `hermes_cli/runtime_provider.py:_get_model_config()` calls `cfg.get("base_url")`. The `inference_url` key exists in some generated configs but is never read by the resolution code. Aliases like `ollama`, `vllm`, `llamacpp` all resolve to the `"custom"` provider, which requires `base_url` to build the runtime.

### Restart gateway after config changes
After changing config.yaml, the running gateway process reads stale config. Kill and restart:
```bash
# Find and kill all gateway processes
ps aux | grep hermes_cli.main | grep -v grep | awk '{print $2}' | xargs kill
sleep 3
cd /home/mkanavi && nohup /home/mkanavi/.hermes/venv/bin/python -m hermes_cli.main gateway run > /home/mkanavi/.hermes/logs/gateway_stdout.log 2>&1 &
```

### Verify LLM call actually goes through
Check the gateway log for `api_calls=N` (N > 0 means real LLM call was made):
```
grep "api_calls=" /home/mkanavi/.hermes/logs/gateway.log | tail -3
# WRONG: api_calls=0 response=73 chars  ← fallback error, no LLM call
# RIGHT: api_calls=2 response=120 chars  ← actual model was called
```

## Common Pitfalls

1. **`docker cp` + SSH heredoc = double escaping nightmare**. Always write files on the host, then `docker cp`.
2. **`ollama create FROM X` re-downloads X** if the layer hash doesn't match. This happens when the Ollama version changes and the blob digest lookup fails.
3. **`OLLAMA_NUM_THREADS=8`** is the env var, not a Modelfile parameter — but Modelfile also supports `PARAMETER num_thread 8`. Set both for safety.
4. **Ollama volume mount must be to `/root/.ollama`** not `/root/.ollama/models` for the 0.32+ structure. If mounting to `/root/.ollama/models`, the blobs/manifests are found at wrong relative paths.
5. **Container exited with `Error: unknown command "server"`** — the command is now `serve`, not `server`.
6. **Stale model references linger after deletion**. After deleting a model, Ollama may log `failed to refresh model list cache` warnings for the old model. Run `docker exec ollama ollama rm <old-name>` to fully clear the reference.
7. **OMLX local server needs `Content-Type: application/json`**. Calling `127.0.0.1:1234/v1/chat/completions` with raw `urllib` (no client lib) fails with `HTTP 422: body: Input should be a valid dictionary or object to extract fields from` even though the JSON body is valid. Fix: pass `headers={"Content-Type": "application/json"}`. See `references/omlx-server-quirks.md`.


## Local Inference Serving Backends (absorbed sibling skills)

> The sibling skills below have been consolidated into this umbrella. Their full workflows remain available in the archived package at `~/.hermes/skills/.archive/<name>/`.

### `llama-cpp` — GGUF / llama.cpp inference (was `mlops/inference/llama-cpp`)
Local llama.cpp inference over GGUF checkpoints: quantization (Q4_K_M, Q5_K_M, Q8_0), context/quantization trade-offs, hub discovery, quantization, server, and troubleshooting. See archived `mlops/inference/llama-cpp/`.

### `serving-llms-vllm` — High-throughput vLLM serving (was `mlops/inference/vllm`)
vLLM serving pipeline: PagedAttention throughput, continuous batching, quantization (AWQ/GPTQ/Q8), structured output (JSON/schema), server deployment. See archived `mlops/inference/vllm/`.

### `ollama-model-compatibility` — Ollama model quirks (was `mlops/ollama-model-compatibility`)
Ollama model parsing quirks, variant creation (Modfile), LFM2 parser fix, and UI compatibility. See archived `mlops/ollama-model-compatibility/`.

### `huggingface-hub` — Model acquisition (was `mlops/huggingface-hub`)
hf CLI: search/upload/download models & datasets, local-dir download. See archived `mlops/huggingface-hub/`.

### `mlx-local` — Local MLX model demo (vanilla vs RAG)
Side-by-side demo of a local MLX model: one model, two prompt modes (vanilla vs RAG), tiny backend + two-column UI. HF cache gotchas (snapshot path, incomplete download → "No safetensors found") and venv setup. See `references/mlx-local-demo.md`.
