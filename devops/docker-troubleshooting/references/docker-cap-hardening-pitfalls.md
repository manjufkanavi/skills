# Docker Security Hardening — Capability Pitfalls

Session findings from iacgenie-platform deployment audit. When applying `cap_drop: ALL` + `no-new-privileges` to containers, several services crash because they need specific Linux capabilities to write to mounted volumes.

## Services That Break With `cap_drop: ALL` Alone

### Redis 7
**Error:** `setpriv: setresuid failed: Operation not permitted`
**Cause:** Redis needs to drop privileges at startup by calling setresuid(). Without SETUID/SETGID, this fails.
**Fix:** Add `SETGID`, `SETUID` to `cap_add` (CHOWN, DAC_OVERRIDE, FOWNER already present).

### NSQD 1.3.0
**Error:** `failed to persist metadata - open /nsq/data/nsqd.dat.XXXXX.tmp: permission denied`
**Cause:** NSQD runs as a non-root user and needs to create files in the mounted volume. Without SETUID, it can't set file ownership.
**Fix:** Add `SETGID`, `SETUID` to `cap_add`.

### Nginx (Frontend, MinIO Console Proxy)
**Error:** `chown("/var/cache/nginx/client_temp", 101) failed (1: Operation not permitted)`
**Cause:** Nginx worker process needs to set ownership on its cache directory. Without CHOWN capability, chown() fails.
**Fix:** Add `CHOWN` to `cap_add`.

### SearXNG 2026.8.1
**Error:** `cp: can't create '/etc/searxng/settings.yml': Permission denied`
**Cause:** The SearXNG Docker image ships with `/etc/searxng/` owned by root. The container runs as a non-root user (uid 1000) and cannot write to this directory.
**Fix:** Two-part:
1. Add volume mount: `/path/to/host/searxng:/etc/searxng`
2. Add `cap_add: CHOWN, DAC_OVERRIDE, FOWNER, SETGID, SETUID`

### Prometheus
**Error:** Would fail to write to `/prometheus` data directory (same pattern as NSQD)
**Fix:** Add `SETGID`, `SETUID` to `cap_add`.

## Generic Diagnosis Flow

When a container crashes with permission-related errors:

1. `docker inspect <container> --format '{{.HostConfig.CapDrop}}'` — see what's dropped
2. `docker inspect <container> --format '{{.HostConfig.CapAdd}}'` — see what's allowed
3. `docker logs <container> 2>&1 | head -20` — find the exact syscall failing
4. `ls -la /path/to/volume/` — check host-side ownership
5. `stat -c '%u:%g' /path/to/volume/` — get numeric UID:GID

## When `cap_drop: ALL` Is Safe

Most services are fine with `cap_drop: ALL` when:
- They only read from volumes (not write)
- They don't need to setuid/setgid
- They don't need to chown files
- They run as root or match the volume owner exactly

Examples: MinIO (data files written as root inside container, volume owned by root), Keycloak (reads config, writes to DB which is on another service).

## Cloudflared: Systemd, Not Docker

Cloudflared should NOT run in Docker. The Docker image expects a tunnel token via `TUNNEL_TOKEN` env var but fails with:
```
"cloudflared tunnel run" requires the ID or name of the tunnel to run as the last command line argument or in the configuration file.
```

Correct pattern: host-level systemd service using a JSON config file with `token` field.
