# BusyBox wget Pattern for OpenBao Container

When running commands inside the OpenBao container (Alpine-based), `wget` is BusyBox's minimal implementation, NOT GNU wget. This affects flag syntax.

## Key Differences

| Action | GNU wget | BusyBox wget |
|--------|----------|--------------|
| Add header | `-H 'Header: value'` | `--header='Header: value'` |
| Output to stdout | `-O -` | `-O -` (same) |
| Quiet mode | `-q` | `-q` (same) |
| Timeout | `--timeout=N` | `-T N` |
| Follow redirects | `-L` | Not available |

## Common Patterns

### Get seal status
```bash
docker exec iacgenie_openbao wget -q -O - http://127.0.0.1:8200/v1/sys/seal-status \
  --header='X-Vault-Token: s.pRPpNddzoGQD9msKvqVftUdZ'
```

### Take raft snapshot via API
```bash
docker exec iacgenie_openbao wget -q -O /openbao/raft/backups/openbao-snapshot-$(date -u +%Y%m%dT%H%M%SZ).snap \
  http://127.0.0.1:8200/v1/sys/storage/raft/snapshot \
  --header='X-Vault-Token: <TOKEN>' \
  --header='Accept: application/octet-stream' \
  -T 120
```

### Health check
```bash
docker exec iacgenie_openbao wget -q -O /dev/null http://127.0.0.1:8200/v1/sys/health
```

## When to Use

This pattern is useful when:
- The host can't reach the container (bridge network, not host mode)
- The `bao` CLI inside the container defaults to HTTPS (even with `tls_disable = 1`)
- You need a quick API call without installing Python or other tools
- The container has no Python but has wget (Alpine-based images)

## Verification

Always check which wget variant is installed:
```bash
docker exec iacgenie_openbao wget --version 2>&1 | head -1
# BusyBox v1.37.0 → use --header
# GNU wget 1.21 → use -H
```
