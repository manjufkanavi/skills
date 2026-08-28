---
name: redis-capability-profile
description: "Redis Docker container capability requirements for security hardening."
created: 2026-08-16
---

# Redis Docker Capability Profile

## Required Capabilities

Redis running in Docker with `cap_drop: ALL` requires these specific capabilities to write to mounted volumes:

| Capability | Reason |
|------------|--------|
| CHOWN | Required for chown/mkdir in mounted volumes |
| DAC_OVERRIDE | Required for bypassing file permission checks |
| FOWNER | Required for owning files in mounted volumes |
| SETGID | Required for Redis to set group ID |
| SETUID | Required for Redis to set user ID |

## Docker Compose Profile

```yaml
redis:
  cap_drop:
    - ALL
  cap_add:
    - CHOWN
    - DAC_OVERRIDE
    - FOWNER
    - SETGID
    - SETUID
```

## Pitfalls

1. **Removing SETUID causes startup failure:** `setpriv: setresuid failed: Operation not permitted`
2. **Removing CHOWN causes volume write failures:** Redis cannot create files in mounted data directories
3. **These capabilities are safe** — they do NOT grant root access or allow container escape. They only permit the Redis process to manage file ownership within its container.