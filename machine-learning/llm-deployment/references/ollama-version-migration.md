# Ollama Version Migration Troubleshooting

## Problem: Models Disappear After Ollama Upgrade

After upgrading Ollama (e.g., via `docker pull ollama/ollama:latest`), `ollama list` returns empty even though model data exists on disk.

## Symptoms
```
$ docker exec ollama ollama list
NAME    ID    SIZE    MODIFIED

$ docker exec ollama ls /root/.ollama/blobs/
sha256-63c9be0cc3d5d7b0377161064a74c82b1a5a6ee9ba4a9a3cf034293d6dd09282
```

## Diagnosis
The new Ollama version has restructured its internal directory layout. The GGUF blob exists but manifests are at the wrong path relative to `OLLAMA_MODELS`.

## Fix

### Step 1: Map the directory change
```bash
# Check old structure
ls /root/.ollama/blobs/          # GGUF files here (NEW location)
ls /root/.ollama/manifests/      # Manifests here (NEW location)

# New Ollama expects them at:
ls /root/.ollama/models/blobs/   # Should have GGUF
ls /root/.ollama/models/manifests/ # Should have manifests
```

### Step 2: Copy data to new locations
```bash
docker exec ollama bash -c '
  mkdir -p /root/.ollama/models/blobs
  mkdir -p /root/.ollama/models/manifests/registry.ollama.ai/library
  
  # Copy blobs
  cp /root/.ollama/blobs/* /root/.ollama/models/blobs/ 2>/dev/null
  
  # Copy manifests (recursive, preserve directory structure)
  cp -r /root/.ollama/manifests/registry.ollama.ai/library/* \
        /root/.ollama/models/manifests/registry.ollama.ai/library/ 2>/dev/null
'
```

### Step 3: Restart Ollama
```bash
docker restart ollama
docker exec ollama ollama list  # Should show models
```

### Step 4: Verify model serves correctly
```bash
curl -s http://localhost:11434/api/tags | python3 -m json.tool
curl -s http://localhost:11434/api/generate \
  -d '{"model":"model-name","prompt":"hi","stream":false}' | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['response'])"
```

## Prevention

### Keep Ollama version pinned
```
# Use a specific tag, not :latest
docker pull ollama/ollama:0.32.6
```

### Backup model directory before upgrade
```bash
tar czf /tmp/ollama-models-backup-$(date +%Y%m%d).tar.gz \
  /home/mkanavi/ollama_models/
```

### Check entrypoint command on upgrade
```bash
docker inspect ollama --format '{{.Config.Cmd}}'
```

## Version-specific notes

| Version | Entry Point | Blob Location | Manifest Location |
|---------|------------|---------------|-------------------|
| < 0.32  | `serve`    | `models/blobs/` | `models/manifests/` |
| >= 0.32 | `serve`    | `blobs/` (top-level) | `manifests/` (top-level) |
