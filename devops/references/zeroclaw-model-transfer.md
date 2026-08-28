# Large Model Transfer Patterns

Patterns for transferring model files (GGUF, Safetensors, etc.) between Mac and remote VM when internet bandwidth is constrained.

## The Problem

SSH-based transfers (SCP, rsync over SSH) between Mac and remote VM use internet bandwidth, which is often severely throttled (~100KB/s). For model files (500MB–6GB), this means 1–2+ hours.

## Strategy 1: LAN HTTP Server (Mac → VM)

When Mac and VM are on the same local network (e.g., 192.168.0.x):

```bash
# On Mac: serve the model directory over HTTP
cd ~/path/to/models && python3 -m http.server 8765

# On VM: download via LAN (expected 100+ MB/s)
wget -O /tmp/model.gguf 'http://192.168.0.120:8765/model-file.gguf'
```

**Caveats:**
- macOS firewall may block inbound connections → check connection resets
- Use `curl` from VM for testing: `curl -I http://192.168.0.120:8765/`
- If connection resets, macOS firewall is blocking — use Strategy 2

## Strategy 2: Direct Download on VM

When internet bandwidth on the VM is better than the Mac→VM SSH path:

```bash
# Install huggingface CLI on VM
pip3 install --user --break-system-packages huggingface-hub
~/.local/bin/hf download <repo> <file> --local-dir /tmp/

# Or use wget directly (HuggingFace uses AWS CloudFront)
wget -O /tmp/model.gguf 'https://huggingface.co/<repo>/resolve/main/<file>'
```

**Notes:**
- HuggingFace uses AWS CloudFront CDN → sometimes faster than direct GitHub/raw transfers
- `hf` CLI is the recommended tool (not deprecated `huggingface-cli`)
- Verify model exists first: `~/.local/bin/hf list-repo-files <repo>`

## Strategy 3: Ollama Native Pull (Fastest)

If the model is available on the Ollama library:

```bash
docker exec ollama ollama pull <model-name>
```

This uses Ollama's own distribution CDN and is typically the fastest method.

## Strategy 4: Direct VM Download + Ollama Ingest

When you have a GGUF file on the VM and need to load it into Ollama:

```bash
# 1. Download to /tmp
wget -O /tmp/model.gguf '<URL>'

# 2. Load into Ollama via Modelfile
docker exec ollama cat <<EOF | ollama create my-model:latest
FROM /tmp/model.gguf
EOF

# Or use ollama create with -f Modelfile
cat > /tmp/Modelfile <<EOF
FROM /tmp/model.gguf
EOF
docker cp /tmp/Modelfile ollama:/tmp/Modelfile
docker exec ollama ollama create my-model:latest -f /tmp/Modelfile
```

## Quick Decision Tree

```
Model on Ollama library?
  YES → docker exec ollama ollama pull <name>  ✅ fastest
  NO
    Mac and VM on same LAN?
      YES → python3 -m http.server on Mac, wget on VM
      NO
        VM has internet?
          YES → hf download / wget on VM
          NO  → SCP (only option, accept slow speed)
```

## Pro Tips

- Always prefer `ollama pull` for Ollama-library models
- Use `q` variants (Q4_K_M, Q5_K_M) to minimize transfer size
- Q4_K_M is typically ~4x smaller than Q8_0 with ~5% quality loss
- For repeated transfers, consider creating a running HTTP server that stays available
- Always verify file integrity: `sha256sum /tmp/model.gguf`
