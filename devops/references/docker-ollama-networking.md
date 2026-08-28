# Docker Ollama Networking Patterns

## Problem: Ollama Unreachable from Docker Compose Containers

When Ollama is running as a standalone Docker container (or systemd service) on the host, containers on custom Docker Compose networks cannot reach it.

## Root Causes

### 1. Ollama on Default Bridge, Consumer on Custom Network

**Symptom:** `OLLAMA_URL=http://ollama:11434` fails with "name resolution failed" or "connection refused"

**Diagnosis:**
```bash
# Check which network Ollama is on
docker inspect ollama --format '{{range $k,$v:=.NetworkSettings.Networks}}{{$k}}={{.IPAddress}} {{end}}'
# Output: bridge=172.17.0.2 (default bridge, NOT on iacgenie-backend)

# Check which network the consumer is on
docker inspect iacgenie_resume_api --format '{{range $k,$v:=.NetworkSettings.Networks}}{{$k}}={{.IPAddress}} {{end}}'
# Output: iacgenie_iacgenie-backend=172.29.1.5
```

**Fix:**
```bash
docker network connect iacgenie_iacgenie-backend ollama
```

### 2. Ollama Port Bound to 127.0.0.1

**Symptom:** Ollama is on the same network but `http://ollama:11434` still fails

**Diagnosis:**
```bash
ss -tlnp | grep 11434
# Output: LISTEN 0 4096 127.0.0.1:11434 0.0.0.0:*
# Only listening on loopback, not on the Docker network interface
```

**Fix — rebind to 0.0.0.0:**
```bash
# For Docker container:
docker stop ollama && docker rm ollama
docker run -d --name ollama -p 0.0.0.0:11434:11434 -e OLLAMA_HOST=0.0.0.0:11434 ollama/ollama serve

# For systemd service:
# Edit /etc/systemd/system/ollama.service or set OLLAMA_HOST=0.0.0.0:11434
# Then: systemctl daemon-reload && systemctl restart ollama
```

### 3. Ollama Container Not on Same Network as Consumer

**Symptom:** Ollama is on `iacgenie-backend` but `http://ollama:11434` still fails

**Diagnosis:**
```bash
# Check if Ollama is actually on the network
docker network inspect iacgenie_iacgenie-backend --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}\n{{end}}' | grep ollama
# If no output, Ollama is NOT on the network
```

**Fix:**
```bash
docker network connect iacgenie_iacgenie-backend ollama
```

## Verification Checklist

After fixing Ollama networking:

```bash
# 1. From the host
curl http://127.0.0.1:11434/api/tags
# Should return model list

# 2. From inside the consumer container
docker exec iacgenie_resume_api curl -s http://ollama:11434/api/tags
# Should return model list (same as above)

# 3. From the consumer container via host IP
docker exec iacgenie_resume_api curl -s http://172.29.1.1:11434/api/tags
# Should return model list (if Ollama is bound to 0.0.0.0)

# 4. Check Ollama env vars
docker inspect ollama --format '{{json .Config.Env}}' | python3 -c "import sys,json; [print(e) for e in json.load(sys.stdin) if 'OLLAMA' in e]"
# Should show: OLLAMA_HOST=0.0.0.0:11434
```

## Common Mistakes

| Mistake | Why It Fails | Fix |
|---------|-------------|-----|
| `OLLAMA_URL=http://127.0.0.1:11434` in container | 127.0.0.1 = container's own loopback | Use `http://ollama:11434` (same network) or `http://<host-ip>:11434` |
| Ollama on default bridge, consumer on custom network | Docker DNS doesn't cross networks | `docker network connect` |
| Port bound to `127.0.0.1:port` | Other networks can't reach via host IP | Rebind to `0.0.0.0:port` |
| `docker restart` after network connect | Network changes persist, restart not needed | Only restart if Ollama config changed |

## Related Patterns

- See `references/docker-network-recovery.md` for bridge network exhaustion
- See `references/docker-multi-network-dns-failure.md` for multi-network DNS issues
- See `references/docker-bridge-dns-issue.md` (docker-troubleshooting) for bridge DNS resolution
