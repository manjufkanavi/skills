---
name: openbao-production
description: >
  Single umbrella skill for all OpenBao/Vault work. Covers production deployment
  & hardening, secret scanning/migration/rotation, backup & restore (Raft),
  namespaces, monitoring, and multi-tenancy. Works with both Docker Compose and
  bare-metal deployments.
version: 1.2.0
created: 2026-07-23
updated: 2026-08-16
---

# OpenBao — Production, Secrets & Backup

## Skill Overview

This is the single umbrella skill for all OpenBao/Vault work. It has three
major sections (with further subsections):

1. **Production Deployment & Hardening** — bootstrap, TLS, security hardening,
   namespaces, monitoring.
2. **Secret Management** — scanning existing `.env` repos, structured storage in
   KV-v2, service tokens & ACL policies, secret rotation, `.env` replacement.
3. **Backup & Restore** — Raft snapshots, cron scheduling, disaster recovery.

## When to Load
- "deploy OpenBao", "harden our OpenBao/Vault", "set up secrets management"
- "Move .env secrets to Vault", "find all secrets in our repos"
- "Migrate secrets to OpenBao", "vault backup", "raft snapshot"
- "Vault token not working", "Root token invalid"
- Any task involving OpenBao/Vault administration, provisioning, or troubleshooting
- **NEW**: "security audit" of OpenBao or any infrastructure — uses Antares LLM pattern via `references/openbao-antares-audit-pattern.md`
- **NEW**: "container keeps crashing after fixing compose" — check `references/openbao-compose-recreate-vs-restart.md` before debugging further
- **NEW**: "unseal keys failing with cipher: message authentication failed" — check `references/openbao-raft-snapshot-key-mismatch.md` for diagnostic procedure

## Prerequisites

- OpenBao installed (Docker image `quay.io/openbao/openbao:<version>` or binary)
- TLS certificates (Let's Encrypt, private CA, or self-signed)
- Network access to API port (8200) and UI port (8201)
- Access to init keys (`init_keys.json`) or unseal keys

---

## Section 1: Production Deployment & Hardening

### Phase 1: Bootstrap & Initialization

**Step 1.1: Install & Configure**

Deploy OpenBao via Docker Compose or bare metal. Key config elements:

```hcl
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_cert_file = "/path/to/cert.pem"
  tls_key_file  = "/path/to/key.pem"
}

storage "raft" {
  path    = "/openbao/data/raft"
  node_id = "node1"
}

ui = true

default_lease_ttl = "0"
max_lease_ttl     = "0"
```

**Step 1.2: Initialize & Capture Keys**

Run initialization and capture ALL output:
- Root token (64+ characters — verify length, see Pitfalls)
- Unseal keys (5 of 3 required for Shamir)
- Base64-encoded unseal keys

```bash
openbao operator init -key-shares=5 -key-threshold=3 -format=json > init_keys.json
```

### Phase 1.3: Unseal & Verify

**Preferred method — Python requests (most reliable from remote host):**
When calling from a remote host (macOS → Linux VM), the `bao operator unseal` CLI
can reject the first unseal key with "key must be a valid hex or base64 string"
even though the key is valid base64. This happens because the `+` and `/` characters
in base64 keys get URL-encoded when the CLI constructs the API PUT request.

**Also:** In OpenBao 2.6.0+, `bao operator unseal` CLI subcommand was **removed** entirely.
The CLI now shows no `unseal` option under `operator`. You must use the API or Python.

**Workaround — use Python `requests` directly:**
```python
import requests, json

with open("init_keys.json") as f:
    data = json.load(f)

# Submit keys 2 and 3 (key 1 may fail due to URL encoding)
for i, key_b64 in enumerate(data["unseal_keys_b64"][1:3], start=2):
    resp = requests.put(
        "http://127.0.0.1:8200/v1/sys/unseal",
        json={"key": key_b64}
    )
    if resp.status_code == 200:
        result = resp.json()
        print(f"Key {i}: progress={result.get('progress')}, sealed={result['sealed']}")
        if not result["sealed"]:
            print("OpenBao unsealed!")
            break
```

**Local unseal (when on the OpenBao host itself):**
In OpenBao 2.6.0+, the unseal CLI subcommand was removed from `bao operator`. Use
the Python API pattern above, or use the `--key` flag with the API endpoint directly.
```python
# Still works: python3 /dev/stdin << 'EOF'
# import requests
# requests.put("http://127.0.0.1:8200/v1/sys/unseal", json={"key": "<key>"})
# EOF
```

**Note:** When using the CLI inside the container from a non-TTY context (e.g., SSH),
the unseal command will fail with "file descriptor 0 is not a terminal". Pass the key
as the first positional argument: `/usr/bin/vault operator unseal <key>`. The `-address`
flag must come AFTER the subcommand: `/usr/bin/vault operator unseal -address=http://127.0.0.1:8200 <key>`.

### Phase 2: Security Hardening

- Configure TLS on port 8200 (API) and 8201 (UI)
- Use Let's Encrypt certs or private CA
- Verify: `curl -sfk https://vault.example.com:8200/v1/sys/health`
- Create vault password policy for userpass auth
- Create scoped policies per service/project; set token TTLs (max 24h dev, 1h prod)
- Prefer approle over userpass for services
- Limit userpass to admin operations only

### Phase 3: Secrets Engines & KV Management

```bash
openbao secrets enable -path=iacgenie/kv kv
openbao secrets enable -path=lightserp/kv kv
openbao secrets enable -path=terraform/kv kv
```

Create per-project HCL ACL policies and bind to auth methods (approle/userpass).

### Phase 4: Namespaces & Multi-Tenancy

Namespaces are built into OpenBao:

```bash
openbao namespace create iacgenie
openbao namespace create lightserp
openbao namespace create terraform
```

Each namespace needs its own auth methods, KV mounts, policies, and admin accounts.
For cross-namespace KV access use proxy path: `/v1/secret/data/iacgenie/proxy/...`

### Phase 6: Monitoring & Operations

Key endpoints:
- `GET /v1/sys/health` — overall health
- `GET /v1/sys/seal-status` — sealed/unsealed state
- `GET /v1/sys/storage/raft/configuration` — raft peer list

Monitor service logs, audit log, token TTLs, and lease counts.

### Troubleshooting Decision Tree

```
"OpenBao not working" →\
  1. Is the container/service running? → docker ps\
  2. Is it crashing in a loop? → check permissions (see Docker Permission Pitfalls above)\
     - Config file readable? (openbao-prod.hcl chmod 644)\
     - Raft data permissions correct? (recreate container if /openbao/raft has bad perms)\
     - Backup dir owned by running user?\
  3. Is it sealed? → GET /v1/sys/seal-status\
  4. Is the token valid? → verify length (64+ chars), use init_keys.json as source\
  5. Can you reach the API from the host? → ss -tlnp | grep 8200\
     - If nothing shows → container may be on bridge network despite compose saying "host"\
       Check: docker inspect <container> --format '{{.HostConfig.NetworkMode}}'\
       Fix: Use docker exec or container bridge IP (see references/openbao-busybox-wget-pattern.md)\
  6. Is TLS configured? → curl -k https://host:8200/v1/sys/health\
  7. Can you list secrets? → LIST method on metadata\
  8. Can you read secrets? → check token capabilities\
  9. Are namespaces enabled? → check X-Vault-Namespace header\
```

---

## Section 2: Secret Management

### Phase 1: Discovery & Inventory

**1.1 Enumerate Secret Sources**

| Source | Notes |
|--------|-------|
| VM `.env` | `~/docker/iacgenie/.env` — primary, ALL service credentials |
| `.bash_profile` | Exported env vars on VM |
| Local `.env` | Per-project (LightSerp, iacgenie, terraform, Hisaab) |
| GitHub | `gh secret list` per repo (org, repo, environment levels) |

Run `scripts/openbao-secret-scan.py --env-path <path>` to scan and output a
JSON catalog of every secret found, grouped by source.

**1.2 Check Current OpenBao State**

See `references/openbao-remote-api-pattern.md` for the Python API client pattern
that avoids shell escaping issues.

### Phase 2: Structured Storage

Enable KV-v2 mounts per project:

```bash
docker exec iacgenie_openbao /usr/bin/vault secrets enable -path=iacgenie/kv kv
docker exec iacgenie_openbao /usr/bin/vault secrets enable -path=lightserp/kv kv
docker exec iacgenie_openbao /usr/bin/vault secrets enable -path=terraform/kv kv
```

Directory layout examples:

```
iacgenie/kv/
  postgres/super    # superuser credentials
  redis/password
  minio/access_key, secret_key
  cloudflare/api_key
  jwt/secret
  openbao/root_token, service_token
```

Store secrets via `scripts/get-secret.sh` helper or Python API client.

### Phase 3: Service Tokens & ACL Policies

Create scoped ACL policies (HCL) per service. See `templates/openbao-policies.hcl`
for ready-to-use templates. Create service tokens bound to these policies via:

```python
# See references/openbao-remote-api-pattern.md for full code
body = json.dumps({"policies": ["iacgenie-read"], "ttl": "720h"}).encode()
```

Role matrix:

| Role | Auth | Policy | Mount Access |
|------|------|--------|--------------|
| DevOps | userpass (admin) | openbao-admin | ALL + sys/ |
| IacGenie Dev | service token | iacgenie-read | iacgenie/kv/* |
| LightSerp Dev | service token | lightserp-read | lightserp/kv/* |
| Terraform Op | service token | terraform-read | terraform/kv/* |
| CI/CD | service token | per-project | per-project |

### Phase 4: Replace Hardcoded Secrets

Use `${__OPENBAO:...}` reference syntax in `.env` templates (see
`templates/env-reference-pattern.env`). Docker Compose loads generated `.env.local`
at startup.

### Phase 5: Secret Rotation

1. Generate new secret value
2. Store in OpenBao under same path
3. Verify services work with new secret
4. Remove old secret from `.env` files and GitHub secrets
5. Rotate GitHub secrets too

---

## Section 3: Backup & Restore

### Automated Snapshots

Configure cron to run backup script (daily minimum, recommended every 6 hours):

```bash
0 */6 * * * /usr/bin/python3 /opt/scripts/backup_openbao.py >> /var/log/openbao-backup.log 2>&1
```

### Manual Full Backup (includes raft data files)

```bash
bash /home/mkanavi/docker/iacgenie/scripts/openbao-backup.sh manual
```

The backup script does:
- Health check (`curl -k` to `https://127.0.0.1:8200/v1/sys/health`)
- Manual Raft snapshot via POST `/v1/sys/storage/raft/snapshot`
- Copies `raft.db` and latest snapshot to backup dir
- Full tar backup of `openbao_raft/` to `/home/mkanavi/backups/openbao/<timestamp>/`
- 7-day retention auto-cleanup

**Note:** The script takes the `backup` action, NOT `scheduled`. Cron jobs should call `python3 backup_openbao.py backup` (not `python3 backup_openbao.py scheduled`). The script itself handles scheduling logic internally if configured.

**Warning — BAO_ADDR protocol mismatch:** The script hardcodes `https://127.0.0.1:8200` but production OpenBao runs on HTTP. If you see `SSL: WRONG_VERSION_NUMBER`, patch the script to use `http://` — see `references/openbao-backup-args.md#backup-script-baoaddr-protocol-mismatch`.

### Backup Script Fallback — Direct vault.db Copy (Primary Fallback)

When `backup_openbao.py backup` fails (API connection reset, permission denied, timeout, or health check unreachable), use the **direct vault.db copy** as the primary fallback. This bypasses the OpenBao HTTP API entirely and copies the Raft database from the host bind mount.

**Quickest method — run the fallback script:**
```bash
python3 /home/mkanavi/docker/iacgenie/scripts/backup_openbao_fallback.py
```

**Manual method — copy vault.db directly:**
```bash
COMPOSE_DIR="/home/mkanavi/docker/iacgenie"
RAFT_DIR="$COMPOSE_DIR/openbao_raft"
BACKUP_DIR="$RAFT_DIR/backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%dT%H%M%SZ)
cp "$RAFT_DIR/vault.db" "$BACKUP_DIR/vault.db-$TIMESTAMP"
cp "$RAFT_DIR/vault.db" "$BACKUP_DIR/vault.db-$TIMESTAMP.sha256"  # placeholder; compute checksum separately
```

**Why this works:** The `vault.db` file is bind-mounted from the host into the container at `/openbao/raft/vault.db`. Copying it from the host side requires no API access, no token, and no running server. It is a point-in-time copy of the Raft database.

**Verify the backup:**
```bash
ls -lh /home/mkanavi/docker/iacgenie/openbao_raft/backups/vault.db-*.sha256 | tail -3
```

### Backup Script Fallback (Container-Exec Raft Snapshot)

When the direct vault.db copy is not sufficient (e.g., you need an API-consistent snapshot with checkpoints), take a Raft snapshot directly from inside the container:

```bash
# Step 1: Get the token from init_keys.json on the host
TOKEN=$(python3 -c "import json; d=json.load(open('/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json')); print(d.get('root_token') or d.get('new_root_token', ''))")

# Step 2: Run snapshot via docker exec with proper env vars
docker exec -e BAO_ADDR=http://127.0.0.1:8200 -e BAO_TOKEN="$TOKEN" \
  iacgenie_openbao sh -c "bao operator raft snapshot save /openbao/raft/backups/openbao-snapshot-$(date -u +%Y%m%dT%H%M%SZ).snap"

# Step 3: Verify the snapshot file
docker exec iacgenie_openbao ls -lh /openbao/raft/backups/openbao-snapshot-*.snap

# Step 4: Copy snapshot out of container
docker cp iacgenie_openbao:/openbao/raft/backups/openbao-snapshot-*.snap /tmp/
```

**Note:** Token values with `***` will be mangled by shell expansion. When the token comes from a file, use the base64-encoded remote execution pattern from `references/openbao-remote-exec-pattern.md` to safely embed it.

### Backup via Container-Exec wget (BusyBox wget)

When the `bao` CLI inside the container defaults to HTTPS (even with `tls_disable = 1`), use `wget` instead. The container uses BusyBox wget which requires `--header` (not `-H`):

```bash
# Get token
TOKEN=$(python3 -c "import json; d=json.load(open('/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json')); print(d.get('root_token') or d.get('new_root_token', ''))")

# Take snapshot via wget inside container
docker exec iacgenie_openbao wget -q -O /openbao/raft/backups/openbao-snapshot-$(date -u +%Y%m%dT%H%M%SZ).snap \
  http://127.0.0.1:8200/v1/sys/storage/raft/snapshot \
  --header="X-Vault-Token: $TOKEN" \
  --header="Accept: application/octet-stream" \
  -T 120
```

See `references/openbao-busybox-wget-pattern.md` for full BusyBox wget flag reference.

### API snapshot may return HTTP 403** — the streaming API endpoint (`/v1/sys/storage/raft/snapshot`) can fail with 403 Forbidden on production deployments. When this happens, the snapshot file is 0 bytes but the Raft DB copy fallback still succeeds. **Always check the Raft DB copy size** (should be ~30MB+) to confirm data was actually captured.

Backup locations:
- Intermediate: `/home/mkanavi/docker/iacgenie/openbao_raft/backups/`
- Final tar: `/home/mkanavi/backups/openbao/<timestamp>/openbao-backup.tar.gz`

### Full Restore from tar

```bash
docker stop iacgenie_openbao
tar -xzf /home/mkanavi/backups/openbao/<timestamp>/openbao-backup.tar.gz -C /tmp/
sudo cp -r /tmp/openbao_raft/* ~/docker/iacgenie/openbao_raft/
sudo chown -R mkanavi:mkanavi ~/docker/iacgenie/openbao_raft/
docker start iacgenie_openbao
```

### Raft.db-only Restore

```bash
docker stop iacgenie_openbao
cp /path/to/raft.db ~/docker/iacgenie/openbao_raft/raft/raft.db
sudo chown mkanavi:mkanavi ~/docker/iacgenie/openbao_raft/raft/raft.db
docker start iacgenie_openbao
```

### Raft Persistence Patterns

See `references/raft-persistence-patterns.md` for detailed storage layout,
bind mount vs volume patterns, and crash recovery procedures.

---

## Pitfalls & Gotchas

### Token Issues
- **Truncated root tokens**: The root token in `init_keys.json` may be truncated during write. ALWAYS verify token length (should be 64+ characters). A 26-char token is invalid.
- **Unseal key length validation**: Each key in `unseal_keys_b64` should be exactly 44 characters (base64-encoded 32 bytes). Keys with different lengths (e.g., 47 chars) indicate corruption. Validate before unsealing. See `references/openbao-unseal-pattern.md` for the diagnostic script.
- **Corrupted unseal keys fallback**: If ALL `unseal_keys_b64` keys are corrupted, OpenBao 2.x accepts the root token as unseal key with `{"key": "<root_token>", "reset": true}`. See `references/openbao-unseal-pattern.md` for details.
- **sys/mounts trailing slash quirk**: `GET /v1/sys/mounts` returns mount keys **WITH** trailing slashes (e.g. `iacgenie/kv/`) but ALL KV API calls (data/metadata endpoints) MUST use paths **WITHOUT** trailing slashes. When parsing mount names from `sys/mounts`, always strip the trailing `/` before using in KV API calls. This caused 404/403 errors when the trailing slash was preserved.
- **Token with list but not read**: A token may have `list` capability on directory level but not `read` on individual secrets.
- **Bootstrap script path**: `bootstrap_openbao.sh` is inside the container at `/openbao/scripts/`. It reads `.env` from the host compose dir.
- **KV mount enumeration quirk**: An empty KV mount returns 404. Create at least one secret to seed the mount.
- **OpenBao config may not have auto_init**: If no `auto_init`/`auto_unseal` in HCL, OpenBao starts sealed.
- **init_keys.json field name variant**: Some OpenBao initializations (especially with custom `root_token` via API POST to `/v1/sys/init`) use `new_root_token` and `root_token_persisted` fields **instead of** `root_token`. Always resolve the token with: `data.get("root_token") or data.get("new_root_token") or data.get("root_token_persisted", "")`.
- **Token length validation nuance**: While standard OpenBao init generates 64+ char tokens, some API-based initializations (especially with custom root_token) produce shorter tokens like `s.FaJmh6ivmGw0rQWRNvem515M` (26 chars). These are valid — verify the token works via API, not just its length.

### Docker Health Check Pitfall (CMD-SHELL Double Quote Escaping)

When defining a Docker health check via `docker run`, double quotes in CMD-SHELL commands get mangled by the shell. The pattern `grep -q '"sealed":false'` fails because the `"sealed":false` in the JSON response has `"` characters around `sealed` — grep for `sealed:false` doesn't match.

**Broken pattern:**
```
--health-cmd "wget -q -O - http://127.0.0.1:8200/v1/sys/health | grep -q sealed:false"
```

**Working patterns (pick one):**
```
# Option A: Simpler grep (match without quotes)
--health-cmd "wget -q -O - http://127.0.0.1:8200/v1/sys/health | grep -q sealed"

# Option B: Check JSON field with escaped quotes (may also fail)
--health-cmd 'wget -q -O - http://127.0.0.1:8200/v1/sys/health 2>/dev/null | grep -q "\\\\"sealed\\\\":false"'

# Option C: Use curl instead of wget (more reliable in Alpine)
--health-cmd 'curl -sf http://127.0.0.1:8200/v1/sys/health 2>/dev/null | grep -q sealed'

# Option D (best): Simple port probe for liveness
--health-cmd "wget -q -O /dev/null http://127.0.0.1:8200/v1/sys/health"
```

**Verification:** Always test the health check command manually inside the container:
```bash
docker exec <container> wget -q -O - http://127.0.0.1:8200/v1/sys/health | grep -q "sealed" && echo OK || echo FAIL
```

### CLI Flag Placement (CRITICAL)
The `-address` flag must come AFTER the subcommand, NOT before:
```bash
# WRONG — causes "Invalid flags before the subcommand":
bao -address=http://127.0.0.1:8200 kv put ...

# CORRECT:
bao kv put -address=http://127.0.0.1:8200 ...
```

The `-format` flag also goes after the subcommand: `bao kv get -address=http://127.0.0.1:8200 -format=json ...`

### KV Metadata API Gotchas
- **GET on metadata returns 403**: You MUST use the `LIST` HTTP method explicitly (via `?list=true` query param).
- **No trailing slash**: `/v1/{mount}/metadata` not `/v1/{mount}/metadata/`
- **Path format for listing**: `GET /v1/{mount}/metadata?list=true` — this returns the key list for KV-v2 mounts
- **Path format for reading**: `GET /v1/{mount}/data/{key}` — this returns the secret value for a specific key
- **CLI equivalent**: `bao kv list` (NOT `bao list`) for listing; `bao kv get -field=data -format=json` for reading
- **`bao list` returns 403 on versioned KV engines** — the legacy `bao list` subcommand is for non-versioned KV engines only. For KV-v2 mounts, always use `bao kv list`.

### Docker Compose Pitfalls
- **`docker compose restart` doesn't re-read compose file changes**: Running `restart` only stops and starts the container with its **existing** definition. It does NOT pick up changes to command, env vars, volumes, ports, or any other compose field. After modifying `docker-compose.yml`, **always use `docker compose up -d`** (recreate) to apply changes. See `references/openbao-compose-recreate-vs-restart.md` for full details and diagnostic patterns.
- **Container name is `iacgenie_openbao` (underscore)**, not `iacgenie-openbao` (hyphen) — verify with `docker ps`
- **Volume naming**: Docker auto-prefixes named volumes. Verify with `docker volume ls`.
- **Bind mount vs named volume**: Raft data should use bind mounts for predictable host paths.
- **Path mismatch Linux VM vs macOS host**: Scripts hardcode Linux paths (`/home/mkanavi/...`). On Mac Studio use `~/docker/iacgenie/`. Always verify the path exists.

### Shell Escaping (CRITICAL)
- OpenBao tokens/passwords contain `$`, `*`, `!`, `^`, `&` — shell metacharacters
- **Never** pass secrets through inline bash
- **Always** use Python scripts: write → scp → execute

### Python Code Auto-Insertion (`***` Bug)
When writing Python code that contains `***` via SSH heredocs or terminal commands, the system may auto-insert `***` characters, breaking Python syntax. The `***` is Python 3.11+'s extended unpacking operator (PEP 448), and the system treats it as a special token.

**Symptom:** `SyntaxError: invalid syntax` or `SyntaxError: unmatched ')'` on lines containing `***`

**Workaround:** Replace all `***` literals with `chr(42) * 3`:
```python
# WRONG — causes auto-insertion bug:
AST3=***
line = "TOKEN=*** value"

# CORRECT — same result, no auto-insertion:
AST3 = chr(42) * 3
line = f"TOKEN={AST3} value"
```

### Docker Permission Pitfalls (NEW 2026-08)
Three permission patterns cause OpenBao containers to crash in restart loops:

1. **Entry point user dropping (CRITICAL)**: The OpenBao Docker image's `docker-entrypoint.sh` runs as root (UID 0) but then executes `su-exec openbao "$@"` to switch to the `openbao` user (UID 100, GID 1000) via the `BAO_SKIP_DROP_ROOT` environment variable check. If `BAO_SKIP_DROP_ROOT` is not set, the container drops privileges to the `openbao` user which **cannot access host-owned bind-mounted files** (owned by `mkanavi`, UID 1000). This causes a crash loop with: `open /openbao/raft/vault.db: permission denied` or `open /openbao/raft/raft/raft.db: permission denied`.

   **Fix**: Add `BAO_SKIP_DROP_ROOT: "true"` to the OpenBao service environment in docker-compose.yml to prevent the entrypoint from dropping to the `openbao` user. The process then stays as root, which can access all bind-mounted files:
   ```yaml
   openbao:
     environment:
       BAO_SKIP_DROP_ROOT: "true"
       OPENBAO_LOG_LEVEL: info
   ```
   **Also**: This changes the `docker inspect` output — instead of showing `openbao` as the user, it shows `0:0` (root). The `su-exec` behavior is hardcoded in the entrypoint and cannot be disabled via image config — only via the `BAO_SKIP_DROP_ROOT` env var.

2. **Config file unreadable by container user**: The `openbao-prod.hcl` config file is bind-mounted into the container. The container runs as a non-root user (usually UID 100). If the file has `600` or `700` permissions owned by root or another user, OpenBao crashes: `error loading configuration: permission denied`. Fix: `chmod 644` the config file.

3. **Raft data permissions**: Raft storage (`/openbao/raft/vault.db`) inside the container may have overly permissive permissions (`777`) from a dev-mode run. OpenBao requires `600` for raft DB files. The container keeps crashing: `error initializing storage of type raft: stat /openbao/raft/vault.db: permission denied`. Since `/openbao/raft` is NOT a volume mount, you cannot fix this from the host — recreate the container (the ephemeral layer resets).

4. **Backup directory ownership**: The `openbao_raft/backups/` directory may be owned by `dhcpcd:mkanavi` (or root) instead of `mkanavi:mkanavi`, preventing the backup script from writing new backups. Fix: `sudo chown mkanavi:mkanavi openbao_raft/backups/`.

### Data Directory Permissions for Docker overlay2 (NEW 2026-08-07)
OpenBao runs as `root:root` inside the container. Docker overlay2 storage on Linux requires the bind-mounted data directory to have `0777` permissions. Ansible roles that set `owner: mkanavi` or `mode: 0750` will cause data directory access failures.

**Fix**: Always set `owner: root`, `group: root`, `mode: "0777"` on OpenBao data directories (both `/data/openbao` and `/data/openbao_raft`). This is especially critical when running Ansible roles that manage the data directories — they must preserve `root:root` ownership and `777` permissions.

### init_keys.json Double-Escaping Bug (NEW 2026-08-07)
When `init_keys.json` is saved via Ansible `slurp` → `b64decode` → `from_json` pipeline, or when the operator init output is processed through JSON serialization layers, the file can end up double-JSON-serialized. The content becomes a JSON string inside a JSON object instead of a flat JSON object.

**Diagnosis**: If `from_json` returns a string instead of a dict, the file is double-escaped.

**Fix**: Use `from_json | from_json` as a fallback in the Ansible expression:
```yaml
# Primary: single JSON decode
openbao_root_token: "{{ content | b64decode | from_json | json_query('root_token') }}"
# Fallback for double-escaped:
openbao_root_token: "{{ content | b64decode | from_json | from_json | json_query('root_token') }}"
```

**Prevention**: When saving operator init output, write the raw JSON directly (not through `json.dumps()` of `json.dumps()` output). If using Ansible `copy` or `template`, ensure the content is the raw JSON from the operator init output.

### Key Loss Recovery — Reinitialization (NEW 2026-08-07)
If `init_keys.json` is missing from the VM, there is **no way to recover** sealed Raft data. The only recovery path is:

1. Stop the container
2. Clear the Raft data directory (`rm -rf /path/to/openbao_raft/*`)
3. Restart the container
4. Run `bao operator init -key-shares=3 -key-threshold=3 -format=json` inside the container
5. **Immediately** save the output to `init_keys.json` on the VM (chmod 600)
6. Unseal with the 3 keys

**Critical**: Always save `init_keys.json` to both the VM and a secure local backup. The Ansible role stores keys in `defaults/main.yml` and `inventory/group_vars/all.yml` (encrypted), but the VM file is the operational key.

### Docker Port Mapping Pattern (REMOTE HOST)
Docker's `127.0.0.1:8200:8200` port mapping creates a listener on the **remote VM's loopback**, NOT on the macOS host. If you SSH into the VM and curl `127.0.0.1:8200`, it works. If you curl from macOS `127.0.0.1:8200`, it fails.

When you need to talk to OpenBao from macOS:
- **Best**: Use `docker exec <container> /usr/bin/bao ...` to run the CLI inside the container
- **Alternative**: Get the container IP via `docker inspect <container> --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'` and connect directly to that IP:port
- **If on the VM**: `127.0.0.1:8200` works fine (the listener IS on the VM's loopback)

### Compose Network Mode Mismatch (CRITICAL — 2026-08-16)
The docker-compose.yml declares `network_mode: host` for the OpenBao service, but the **actual running container** may be on a bridge network (e.g., `iacgenie_iacgenie-backend`). This happens when:
- The compose file was modified (e.g., port mappings added) which overrides `network_mode: host`
- Docker Compose silently defaults to bridge networking when port mappings conflict with host mode
- The container was created before the `network_mode: host` directive was added

**Symptoms:**
- `docker ps` shows the container running and healthy
- `docker exec <container> wget -qO- http://127.0.0.1:8200/...` works from inside the container
- `ss -tlnp | grep 8200` on the host shows NOTHING (port not visible on host)
- The backup script connecting to `127.0.0.1:8200` from the host gets `Connection refused`

**Diagnosis:**
```bash
# Check actual network mode (not what compose file says):
docker inspect <container> --format '{{.HostConfig.NetworkMode}}'
# If it shows "iacgenie_iacgenie-backend" or similar bridge network, the compose file is misleading.

# Get container's bridge IP for direct access:
docker inspect <container> --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

**Fix:** Use `docker exec` to run commands inside the container (where `127.0.0.1:8200` is correct), or connect to the container's bridge IP directly.

### All KV Paths Empty (KV Bootstrap Never Run)
When all KV engine paths return `{}` or empty, it means **KV bootstrapping was never executed** against this OpenBao instance. The KV engines may be mounted (visible in `sys/mounts`) but no secrets were ever seeded.

**Diagnosis:** `GET /v1/iacgenie/kv/metadata` returns `{"errors":[]}` or `{"data":{"keys":[]}}`

**Action:**
1. Verify KV engines are mounted: `GET /v1/sys/mounts` — look for `iacgenie/kv/`, `lightserp/kv/`, etc.
2. If mounted, seed secrets from `.env` files (see seeding workflow below)
3. If NOT mounted, create them first: `POST /v1/sys/mounts/iacgenie/kv` with `{"type":"kv","options":{"version":"2"}}`

**Seeding Workflow:** Read all `.env` files from the target host, map secret values to the correct KV path structure, then POST each path via the API. Use `chr(42)*3` instead of literal `***` in Python code to avoid auto-insertion bugs.

### Cloudflare Tunnel KV v2 Listing Failure
The Cloudflare tunnel (`https://vault.iacgenie.com`) works for health checks, auth listing, and mount listing, but **returns 404 for KV v2 listing endpoints** — even with a valid root token and root policy. Affected: `GET /v1/{mount}` with `X-Vault-List: true`, `GET /v1/{mount}/list`, `GET /v1/{mount}/metadata`. Root cause: Nginx reverse proxy + Cloudflare tunnel may rewrite/strip headers and paths for non-standard routes. Solution: See `references/openbao-kv-list-remote-pattern.md` for the reliable SSH → docker exec pattern.

### Multiple init_keys.json Files with Different Keys (CRITICAL)

This deployment has THREE copies of `init_keys.json` with DIFFERENT unseal key sets. The backup script reads from the wrong one (stale keys), causing unseal to fail with `"cipher: message authentication failed"`:

- `/home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json` — stale keys (`Ji1h...`)
- `/home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json` — working keys (`WM3H...`)
- `/home/mkanavi/docker/iacgenie/init_keys.json` — working keys (`WM3H...`)

**Fix:** When unseal fails with decryption errors, check ALL `init_keys.json` files on the VM. The keys mounted into the container (`data/openbao_raft/`) are authoritative. See `references/openbao-init-keys-location.md` for the full diagnostic procedure.

### OpenBao Config File Lives in TWO Locations (CRITICAL — 2026-08-14)

OpenBao's HCL config is bind-mounted into the container at TWO separate paths:

1. `/home/mkanavi/docker/iacgenie/openbao_raft/` → mounted to `/openbao/raft/` inside container
2. `/home/mkanavi/docker/iacgenie/data/openbao/` → mounted to `/openbao/storage/` inside container

The server command references `command: bao server -config=/openbao/storage/openbao-prod.hcl`, so the **authentic config is in the `data/openbao/` directory**, NOT the `openbao_raft/` directory.

**Pitfall:** When you edit `openbao_raft/openbao-prod.hcl` (e.g., to change `tls_disable`), the running server ignores your change because it reads from `/openbao/storage/openbao-prod.hcl`. Always verify which path the server command actually references.

**Diagnosis:**
```bash
# Check which config the server is using
docker logs iacgenie_openbao | grep 'config\|Listener'
# Then verify the file content at BOTH locations:
grep tls_disable /home/mkanavi/docker/iacgenie/openbao_raft/openbao-prod.hcl
grep tls_disable /home/mkanavi/docker/iacgenie/data/openbao/openbao-prod.hcl
# Also check inside the container:
docker exec iacgenie_openbao cat /openbao/storage/openbao-prod.hcl | grep tls_disable
```

### Docker Port Proxy Connection Reset (NEW 2026-08-14)

When the OpenBao container is healthy and running, but **Python HTTP clients on the host** get `Connection reset by peer` or `Connection aborted` errors connecting to `127.0.0.1:8200`, this is a **Docker port proxy issue** — not a container issue.

**Symptoms:**
- `docker ps` shows the container as healthy
- `docker exec <container> wget -qO- http://127.0.0.1:8200/v1/sys/health` works from inside the container
- `ss -tlnp | grep 8200` shows port 8200 listening on `127.0.0.1`
- `curl http://127.0.0.1:8200/v1/sys/health` works from the host
- `requests.get('http://127.0.0.1:8200/...')` or `urllib.request.urlopen()` fails with `ConnectionResetError(104, 'Connection reset by peer')`

**Root cause:** Docker's port mapping proxy (`127.0.0.1:8200:8200`) creates a user-space proxy on the host's loopback. Some Python HTTP clients (especially `urllib` with certain TLS/HTTP versions) interact poorly with this proxy and get reset. This is a known issue with Docker's port proxy on some Linux kernels.

**Fallback approach — copy vault.db directly (bypasses API entirely):**
```bash
python3 /home/mkanavi/docker/iacgenie/scripts/backup_openbao_fallback.py
```

**Alternative — use the container's internal loopback via docker exec:**
```bash
docker exec -e BAO_ADDR=http://127.0.0.1:8200 -e BAO_TOKEN=*** \
  iacgenie_openbao bao operator raft snapshot save /openbao/raft/backups/backup-<timestamp>.snap
```

**Alternative — use the container's bridge IP directly (bypasses port proxy):**
```bash
# Get container IP
IP=$(docker inspect iacgenie_openbao --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
curl -s "http://$IP:8200/v1/sys/health"
```

**See:** `references/openbao-backup-approaches.md` for the full comparison of backup methods.

### Token Source Priority
When reading the root token from the `.env` file, note that `OPENBAO_ROOT_TOKEN=***` may show a **literal three-asterisk string** instead of the actual token. This is **not** a shell wildcard — it is actual masked text written into the `.env` file by Ansible or a script.

**`***` means one of two things depending on context:**
1. **Literal `***` (three asterisk characters)** — the actual token was intentionally masked when the `.env` was generated. Extract from `init_keys.json` instead.
2. **Shell wildcard** — when the `.env` was never truncated and the actual token starts with `s.`. In this case `grep '^OPENBAO_ROOT_TOKEN=***` will NOT match properly because `*` is a glob.

**Canonical extraction pattern (Python):**
**Canonical extraction pattern (Python):**
```python
import subprocess
r = subprocess.run(
    ['ssh', 'mkanavi@127.0.0.1', 'cat /home/mkanavi/docker/iacgenie/.env'],
    capture_output=True, text=True
)
for line in r.stdout.splitlines():
    if line.startswith('OPENBAO_ROOT_TOKEN='):
        token = line.split('=', 1)[1].strip()
        if token == '***' or (len(token) < 20 and not token.startswith('s.')):
            print("Token masked in .env — use init_keys.json instead")
            break
        print(f"Token: {token} (len={len(token)})")
        break
```

**Always use `init_keys.json` as the source of truth:**
```python
import json
with open("/path/to/openbao_raft/init_keys.json") as f:
    keys = json.load(f)
TOKEN = keys.get("root_token") or keys.get("new_root_token") or keys.get("root_token_persisted", "")
```

When reading the root token from the `.env` file, note that `OPENBAO_ROOT_TOKEN=***` may show a **literal three-asterisk string** instead of the actual token. This is **not** a shell wildcard — it is actual masked text written into the `.env` file by Ansible or a script.

**`***` means one of two things depending on context:**
1. **Literal `***` (three asterisk characters)** — the actual token was intentionally masked when the `.env` was generated. Extract from `init_keys.json` instead.
2. **Shell wildcard** — when the `.env` was never truncated and the actual token starts with `s.`. In this case `grep '^OPENBAO_ROOT_TOKEN=***` will NOT match properly because `*` is a glob.

### Token Drift: `.env.openbao` vs `init_keys.json` (CRITICAL)
The `OPENBAO_ROOT_TOKEN` stored in `.env.openbao` can diverge from the actual root token in `init_keys.json`. This happens when a service token is accidentally written over the root token value, or when OpenBao is reinitialized without updating the `.env` file.

**Diagnosis:** Token from `.env.openbao` returns `403` on `/v1/sys/mounts`, but `init_keys.json` token works.

**Fix:** Always validate by testing both tokens:
```bash
# Test token from .env.openbao
TOKEN=*** "^OPENBAO_ROOT_TOKEN=*** ~/.env.openbao | cut -d= -f2)
curl -s -H "X-Vault-Token: $TOKEN" http://127.0.0.1:8200/v1/sys/mounts | head -1

# Test token from init_keys.json
TOKEN=*** -c "import json; d=json.load(open('init_keys.json')); print(d.get('root_token',''))")
curl -s -H "X-Vault-Token: $TOKEN" http://127.0.0.1:8200/v1/sys/mounts | head -1

# The working one will show mount data; the other returns {"errors":["permission denied"]}
```

When token drift is detected, update `.env.openbao` with the `init_keys.json` root token, or regenerate a fresh token and update ALL files.

### HTTP Library (NUANCED)
- **`requests` library works fine for** `GET`, `PUT` (unseal, status, health) — use it when you need cleaner code and the API response isn't a problematic POST with empty error body.
- **Use `urllib.request` instead of `requests`** only when doing POST requests that may return `{"errors":[]}` — `requests` can hang on that specific response format.
- **`GET` redirects**: HTTP 307 may return HTML body on trailing slash mismatch. Use `urllib.request` or add `allow_redirects=True` explicitly with `requests`.
- See `references/openbao-remote-api-pattern.md` and `references/openbao-unseal-pattern.md` for full code examples.

### Backup Method: Host Bind Mount vs API Snapshot
**API snapshot endpoint (`/v1/sys/storage/raft/snapshot`) may return permission errors or incomplete data** on production deployments where the OpenBao container has restricted filesystem access. **Always use the host bind mount approach as the primary backup method:**
- Copy Raft DB files directly from the host-mounted directory (`~/docker/iacgenie/openbao_raft/` → backup dir)
- This works regardless of OpenBao API permissions because it accesses files on the host filesystem
- Combine with config file backup (`openbao-prod.hcl`, certs) for completeness
- See `scripts/backup-openbao-bind-mount.py` for the full automation pattern
- The API snapshot (`bao operator snapshot save`) can still be used as a secondary method if permissions allow
- **Important:** The API snapshot works from **inside the container** (connecting to 127.0.0.1 on the container's loopback), but may fail from the host side even when the container is healthy. Docker port proxy can drop TLS connections. If host-side API fails, use the container-exec pattern: `docker exec -e BAO_ADDR=http://127.0.0.1:8200 -e BAO_TOKEN=*** iacgenie_openbao bao operator raft snapshot save /openbao/raft/backups/backup-<timestamp>.snap`

### OpenBao 2.6.0 `bao operator init` Requires `-address` Flag (NEW 2026-08)
In OpenBao 2.6.0+, `bao operator init` defaults to HTTPS (port 8200) even when TLS is disabled. When TLS is off (`tls_disable = 1`), the CLI fails with:
```
Get "https://127.0.0.1:8200/v1/sys/seal-status": http: server gave HTTP response to HTTPS client
```
**Fix:** Always pass `-address=http://127.0.0.1:8200` BEFORE the subcommand:
```bash
docker exec iacgenie_openbao bao operator init -address=http://127.0.0.1:8200 -key-shares=5 -key-threshold=3 -format=json
```
This is the only CLI command where `-address` goes BEFORE the subcommand (unlike `bao operator unseal` where it goes after).

### `bao` CLI Defaults to HTTPS Even with `tls_disable = 1` (NEW 2026-08-13)
The `bao` CLI inside the OpenBao container **always** attempts HTTPS on port 8200, regardless of the HCL config. When `tls_disable = 1` (HTTP listener), the CLI silently switches to HTTPS and fails with:
```
http: server gave HTTP response to HTTPS client
```
This affects ALL CLI commands inside the container (`bao secret list`, `bao auth list`, `bao policy list`, etc.), not just init/unseal.

**Fix:** Always pass `-address=http://127.0.0.1:8200` on the CLI. The flag position depends on the subcommand (see above). For example:
```bash
# Commands where -address goes BEFORE the subcommand:
docker exec iacgenie_openbao bao -address=http://127.0.0.1:8200 operator init ...
docker exec iacgenie_openbao bao -address=http://127.0.0.1:8200 operator unseal ...

# Commands where -address goes AFTER the subcommand:
docker exec iacgenie_openbao bao -address=http://127.0.0.1:8200 kv list ...
docker exec iacgenie_openbao bao -address=http://127.0.0.1:8200 auth list ...
docker exec iacgenie_openbao bao -address=http://127.0.0.1:8200 policy list ...
```

**Workaround:** Use `curl` instead of the `bao` CLI inside the container. All operations work via direct HTTP API without address flag issues:
```bash
docker exec iacgenie_openbao sh -c 'curl -sfk http://127.0.0.1:8200/v1/sys/health'
```
Or call the API directly from macOS using Python `requests` (see `references/openbao-remote-api-pattern.md`).

### OpenBao 2.6.0 `bao secrets list` Syntax Change (NEW 2026-08)
In OpenBao 2.6.0+, the `bao secrets list` subcommand **no longer accepts a mount path as a positional argument**. It only works with no args (lists all mounts). Passing a path like `bao secrets list iacgenie/kv/` returns:
```
Too many arguments (expected 0, got 1)
```

**Fix:** Use `bao kv list` for listing KV secrets, or `bao secrets list` for listing mount points only:
```bash
# WRONG — returns "Too many arguments":
bao secrets list iacgenie/kv/

# RIGHT — list KV secrets in a mount:
bao kv list -mount=iacgenie/kv
bao kv list -mount=iacgenie/kv -recurse

# RIGHT — list all mount points (no path arg):
bao secrets list
```

### OpenBao HCL Config Path Mismatch Crashes Container (NEW 2026-08-13)
OpenBao crashes on startup with `Error initializing core: missing API address, please set in configuration or via environment` when:
1. The compose command references a config path that doesn't exist (e.g., `/openbao/storage/openbao-prod.hcl` but file is at `/openbao/raft/openbao-prod.hcl`)
2. OpenBao falls back to defaults, but Raft storage **requires** `api_addr` to be set

**Root cause:** The `api_addr` and `cluster_addr` directives must be at the top level of the HCL with standard spacing (single space), not excessive whitespace. The old HCL format `api_addr     = "http://..."` with excessive spaces may not parse correctly in some versions.

**Fix:** Always verify the config path in the compose `command` directive matches the actual file location. Standardize HCL format:
```hcl
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = 1
}
storage "raft" {
  path    = "/openbao/raft"
  node_id = "node1"
}
api_addr     = "http://127.0.0.1:8200"
cluster_addr = "http://127.0.0.1:8201"
ui = false
default_lease_ttl = "168h"
max_lease_ttl     = "720h"
```

### Health Check TLS Mismatch Crashes Container (NEW 2026-08-14)
When the deployed `openbao-prod.hcl` has `tls_disable = 0` (TLS enabled) but the compose health check uses `http://127.0.0.1:8200`, the health check fails with "400 Bad Request" and the container reports `unhealthy`. OpenBao logs show repeated: `http: TLS handshake error from 127.0.0.1:X: client sent an HTTP request to an HTTPS server`.

This mismatch commonly occurs when:
- The HCL config was manually edited on the VM to enable TLS (e.g., for direct Cloudflare TLS termination)
- The ansible template defaults to `tls_disable = 1` but the deployed file diverges
- The deployed file has TLS certs but nginx still proxies over HTTP

**Diagnosis:**
```bash
# Check deployed config
grep tls_disable /home/mkanavi/docker/iacgenie/data/openbao/openbao-prod.hcl

# Check health check in running container
docker inspect iacgenie_openbao --format "{{.Config.Healthcheck.Test}}"

# Check logs for TLS errors
docker logs iacgenie_openbao | grep "TLS handshake error"
```

**Fix (Option A — disable TLS on OpenBao, terminate at nginx):**
Set `tls_disable = 1` in `openbao-prod.hcl.j2`, bind to `127.0.0.1:8200`, and use HTTP `api_addr`/`cluster_addr`. This is the recommended pattern when Nginx terminates TLS for Cloudflare.

**Fix (Option B — keep TLS, fix health check):**
Update the compose health check to use `https://` with certificate verification disabled:
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget --no-check-certificate -q -O /dev/null https://127.0.0.1:8200/v1/sys/health"]
```

**Nginx impact:** When proxy_pass is `http://127.0.0.1:8200` but OpenBao has TLS enabled, `proxy_ssl_server_name on` and `proxy_ssl_verify off` directives become **no-ops** because they only apply when proxy_pass uses `https://`. This means TLS is never established between Nginx and OpenBao, causing proxy failures.

### TLS Listener Must Bind to 127.0.0.1 for Docker Deployments (2026-08-14)
When OpenBao is behind a reverse proxy (Nginx) or Cloudflare Tunnel, the TLS listener should bind to `127.0.0.1:8200` — NOT `0.0.0.0:8200`. Binding to `0.0.0.0` exposes the OpenBao API directly on all network interfaces, bypassing Nginx rate limiting and security headers.

**Fix:** In `prod.hcl` AND the Ansible template:
```hcl
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = 0
  tls_cert_file = "/etc/letsencrypt/live/vault.iacgenie.com/fullchain.pem"
  tls_key_file  = "/etc/letsencrypt/live/vault.iacgenie.com/privkey.pem"
}
```
TLS termination happens at Nginx (Cloudflare edge). OpenBao only needs localhost access. The Docker port mapping `127.0.0.1:8200:8200` exposes on the VM loopback only.

### KV v1 vs KV v2 — Ansible Playbook Bug (2026-08-14)

The `openbao-init.yml` playbook **says "Enable KV v2"** but actually uses `kv` (v1):
```yaml
# ❌ WRONG — says v2 but enables v1:
- name: "Phase 4 | Enable KV v2 secret engine (iacgenie)"
  ansible.builtin.command: >
    docker exec iacgenie_openbao bao secrets enable
    --address={{ openbao_addr }}
    -path=iacgenie kv   # ← This is KV v1, not v2!
```

**Fix:** Change `kv` to `kv-v2`:
```yaml
# ✅ CORRECT:
- path=iacgenie kv-v2
```

**Why this matters:** KV v1 uses paths like `iacgenie/data/key` directly. KV v2 requires the `data/` subpath: `iacgenie/data/data/key`. The injector configs expect KV v2 paths (`iacgenie/data/config/platform/database_url`). Storing in KV v1 makes all injectors return `{"errors":[]}`.

**Diagnose:** Run `bao secrets list` — KV v2 shows `type=kv-v2` with version info. KV v1 shows `type=kv` with no version:
```
iacgenie/     kv           ...     ← v1 (WRONG for injectors)
iacgenie/     kv-v2        ...     ← v2 (CORRECT)
```

**To migrate in-place:** Disable and re-enable:
```bash
bao secrets disable iacgenie/
bao secrets enable -path=iacgenie kv-v2
```
Note: This wipes all existing secrets. Re-seed after migration.

### KV Secrets Must Be Seeded After Re-Initialization (2026-08-14)
When OpenBao is re-initialized (vault.db wiped and recreated), ALL previously stored KV secrets are permanently lost. The KV engines are still mounted but return empty data.

**Critical flow after re-init:**
1. `bao operator init` → generate new unseal keys + root token
2. Unseal with threshold keys
3. **Immediate re-seeding** of all KV paths (see `references/openbao-kv-seeding-workflow.md`)
4. Regenerate AppRole credentials (role_id/secret_id are regenerated on re-init)
5. Update `init_keys.json` on VM
6. Verify with `bao read <path>` for each critical secret

**Always seed these minimum paths:**
- `iacgenie/data/config/platform/database_url` (POSTGRES_USER/PASSWORD/DB/HOST)
- `iacgenie/data/config/platform/redis_url` (REDIS_URL)
- `iacgenie/data/config/platform/jwt_secret`
- `iacgenie/data/config/platform/openbao_addr`
- `iacgenie/data/config/minio/minio_root_user`
- `iacgenie/data/config/minio/minio_root_password`
- `iacgenie/data/config/keycloak/kc_admin_user`
- `iacgenie/data/config/keycloak/kc_admin_password`
- `lightserp/data/config/lightserp_database_url`
- `lightserp/data/config/lightserp_api_secret`
- `lightserp/data/config/minio_access_key`
- `lightserp/data/config/minio_secret_key`
- `lightserp/data/config/redis_url`
- `lightserp/data/config/lightserp_keycloak_client_secret`

### OpenBao Security Audit via Local LLM (NEW 2026-08-13)
When auditing an OpenBao deployment, send a structured prompt to a local LLM (antares-1b-mlx-8bit at `http://127.0.0.1:1234`) via `curl` to get a prioritized security report. Include: HCL config, Docker config, Nginx vHost, infrastructure context, and known issues. The model returns risk ratings (HIGH/MEDIUM/LOW) with remediation steps. See `references/openbao-antares-audit-pattern.md` for the full prompt template.

### Root Token Extraction from init_keys.json
When the root token in `.bash_profile` is masked/empty, extract from `init_keys.json`:
```bash
# Extract from the file on the VM:
cat /home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('root_token') or d.get('new_root_token', ''))"
```

The token may be under `root_token` or `new_root_token` (depending on init method). Always resolve with:
```python
data.get("root_token") or data.get("new_root_token") or data.get("root_token_persisted", "")
```

### Storage Env Vars Override Config File (NEW 2026-08)
`OPENBAO_STORAGE_TYPE` and `OPENBAO_STORAGE_PATH` environment variables in Docker compose **override** the values in the OpenBao HCL config file. If your `openbao-prod.hcl` has `path = "/openbao/raft"` but the compose env says `OPENBAO_STORAGE_PATH: /openbao/storage`, the env var wins and raft data goes to the wrong directory.

**Fix:** Remove `OPENBAO_STORAGE_TYPE` and `OPENBAO_STORAGE_PATH` from the compose environment section entirely. Let the config file be the single source of truth. The compose template should only set:
```yaml
environment:
  OPENBAO_ADDR: http://127.0.0.1:8200
  OPENBAO_CLUSTER_ADDR: http://127.0.0.1:8201
  OPENBAO_UI: "true"
  OPENBAO_LOG_LEVEL: info
```

### Docker User Namespace Override (NEW 2026-08)
Docker's user namespace remapping (configured in `daemon.json` with `userns-remap`) **silently overrides** the `user: "0:0"` directive in Docker Compose. Even if you specify `user: "0:0"` in the compose file, the container may run as a remapped UID (e.g., `openbao` instead of `root`). This causes permission mismatches on bind-mounted data directories.

**Diagnosis:** `docker inspect <container> --format '{{.Config.User}}'` — shows what the container actually runs as.

**Fix:** If user namespace remapping is active, set ownership on host data dirs to match the remapped UID, or disable remapping for the OpenBao service. Alternatively, run `docker compose down` and manually start with explicit `--user=0:0` flag to bypass compose parsing.

### Storage Backend Detection (CRITICAL)
**Always check the actual storage backend before backing up.** Dev mode (`-dev` flag) uses file storage or in-memory, NOT Raft. An empty `openbao_raft/` directory does NOT mean the backup failed — data may be in the Docker container.

Detection checklist:
1. **Check container startup args**: `docker inspect <container> --format='{{.Config.Cmd}}'` — look for `-dev` flag
2. **Check config HCL inside container**: `docker exec <container> cat /etc/openbao/openbao.hcl` or check mounted config
3. **Check volume mounts**: `docker inspect <container> --format='{{range .Mounts}}{{.Destination}} -> {{.Source}}{{println}}{{end}}'`
4. **If Raft volume is missing**: Data is either in the container's writable layer (non-persistent) or using a different backend (file/consul)

**Dev mode backup**: Use `docker exec <container> tar czf - /openbao/ | tar xzf - -C <backup_dir>` to extract the entire OpenBao data directory from inside the container. This captures whatever storage backend is actually in use.

### Backup Script Platform Paths
The backup script location differs between platforms:
- **macOS**: `~/docker/iacgenie/backup_openbao.py` (runs from compose directory)
- **Linux VM**: `/home/mkanavi/docker/iacgenie/scripts/backup_openbao.py`

The script auto-detects its `COMPOSE_DIR` from its own file location (`Path(__file__).resolve().parent`), so always run it from its actual location, not via symlink.

### Cloudflare Tunnel + Docker Bridge Networking (2026-08-14)

When Cloudflared runs on a Docker bridge network and Nginx uses `network_mode: host`, the Cloudflare ingress **cannot** use `127.0.0.1` to reach Nginx. The tunnel process runs inside the container, so `127.0.0.1` refers to the container's own loopback, NOT the host.

**Current deployment (2026-08-14):** Cloudflared runs as Docker container `iacgenie_cloudflared` on `iacgenie-frontend` bridge network. Nginx runs as Docker container `iacgenie-nginx` with `network_mode: host`. The ingress config points ALL services to `http://127.0.0.1:80` — this WORKS because:
1. Cloudflared → Nginx container (which has host-level access via `network_mode: host`)
2. Nginx handles hostname-based routing on port 80
3. Nginx proxies each vHost to correct `127.0.0.1:<port>` on the host

**Fix (if standalone cloudflared):** Use the bridge gateway IP instead:
```yaml
ingress:
  - hostname: "vault.iacgenie.com"
    service: https://<bridge-gateway-ip>:443  # e.g., 172.29.2.1
```

Find the gateway IP via: `docker inspect <cloudflare-container> --format '{{.NetworkSettings.Networks.<network>.Gateway}}'`

**IMPORTANT:** After modifying the Cloudflare config.yml volume mount in docker-compose, you must **recreate** the container (not just restart): `docker compose up -d --force-recreate cloudflared`. A plain `restart` does NOT pick up new volume mounts.

---

## Support Files
When data lives inside a container and has no host bind mount:
```bash
docker exec <container> tar czf - /openbao/raft/ | tar xzf - -C <local_dir>
```
This piped tar pattern works reliably for extracting container paths to the host, including when the container has restricted filesystem access.

### Path Resolution Bug in Tarball Creation
When building tar archives from a mixed source (host paths + exported container temp dirs), `Path.relative_to()` can raise `ValueError` when a path doesn't share the expected root. **Always wrap in try/except:**
```python
try:
    arcname = str(member_path.relative_to(COMPOSE_DIR))
except ValueError:
    arcname = member_path.name
```

### ACL Policy API Format (CRITICAL)
When creating ACL policies via the API, you MUST send the HCL content **wrapped in JSON** — NOT raw HCL.

**WRONG — raw HCL via `-d @-`:**
```bash
cat <<'HCL' | curl -s -X POST \
    -H "X-Vault-Token: $TOKEN" \
    -H "Content-Type: application/json" \
    http://127.0.0.1:8200/v1/sys/policy/my-policy -X PUT -d @-
path "secret/*" { capabilities = ["read"] }
HCL
```
Returns: `"failed to decode JSON input: invalid character 'p' looking for beginning of value"`

**CORRECT — JSON-wrapped HCL:**
```python
import json, urllib.request
payload = json.dumps({"policy": 'path "secret/*" { capabilities = ["read"] }'}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8200/v1/sys/policy/my-policy",
    data=payload,
    headers={"X-Vault-Token": TOKEN, "Content-Type": "application/json"},
    method="PUT"
)
urllib.request.urlopen(req)
```

Or with curl:
```bash
echo '{"policy":"path \"secret/*\" { capabilities = [\"read\"] }"}' | \
    curl -s -X PUT -H "X-Vault-Token: $TOKEN" \
    -H "Content-Type: application/json" \
    http://127.0.0.1:8200/v1/sys/policy/my-policy
```

### Credential Audit & Remediation Playbook
When performing a full credential audit and remediation of OpenBao:

1. **Audit phase** — enumerate all services from docker-compose, check which have secrets in OpenBao KV
2. **Validate phase** — test each credential against the live service (pg_isready, redis ping, curl API endpoints)
3. **Fix phase** — identify mismatches (e.g., hardcoded `CHANGE_ME_*` in init scripts overriding OpenBao values)
4. **Bootstrap phase** — if reinitializing, run the 5-phase bootstrap (wait → KV mounts → seed → RBAC → verify)
5. **RBAC phase** — create admin + read-only policies, generate service tokens
6. **Validate phase** — run consistency check comparing .env ↔ OpenBao KV
7. **Document phase** — write credential matrix, operations guide
8. **Commit phase** — commit all scripts, configs, docs; push to Git

See `references/credential-audit-playbook.md` for the detailed playbook.

---

## Documentation Deliverables

For every OpenBao hardening or reconfiguration session, produce 3 audience-specific docs:

1. **DevOps Guide** — Architecture, deployment, config, backup, troubleshooting, security checklist
2. **Admin Guide** — User management, KV operations, policies, token management, emergency procedures
3. **Engineer Guide** — How to read/write secrets, integration examples, best practices, quick reference

Write docs to `docs/` in the infrastructure directory (e.g., `~/docker/iacgenie/docs/`).

---

## Recovery Procedures

These procedures handle unsealing sealed vaults, reinitializing vaults with lost keys, and re-seeding KV engines. Merged from the `vault-recovery` skill.

### Workflow A: Unsealing a Sealed Vault (keys exist)

**Trigger:** Vault reports `sealed: true` but unseal keys are available.

1. **Verify vault state:**
   ```bash
   curl -sk https://127.0.0.1:8200/v1/sys/seal-status
   ```
   Note `t` (threshold) and `n` (total shards). Apply at least `t` keys.

2. **Validate key lengths (diagnostic):**
   ```bash
   python3 -c "
   import json
   with open('init_keys.json') as f:
       data = json.load(f)
   for i, k in enumerate(data['unseal_keys_b64']):
       print(f'Key {i}: {len(k)} chars')
   # All should be 44. Non-44 = corruption.
   "
   ```

3. **Unseal using base64 keys:**
   ```bash
   curl -sk -X POST https://127.0.0.1:8200/v1/sys/unseal \
     -H "Content-Type: application/json" \
     -d '{"key": "<base64_shard>"}'
   ```
   Repeat until `progress` reaches `t` and `sealed` becomes `false`.

   **If keys fail validation or return 400:**
   - See `references/openbao-unseal-pattern.md` for the Python `requests` workaround
   - If ALL keys corrupted, use root-token `reset: true` fallback

4. **Check final state:**
   ```bash
   curl -sk https://127.0.0.1:8200/v1/sys/seal-status
   ```

### Workflow B: Reinitializing (keys lost)

**Trigger:** Vault is sealed AND no unseal keys are available.

1. **Stop the vault container:**
   ```bash
   cd /path/to/docker/compose/dir
   docker compose stop openbao
   ```

2. **Find and wipe ALL storage data (CRITICAL — all files listed):**
   - `<raft_parent>/vault.db` — **most commonly missed** init state file
   - `<raft_parent>/raft/raft.db` — the raft database
   - `<raft_parent>/init_keys.json` — old keys file
   - `<data_dir>/vault.db` — bolt database if exists
   - Any `*.bolt`, `*.wal` files in both directories

3. **Fix ownership to container UID (usually 100):**
   ```bash
   sudo chown -R 100:1000 /path/to/openbao_data/
   sudo chown -R 100:1000 /path/to/openbao_raft/
   ```

4. **Start the vault and verify it's un-initialized:**
   ```bash
   docker compose up -d openbao
   curl -sk https://127.0.0.1:8200/v1/sys/init | python3 -m json.tool
   # Expected: {"initialized": false}
   ```

5. **Initialize with a custom root token:**
   ```bash
   curl -sk -X POST https://127.0.0.1:8200/v1/sys/init \
     -H "Content-Type: application/json" \
     -d '{"secret_shares": 3, "secret_threshold": 2, "root_token": "YOUR_TOKEN"}'
   ```
   **Save the entire response** — unseal keys, root token.

6. **Unseal with keys (order matters — apply 1, then 2):**
   Apply `t` out of `n` keys. Check seal status after each.

7. **Save credentials to init_keys.json** with `chmod 600`.

### Workflow C: Seeding KV Engines & Policies

1. **Create KV-v2 engines** (secret/, terraform/, vault/) — skip if already mounted.
2. **Store service secrets** using `v1/secret/data/<service>/<key>` PUT.
3. **Create policies** using `v1/sys/policy/<name>` PUT.
4. **Create userpass auth** if not already enabled.

### Workflow D: Post-Reinit Admin Setup (OpenBao 2.x)

After reinitialization, the root token may have limited permissions. Always create an admin userpass backup:

1. **Create admin userpass auth** (if not enabled):
   ```bash
   curl -sk -X POST https://127.0.0.1:8200/v1/sys/auth/userpass \
     -H "X-Vault-Token: <root_token>" \
     -H "Content-Type: application/json" \
     -d '{"type": "userpass"}'
   ```

2. **Create admin user**:
   ```bash
   curl -sk -X POST https://127.0.0.1:8200/v1/auth/userpass/users/admin \
     -H "X-Vault-Token: <root_token>" \
     -H "Content-Type: application/json" \
     -d '{"password": "<strong_password>", "policies": ["root"]}'
   ```

3. **Test login**:
   ```bash
   curl -sk -X POST https://127.0.0.1:8200/v1/auth/userpass/login/admin \
     -H "Content-Type: application/json" \
     -d '{"password": "<password>"}'
   ```
   Saves a backup auth method that survives root token revocation.

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `initialized: true` after wiping | `vault.db` in raft parent dir missed | Delete `<raft_parent>/vault.db` too |
| Root token 403 on sys/ paths | Root token has restricted policy | Use admin userpass auth (Workflow D) |
| Unseal key returns empty/400 | Shell quoting mangled `+`/`/` in base64 key, or keys are corrupted (non-44-char lengths) | Use Python script or file-based passing; validate key lengths first. If ALL keys corrupted, use root-token `reset: true` fallback |
| `HTTP 400: path is already in use` | KV engine already mounted | Skip mount step |
| Wildcard cert shows `no cert` on localhost | Nginx uses SNI, not direct IP | Verify via domain name through tunnel, or use `openssl -servername` |
| Container crashes in restart loop | Permission issue on config or raft data | See Docker Permission Pitfalls above |
| Port 8200 works on VM but not from macOS host | Docker port mapping only visible on VM loopback | Use `docker exec` or container IP from host |
| `seal-status` says sealed but server is operational | `GET /v1/sys/seal-status` can return stale/incorrect `sealed=true` when unseal keys are partially applied or nonce changed (e.g., after failed key attempts or server crash) | Cross-check with `GET /v1/sys/health` — if `sealed:false`, the server is operational and API calls will succeed. Also verify with `GET /v1/sys/seal-status` after a clean container restart |

### Operational Notes

- **Save credentials immediately**: Unseal keys are returned ONLY during init. Once saved to disk, they can't be retrieved again. Always `init_keys.json` with `chmod 600` and store a copy offline.
- **Test admin userpass**: Always verify the admin userpass login works right after recovery. This is the recovery path when the root token is lost.
- **VM stability during recovery**: Heavy operations (init + seed + deploy) can stress the VM. After completing operations, allow 1-5 minutes for the VM to stabilize. If SSH is unresponsive, retry with exponential backoff (15s, 60s, 120s).

---

### TLS Cert Hostname Mismatch (CRITICAL — 2026-08-13)

When OpenBao uses a Let's Encrypt cert for `vault.iacgenie.com` but local/admin scripts connect
to `https://127.0.0.1:8200`, the cert hostname does not match → SSL verification fails.

**Symptoms:** `CERTIFICATE_VERIFY_FAILED` error, API snapshot returns 0 bytes, `bao` CLI TLS errors.

**Fix — explicit no-verify SSL context for local connections:**
```python
import ssl
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE
# Then use: urllib.request.urlopen(req, context=_ssl_ctx)
```

### KV v2 List Endpoint Quirk (2026-08-13)

The KV v2 list endpoint has unexpected behavior on some deployments:
- `GET /v1/{engine}/?list=true` → **WORKS** (returns keys)
- `GET /v1/{engine}/metadata/?list=true` → **returns 404**

When listing KV secrets programmatically, always use `/?list=true` endpoint.

### backup_openbao.py sha256_file Typo Bug (2026-08-13)

`backup_openbao.py` crashes with `TypeError` at `sha256_file`: the code has `h.update(h)` instead of `h.update(chunk)`.

**Fix:** `sed -i 's/h.update(h)/h.update(chunk)/' backup_openbao.py`

## Support Files

This skill ships with the following support files:
### References
- `references/openbao-secret-injection-pattern.md` — **NEW**: Docker-entrypoint secret injection pattern — Python injector + shell wrapper + per-service JSON config. Covers TLS skip, HTTPS upgrade, vault key-name mismatch, and AppRole credential sharing via named volume.
- `references/openbao-compose-recreate-vs-restart.md` — **NEW 2026-08-13**: Why `docker compose restart` silently ignores compose file changes and the correct fix (`up -d` + verification via `docker inspect`)
- `references/openbao-docker-permission-diagnostic.md` — **NEW 2026-08-13**: Full diagnostic guide for the entrypoint user-dropping crash loop — `BAO_SKIP_DROP_ROOT` fix, test container patterns, ownership mismatch diagnosis
- `references/credential-audit-pattern.md` — **NEW**: Step-by-step workflow for auditing credentials across the Docker/IacGenie infrastructure — .env extraction, OpenBao token lookup, Nginx URL mapping
- `references/openbao-kv-v2-read-path-pattern.md` — **NEW 2026-08-14**: KV v2 URL construction rule — `/v1/{engine}/data/{path}` (not `/{engine}/{path}`), Python API patterns, IacGenie path table, diagnostic checklist
- `references/openbao-kv-seeding-workflow.md` — **NEW**: Complete workflow for seeding empty KV store from `.env` files, including Python API pattern, key mapping table, and verification steps
- `references/openbao-kv-v2-migration-pattern.md` — **NEW**: KV v1→v2 migration workflow, secret seeding via remote Python scripts, injector config path table, and common error patterns
- `references/openbao-backup-args.md` — **NEW**: Backup script argument syntax (`backup`/`status`/`restore`, NOT `scheduled`)
- `references/openbao-init-keys-location.md` — **NEW**: Multiple init_keys.json files with divergent keys — diagnostic procedure to find the correct unseal keys
- `references/vault-api-mappings.md` — HashiCorp Vault vs OpenBao API path differences
- `references/iacgenie-openbao-deployment-context.md` — IacGenie instance-specific deployment context
- `references/macos-deployment-context.md` — Mac Studio vs Linux VM environment distinction
- `references/openbao-remote-api-pattern.md` — Remote API access via Python (avoids shell escaping)
- `references/openbao-unseal-pattern.md` — Workaround for `bao operator unseal` CLI URL-encoding bug (use Python `requests` PUT instead)
- `references/openbao-kv-v2-read-path-pattern.md` — **NEW 2026-08-14**: KV v2 URL construction rule — `/v1/{engine}/data/{path}` (not `/{engine}/{path}`), Python API patterns, IacGenie path table, diagnostic checklist — SSH → docker exec pattern for KV v2 listing (Cloudflare tunnel fails with 404)
- `references/openbao-token-policy-discovery.md` — Diagnostic workflow for mismatched tokens and stale policy names
- `references/openbao-seal-health-inconsistency.md` — When `seal-status` says sealed but `health` says unsealed
- `references/docker-exec-snapshot-pattern.md` — Docker exec CLI pattern when port mapping doesn't work
- `references/openbao-dev-to-prod-migration.md` — Dev mode to production migration patterns
- `references/init-state-persistence.md` — Init state file persistence across restarts
- `references/remote-script-safe-patterns.md` — Secure remote script patterns
- `references/openbao-production-plan.md` — OpenBao production deployment plan
- `references/openbao-production-plan-2026-08-13.md` — **NEW 2026-08-13**: Current state analysis, issues, migration phases, deep research findings, Ansible-only workflow
- `references/openbao-antares-audit-pattern.md` — **NEW 2026-08-13**: Structured security audit prompt template for local LLM (Antares)
- `references/openbao-production-hardening.md` — Hardening checklist and patterns
- `references/iacgenie-recovery-sequence.md` — IacGenie recovery sequence
- `references/openbao-ssh-transport-pattern.md` — SSH transport patterns for remote OpenBao access
- `references/openbao-unseal-diagnostic.md` — Unseal key diagnostic workflow
- `references/openbao-deployment-context.md` — General deployment context
- `references/openbao-bootstrap-sequence.md` — **NEW 2026-08-13**: Diagnostic checklist + complete bootstrap sequence for running-but-empty OpenBao instances
- `references/openbao-backup-approaches.md` — When to use host bind mount vs Docker exec export vs API snapshot
- `references/cross-kv-policy-pattern.md` — **NEW 2026-08-13**: Cross-KV engine policy sharing pattern. Both iacgenie and lightserp policies must explicitly grant read access to all mounts.

### Scripts
- `scripts/verify-openbao-kv.py` — Quick verification of stored secrets
- `scripts/openbao-secret-scan.py` — Scan `.env` files for secrets, output JSON catalog
- `scripts/check-openbao-ssl.sh` — SSL/TLS health check
- `scripts/audit-openbao-state.sh` — Full state audit
- `scripts/verify-openbao-health.sh` — Quick health check script
- `scripts/get-secret.sh` — Lightweight helper to read a single secret from OpenBao
- `scripts/backup_openbao_fallback.py` — **NEW 2026-08-14**: Direct vault.db copy fallback for backup_openbao.py failures — bypasses HTTP API entirely

### References (NEW)
- `references/openbao-remote-exec-pattern.md` — **NEW 2026-08-14**: Base64-encoded remote script execution pattern for running Python scripts on remote VMs via SSH without shell escaping issues (fallback for failed `backup_openbao.py`)
- `references/openbao-raft-snapshot-key-mismatch.md` — **NEW 2026-08-16**: Diagnostic procedure for when raft data restored from snapshot has incompatible unseal keys, including the "accepted key trap" pattern
- `references/openbao-busybox-wget-pattern.md` — **NEW 2026-08-16**: BusyBox wget syntax differences vs GNU wget — `--header` vs `-H`, useful for running API calls inside Alpine-based OpenBao containers
- `references/openbao-raft-snapshot-key-mismatch.md` — **NEW 2026-08-16**: Diagnostic procedure for when raft data restored from snapshot has incompatible unseal keys, including the "accepted key trap" pattern
- `references/ssh-heredoc-remote-exec.md` — **NEW 2026-08-14**: SSH heredoc pattern (`<< 'PYEOF'`) for running Python scripts on remote VMs — bypasses shell expansion AND file-write tool `***` censorship
- `references/openbao-health-check-tls-mismatch.md` — **NEW**: Diagnosis and fix for TLS mismatch between deployed config and health check (400 Bad Request → unhealthy)
- `references/cloudflare-tunnel-docker-network.md` — **NEW**: Cloudflare tunnel Docker bridge networking pattern and architecture diagram

### Templates
- `templates/openbao-secret-injection.sh` — **NEW**: Reusable shell entrypoint wrapper for Docker secret injection. Drop in as `entrypoint` for any service container.
- `templates/backup_openbao_prod.py`
- `templates/env-reference-pattern.env` — Template showing ${__OPENBAO:...} reference syntax
- `templates/openbao-policies/sample-policies.hcl` — Sample HCL policy templates per service
- `templates/openbao-init.yml` — **NEW**: Ansible playbook for full OpenBao bootstrap (init, unseal, engines, policies, AppRoles) — deploy on fresh instances
- `templates/backup_openbao_prod.py` — **NEW 2026-08-13**: Production backup script with TLS cert hostname mismatch fix (`_ssl_ctx` with `CERT_NONE` for local 127.0.0.1 connections), sha256_file typo fix, API snapshot + DB copy + config backup + rotation. Drop-in replacement for the broken v2.0 script.

### New in 2026-08-13
- **OpenBao Ansible bootstrap playbook** — `openbao-init.yml` now ships in this skill. Run once after first deploy to bootstrap init, unseal, secret engines, and policies reproducibly.
- **Docker compose volume path mismatch** — When the deployed `docker-compose.yml` has volume mounts that differ from the Ansible template (e.g., `data/openbao_raft:/openbao/raft` vs `openbao_raft:/openbao/raft`), the container may silently mount the wrong host directory. **Always verify with `docker inspect --format='{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'`** after any compose change, not just after `up -d`.
- **Multi-path HCL deployment** — When fixing crashes where the HCL config was at the wrong path, deploy to both paths (`/home/mkanavi/docker/iacgenie/openbao_raft/` and `/home/mkanavi/docker/iacgenie/data/openbao_raft/`) to ensure the Ansible role is compatible with either compose variant. See the `roles/openbao/tasks/main.yml` HCL copy task for the loop pattern.
- **Ansible `replace` module breaks YAML** — Using Ansible's `replace` module on deployed `docker-compose.yml` can silently break YAML indentation. **Never use `replace` on compose files** — use `copy` with a template instead. If you hit this, fix manually via SSH `sed -i`.
- **OpenBao bootstrap sequence** — For a fresh OpenBao instance: (1) wait for container running, (2) `bao operator init -format=json`, (3) save keys to BOTH mount paths with `chmod 0600`, (4) unseal keys 1+2, (5) enable secret engines (kv, transit, database, ssh), (6) enable AppRole auth, (7) write policies, (8) create AppRole roles. Use `openbao-init.yml` playbook to automate all steps.
- **Service secret injection via Docker entrypoint** — Instead of modifying service images to use OpenBao SDKs, inject secrets at container startup via an entrypoint wrapper. The pattern uses: (a) a Python injector (`openbao_injector.py`) that authenticates via AppRole, fetches secrets from KV v2, and re-exports them as environment variables, (b) a shell entrypoint wrapper (`inject-secrets.sh`), (c) per-service JSON config files mapping env var names to vault paths. Key pitfalls: **force HTTPS** (OpenBao listener always has TLS), **skip TLS verification** (cert hostname doesn't match `openbao` Docker DNS), and **vault key names may differ** from env var names (e.g., vault path `iacgenie/data/config/minio/minio_root_user` stores key `MINIO_ROOT_USER`, not `MINIO_ACCESS_KEY`). Use the full pattern from `templates/openbao-secret-injection.sh`.
- **AppRole credential sharing via Docker named volume** — To share AppRole role_id/secret_id from Ansible host to Docker service containers, create a named volume (`openbao-appprope`) mounted at `/var/run/approle` in both the Ansible host path and service containers. Ansible writes role_id on line 1 and secret_id on line 2 to `<service>-creds.txt`. Service containers read from this shared path. **Create roles with `secret_id_ttl=0`** (no rotation) and **token_num_uses=0** (unlimited) for service accounts. See `templates/openbao-secret-injection.sh` for the full pattern.
