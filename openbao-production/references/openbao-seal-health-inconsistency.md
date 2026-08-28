# OpenBao seal-status / Health API Inconsistency

## The Problem

In some OpenBao 2.6.x deployments, `GET /v1/sys/seal-status` can return `sealed=true` while the server is actually operational and accepting API requests.

### Manifestation

```json
// seal-status says sealed:
{
  "type": "shamir",
  "initialized": true,
  "sealed": true,
  "t": 2,
  "n": 3,
  "progress": 0,
  "nonce": ""
}

// but health says unsealed:
{
  "initialized": true,
  "sealed": false,
  "standby": false,
  "version": "2.6.0"
}
```

### Root Cause

This inconsistency occurs after:
1. **Failed unseal key attempts** — When a wrong key is submitted, the nonce resets and `progress` drops to 0, but the server's internal unseal state may not fully reset.
2. **Server crash during unseal** — If the container crashes after partial unseal (e.g., 1/3 keys applied), the next restart may load an inconsistent state.
3. **Container recreation** — `docker rm` + `docker compose up -d` with pre-existing raft data can leave the raft layer in a state where `seal-status` reports sealed but internal Raft leadership has established.

### How to Diagnose

Always cross-check with the health endpoint:

```bash
curl -sfk http://127.0.0.1:8200/v1/sys/health | python3 -c "
import sys, json
h = json.load(sys.stdin)
print('sealed:', h.get('sealed'))
print('standby:', h.get('standby'))
print('version:', h.get('version'))
"
```

If `sealed=false` in health, trust the health endpoint — the server is operational and backup scripts will work.

### Resolution

1. **Stop and recreate the container** (not just restart):
   ```bash
   docker stop iacgenie_openbao && docker rm iacgenie_openbao
   cd /home/mkanavi/docker/iacgenie && docker compose up -d openbao
   ```

2. **Wait for raft to stabilize** (~30 seconds).

3. **Recheck both endpoints** — `seal-status` and `health` should now agree.

### Prevention

- Avoid submitting invalid unseal keys — always validate key lengths (44 chars) before attempting.
- Use `docker compose up -d --force-recreate` when troubleshooting seal state.
- After a crash, always recreate the container rather than just starting it.
