# Docker Health Check Troubleshooting

## /dev/tcp Bashism

Docker health checks run via `/bin/sh -c`, NOT bash. Any command using bash-specific syntax will fail silently.

### Broken pattern (across all containers)
```yaml
healthcheck:
  test: ["CMD-SHELL", "exec 6<>/dev/tcp/127.0.0.1/3000 && exec 6>&-"]
```
**Result:** Container marked unhealthy. FailingStreak grows to 1000+. Command output:
```
/bin/sh: can't create /dev/tcp/127.0.0.1/3000: nonexistent directory
```

### Diagnosis script
```bash
for c in $(docker ps -q); do
  name=$(docker inspect --format '{{.Name}}' $c | sed 's/^\///')
  hc=$(docker inspect --format '{{range .State.Health.Log}}{{.Output}}{{end}}' $c | tail -1)
  echo "$name: $hc"
done
```

## Working Health Check Patterns

### Pattern 1: wget --spider (Alpine/Debian containers with wget)
```yaml
test: ["CMD-SHELL", "wget -q --spider http://localhost:<port>/ || exit 1"]
```
Works for: Gitea, SearXNG, Minio. Does NOT work for: NSQD (`/` returns 404).

### Pattern 2: wget to service-specific endpoint
```yaml
test: ["CMD-SHELL", "wget -q -O /dev/null http://127.0.0.1:4151/stats 2>/dev/null || exit 1"]
```
Works for: NSQD (`/stats` returns HTTP 200 with health info).

### Pattern 3: bash /dev/tcp (containers with bash but no wget)
```yaml
test: ["CMD-SHELL", "bash -c 'exec 6<>/dev/tcp/127.0.0.1/<port> && exec 6>&-']
```
Works for: Keycloak (RHEL-based, has bash, no wget/curl).

### Pattern 4: curl-based (containers with curl)
```yaml
test: ["CMD-SHELL", "curl -sf http://localhost:<port>/ || exit 1"]
```

## Verifying Before Deployment

Always test inside the target container:
```bash
# Test sh compatibility
docker exec <container> sh -c "exec 6<>/dev/tcp/127.0.0.1/3000 && echo OK || echo FAIL"

# Test wget availability
docker exec <container> sh -c "which wget && echo OK || echo 'no wget'"

# Test bash availability
docker exec <container> sh -c "which bash && echo OK || echo 'no bash'"

# Test endpoint HTTP status
docker exec <container> sh -c "wget -q -O - http://localhost:3000/ 2>&1 | head -3"
```

## Debugging a Stubborn Unhealthy Container

1. Get health check definition: `docker inspect <container> --format '{{.Config.Healthcheck.Test}}'`
2. Run it manually inside container: `docker exec <container> sh -c '<test-command>'`
3. If it fails, test alternative: `docker exec <container> sh -c 'wget -q -O - http://localhost:<port>/'`
4. If wget isn't available, check for bash: `docker exec <container> test -f /bin/bash && echo 'has bash'`
5. If bash exists, try `/dev/tcp` in bash: `docker exec <container> bash -c 'exec 6<>/dev/tcp/127.0.0.1:<port>'`
6. Pick the best working command and update compose file

## Base64-in-SSH Pattern

For running complex Python scripts on VMs without quoting hell:

```bash
python3 /tmp/script.py | base64 | ssh newvm "base64 -d > /tmp/script.py && python3 /tmp/script.py"
```

This avoids all shell escaping issues with nested quotes, special characters, and heredocs.
