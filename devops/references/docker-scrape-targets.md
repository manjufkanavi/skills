# Docker Networking — Prometheus Scrape Targets

## The Problem
Prometheus running inside a Docker container cannot reach services bound to `127.0.0.1` on the host.

## Why It Happens
- Inside the container, `127.0.0.1` = the container itself
- `host.docker.internal` = Docker Desktop only (not Linux Docker)
- Bridge gateway IPs (`10.0.2.1`, `10.0.1.1`) only work if services listen on the bridge IP, not `127.0.0.1`

## Docker Compose Project Isolation
Containers in **different** Docker Compose projects (different directories) create **separate** Docker networks with isolated DNS. You cannot resolve `iacgenie_backend` from a compose file in a different project.

### Solutions
1. **Shared networks**: Define `external: true` for the network in both compose files
2. **Same project**: Put everything in one docker-compose.yml
3. **Host networking**: Use `network_mode: "host"` for the monitoring stack
4. **Add hosts**: In compose, use `extra_hosts: ["host.docker.internal:10.0.2.1"]`
5. **Exporters as containers**: Run node_exporter, postgres_exporter, etc. on the shared network

## Port Discovery
Always verify what's actually listening before configuring scrape targets:
```bash
ss -tlnp | grep 127.0.0.1
```

## Common Gotcha: Services on 127.0.0.1 vs 0.0.0.0
| Binding | Container can reach? | `host.docker.internal`? | Bridge IP? |
|---|---|---|---|
| `127.0.0.1:PORT` | No | No | No |
| `0.0.0.0:PORT` | Yes (via bridge IP) | No | Yes |
| `:::PORT` | No | No | No |
