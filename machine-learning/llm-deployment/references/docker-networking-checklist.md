# Docker Networking Checklist for LLM Stack

When OpenWebUI cannot reach Ollama, run these checks in order:

## Step 1: Confirm Ollama is listening
```bash
docker exec ollama curl -s http://127.0.0.1:11434/api/tags
```
If this fails, the Ollama container is down or misconfigured.

## Step 2: Find Ollama's bridge IP
```bash
docker inspect ollama --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{"\n"}}{{end}}'
```
Typical output: `10.0.0.7` (or `172.17.0.x` for default bridge).

## Step 3: Test reachability from OpenWebUI container
```bash
docker exec open-webui curl -s --connect-timeout 3 http://10.0.0.7:11434/api/tags
```
If this works, the issue is `OLLAMA_BASE_URL` env var. Fix:
```bash
docker stop open-webui && docker rm open-webui
docker run -d --name open-webui -p 4000:8080 \
  -e OLLAMA_BASE_URL=http://10.0.0.7:11434 \
  -e USE_OLLAMA_DOCKER=false \
  ghcr.io/open-webui/open-webui:main
```

If this fails, proceed to Step 4.

## Step 4: Check network configuration
```bash
docker inspect open-webui --format '{{.HostConfig.NetworkMode}}'
docker inspect ollama --format '{{.HostConfig.NetworkMode}}'
```
Both should show `bridge` or both should show `iacgenie` (user-defined).

**If both are `bridge` but container-name resolution fails**:
The default bridge network doesn't support cross-container DNS. Use the bridge IP (from Step 2) instead of the container name.

**To fix permanently (user-defined network)**:
```bash
docker network create iacgenie
docker network connect iacgenie ollama
docker network connect iacgenie open-webui
```
After this, `http://ollama:11434` will resolve correctly.

## Step 5: Verify host-level access
```bash
curl -s http://127.0.0.1:11434/api/tags
```
If this fails, Ollama isn't bound to `127.0.0.1` or the port is wrong. Check `OLLAMA_HOST` in the container's env.

## Common symptoms and causes
| Symptom | Likely cause |
|---------|-------------|
| `Could not resolve host: ollama` | Using container name on bridge network; use IP |
| Connection timed out from container | `OLLAMA_BASE_URL` uses host external IP (e.g., 192.168.x.x) |
| `Not authenticated` on `/api/models` | OpenWebUI requires login; model sync may still be working |
| WebUI shows "No models available" | Ollama unreachable OR OpenWebUI hasn't synced yet (wait 60s) |
