# OpenBao 2.6 Deployment Notes

## Key Changes from Earlier Versions

### Binary Name
- **Image entrypoint:** `openbao` (Helm/K8s name)
- **Actual binary:** `/usr/local/bin/bao`
- In Docker Compose, use `bao server` — not `openbao server`

### Config File
- Mount config to a known path: `-v /path/to/openbao-prod.hcl:/openbao/storage/openbao-prod.hcl`
- Ensure config exists on the host BEFORE starting the container
- Remove unsupported fields: `rate_limit` is not valid in 2.6+

### Permission Issue (Very Common)
```
FATAL: failed to create fsm: failed to open bolt file: open /openbao/raft/vault.db: permission denied
error loading configuration: stat /openbao/storage/openbao-prod.hcl: permission denied
```

**Root cause:** The OpenBao Docker image runs as the `openbao` user (uid 100).
Host bind mount files owned by `mkanavi` (uid 1000) are not accessible.

**Fix 1 (quickest):** Add to compose service:
```yaml
openbao:
  user: "0:0"
  command: bao server -config=/openbao/storage/openbao-prod.hcl
```

**Fix 2 (proper):** Set ownership in Ansible before starting:
```yaml
- name: Fix OpenBao volume ownership
  file:
    path: "{{ openbao_data_dir }}"
    owner: "100"
    group: "1000"
    recurse: yes
```

### Unseal Procedure
1. Read unseal key from `init_keys.json` (base64-encoded Shamir shares)
2. Use API: `POST /v1/sys/unseal` with `{"key": "<base64-key>"}`
3. Or CLI: `bao operator unseal <key>` (pass key as arg, not stdin, when not in TTY)
4. If CLI fails with "HTTP response to HTTPS client": `OPENBAO_ADDR=http://127.0.0.1:8200` overrides

### Health Check
The health endpoint at `/v1/sys/health` returns 200 OK even when sealed.
Check both `sealed=false` AND `initialized=true`:
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -k -sf http://127.0.0.1:8200/v1/sys/health | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"sealed\"]==False or d[\"initialized\"]==True'"]
```

## Example Compose Fragment
```yaml
openbao:
  image: openbao/openbao:2.6.0
  container_name: iacgenie_openbao
  restart: unless-stopped
  user: "0:0"
  command: bao server -config=/openbao/storage/openbao-prod.hcl
  volumes:
    - /home/mkanavi/docker/iacgenie/data/openbao:/openbao/storage
    - /home/mkanavi/docker/iacgenie/data/openbao_raft:/openbao/raft
    - /etc/letsencrypt:/etc/letsencrypt
  ports:
    - "127.0.0.1:8200:8200"
    - "127.0.0.1:8201:8201"
```

## Example openbao-prod.hcl
```hcl
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}
storage "raft" {
  path    = "/openbao/raft"
  node_id = "node1"
}
api_addr     = "http://127.0.0.1:8200"
cluster_addr = "http://127.0.0.1:8201"
ui = true
default_lease_ttl = "768h"
max_lease_ttl     = "768h"
telemetry {
  disable_hostname = true
}
# Do NOT include: rate_limit = 0  (unsupported in 2.6+)
```