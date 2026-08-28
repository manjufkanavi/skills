# IacGenie OpenBao — VM-Specific Quirks

This file documents quirks specific to the IacGenie VM (192.168.0.118) OpenBao deployment, as discovered during operations.

## Container Name

**Actual:** `iacgenie_openbao` (underscore)
**NOT:** `iacgenie-openbao` (hyphen)

Always verify with `docker ps | grep openbao` before running `docker exec` commands.

## CLI Binary Path

**This VM's OpenBao 2.6.0 image uses `/usr/bin/bao`** (the binary was renamed from `vault` to `bao`).

```bash
# On this VM:
docker exec iacgenie_openbao /usr/bin/bao operator health-check
docker exec iacgenie_openbao /usr/bin/bao operator unseal <key>
```

Some older images or custom builds may still use `/usr/bin/vault` or `/usr/bin/openbao`. Always verify:
```bash
docker exec iacgenie_openbao find / -name 'bao' -o -name 'vault' -o -name 'openbao' -type f 2>/dev/null | head -5
```

## API Snapshot Endpoint Returns 403

The streaming API endpoint `GET /v1/sys/storage/raft/snapshot` consistently returns HTTP 403 Forbidden on this deployment. The backup script falls back to raw Raft DB copy, which succeeds.

**Verification:** After running `backup_openbao.py backup`, check:
```bash
ls -la /home/mkanavi/docker/iacgenie/openbao_raft/backups/
```
- The `.snap` file may be 0 bytes (API failed)
- The `vault.db-*` file should be ~33 MB (raw copy succeeded)
- **Trust the Raft DB copy** if it has content; ignore 0-byte snapshots

## Root Token Masking in .env

The token line in `.env` looks like: `OPENBAO_ROOT_TOKEN=***` — `***` prefix (if present) is literal masking text, not a shell wildcard. `grep 'OPENBAO_ROOT_TOKEN=***'` will fail because `***` is not a glob pattern. Parse with Python:

```python
if line.startswith('OPENBAO_ROOT_TOKEN=***'):
    val = line.split('=', 1)[1].strip("'\"")
```

## Config File Location

`openbao-prod.hcl` may NOT be at `~/docker/iacgenie/openbao_raft/../openbao-prod.hcl`.
The backup script's config lookup may fail — verify with:
```bash
docker exec iacgenie_openbao cat /openbao/config/openbao-prod.hcl 2>&1
find ~/docker/iacgenie -name 'openbao-prod.hcl' 2>&1
```

## Unseal Key Pattern

Shamir threshold t=2, n=3. First key (index 0) may return HTTP 400 due to base64 `+`/`/` URL encoding. Start from key 1 (second key):

```python
# Skip key 0; use keys [1] and [2]
for key in unseal_keys[1:3]:
    requests.put(f"http://127.0.0.1:8200/v1/sys/unseal", json={"key": key})
```

## Auto-Unseal Disabled

**`OPENBAO_AUTO_UNSEAL=False`** in `.env`. OpenBao starts sealed after each container restart. Unseal keys must be provided manually.

**Impact on automated backups:** The `backup_openbao.py` script checks `GET /v1/sys/seal-status` and **aborts immediately** if sealed. All previous snapshot attempts when sealed produced 0-byte files.

**Backup diagnostic:** If all snapshot files in the backup directory are 0 bytes, OpenBao was likely sealed. Check: `curl -s http://127.0.0.1:8200/v1/sys/seal-status | python3 -m json.tool`

## Backup Script Arguments

The script accepts `backup`, `status`, or `restore` — **NOT** `scheduled`.
Cron entry should call: `python3 /home/mkanavi/docker/iacgenie/scripts/backup_openbao.py backup`
Not: `python3 /home/mkanavi/docker/iacgenie/scripts/backup_openbao.py scheduled` (rejected)
