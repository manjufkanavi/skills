# Docker Bridge Network DNS Resolution Failure

**Session:** 2026-08-11

## Problem

OpenWebUI container could not reach Ollama container despite both being on the `bridge` network.

**Error in logs:**
```
Connection error: Cannot connect to host ollama:11434 ssl:default [Domain name not found]
```

**Config:** `ollama.base_urls` was set to `["http://ollama:11434"]` (correct JSON format).

## Root Cause

On Linux Docker, containers on the **same bridge network** do NOT always resolve each other's container hostnames via DNS. This is a Docker DNS service issue on the default bridge network.

**Why it's tricky:** Both containers had IPs on the same subnet (`10.0.0.x`), so pinging by IP might work, but DNS name resolution of `ollama` fails.

## Diagnosis

```bash
# Check which networks each container is on
docker inspect open-webui --format '{{json .NetworkSettings.Networks}}'
docker inspect ollama --format '{{json .NetworkSettings.Networks}}'

# Check IPs
docker inspect open-webui --format '{{.NetworkSettings.IPAddress}}'
docker inspect ollama --format '{{.NetworkSettings.IPAddress}}'
```

Expected output — both on `bridge` network, both on `10.0.0.x/24` subnet.

## Fix Options (ordered by reliability)

### Option 1: Connect to a user-defined network (RECOMMENDED)

User-defined bridge networks have working DNS:
```bash
docker network create iacgenie-backend
docker network connect iacgenie-backend ollama
docker network connect iacgenie-backend open-webui
# Or if already created:
docker network connect iacgenie-backend ollama
```

### Option 2: Use the container's IP directly

Replace `http://ollama:11434` with `http://10.0.0.7:11434` (or whatever IP Ollama has).

**Caveat:** IPs can change on container restart/recreation.

### Option 3: Use `--add-host` in the container

```bash
docker update open-webui --add-host ollama:10.0.0.7
docker restart open-webui
```

## Lessons

1. **Same bridge network ≠ working DNS.** User-defined networks (`docker network create`) have working DNS; the default `bridge` network does not reliably.
2. **`host.docker.internal` does NOT work on Linux Docker.** It's a Docker Desktop feature, not available on bare-metal Linux.
3. **Always verify by testing from INSIDE the container:** `docker exec <container> curl -s http://<target-host>:<port>/path`
4. **Check Docker logs before changing config.** The log showed `[Domain name not found]` — confirming it was DNS, not connectivity.
