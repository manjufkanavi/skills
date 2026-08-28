# Nginx + Docker Port Mapping Pitfall

## The Trap

Docker container port mapping syntax is `host_port:container_port`. When a container maps `9096→9090`, the **host-facing port is 9096** and the **container-internal port is 9090**.

Nginx runs on the **host** and must proxy to the **host-facing port** (9096), NOT the container-internal port (9090).

## Common Mistake

```nginx
# ❌ WRONG — proxies to container-internal port
location /api/v1/ {
    proxy_pass http://127.0.0.1:9090;  # This is Prometheus, not auth-wrapper!
}
```

```nginx
# ✅ CORRECT — proxies to host-facing port
location /api/v1/ {
    proxy_pass http://127.0.0.1:9096;  # Docker-mapped port for auth-wrapper
}
```

## Diagnosis

```bash
# Check what port mapping the container has
docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep auth_wrapper
# Output: iacgenie_auth_wrapper    127.0.0.1:9096->9090/tcp
#         ^^^^^^^^^^^^^^^^^^^^ host-facing port

# Check what's actually listening on each port
ss -tlnp | grep -E '909[06]'
# 9090 → Prometheus (wrong target)
# 9096 → auth_wrapper (correct target)

# Test each port
curl -s http://127.0.0.1:9090/   # Returns Prometheus redirect
curl -s http://127.0.0.1:9096/  # Returns auth-wrapper redirect to /login
```

## Why This Happens

The summary/commit message said:
> "auth_wrapper listens on 9090, so change nginx to 9090"

This is **backwards**. The container's internal port is 9090, but nginx runs on the host and needs the host-facing port (9096). The container-internal port is only reachable from within the Docker network, not from the host.

## Rule of Thumb

When nginx (running on the host) proxies to a Docker container:
- **Always use the host-facing port** (left side of `→` in `docker ps` output)
- **Never use the container-internal port** (right side of `→`)
- Verify by checking `ss -tlnp` to see what's actually listening on each port

## Affected Services on This VM

| Container | Host Port | Container Port | What's on Container Port |
|-----------|-----------|----------------|-------------------------|
| auth_wrapper | 9096 | 9090 | Auth wrapper service |
| Prometheus | 9090 | 9090 | Prometheus (NOT auth_wrapper) |
| Ollama | 11434 | 11434 | Ollama (same port, no confusion) |
