# iacgenie OpenBao Deployment Context

## VM & Infrastructure

| Item | Value |
|------|-------|
| VM IP | 192.168.0.118 |
| User | mkanavi |
| macOS host | macOS 26.5.2 |
| Docker Compose | v1 (not v2 compose spec) |
| Network | `iacgenie_network` (shared Docker network) |
| Domain | `*.iacgenie.com` via Cloudflare Tunnel |
| Nginx | Reverse proxy on port 443 |

## OpenBao Instance Details

| Parameter | Value |
|-----------|-------|
| Version | 2.6.0 |
| Container | `iacgenie_openbao` (underscore) |
| Image | `quay.io/openbao/openbao:2.6.0` |
| Storage | Raft at `/openbao/raft` (bind-mounted) |
| Unseal | Shamir, auto-unseal **DISABLED** |
| Namespaces | NOT enabled |
| TLS | Self-signed, TLS 1.2+, port 8200 |
| UI | Enabled at `/ui` |
| Node ID | `node1` |
| CLI binary | `/usr/bin/bao` (NOT `vault`) |

## KV Mounts & Policies

| Mount | Policy | Secrets | Status |
|-------|--------|---------|--------|
| `iacgenie/kv` | `iacgenie` | 13+ | Active |
| `lightserp/kv` | `lightserp` | 1+ | Active |
| `terraform/kv` | `terraform` | 1 | Active (was empty, now seeded) |

All policies use capabilities: `create`, `read`, `update`, `delete`, `list` on their respective KV paths.

## Bootstrap Script

Path inside container: `/openbao/scripts/bootstrap_openbao.sh`

```bash
docker exec iacgenie_openbao bash /openbao/scripts/bootstrap_openbao.sh init
docker exec iacgenie_openbao bash /openbao/scripts/bootstrap_openbao.sh unseal
docker exec iacgenie_openbao bash /openbao/scripts/bootstrap_openbao.sh seed
docker exec iacgenie_openbao bash /openbao/scripts/bootstrap_openbao.sh status
```

## Docker Compose (excerpt)

File: `~/docker/iacgenie/docker-compose-unified.yml`

```yaml
services:
  openbao:
    image: quay.io/openbao/openbao:2.6.0
    container_name: iacgenie_openbao
    restart: unless-stopped
    volumes:
      - /home/mkanavi/docker/iacgenie/openbao_raft:/openbao/raft
      - /home/mkanavi/docker/iacgenie/openbao_data:/openbao/data
    environment:
      - OPENBAO_UI=true
    networks:
      - iacgenie_network
```

## Volume Mapping

| Host Path | Container Path | Type | Purpose |
|-----------|---------------|------|---------|
| `openbao_raft/` | `/openbao/raft` | bind mount | Raft DB, snapshots |
| `openbao_data/` | `/openbao/data` | bind mount | Config, certs, audit logs |

## Cron Jobs

| Schedule | Command | Purpose |
|----------|---------|---------|
| `0 */6 * * *` | `python3 /home/mkanavi/docker/iacgenie/scripts/backup_openbao.py backup` | Backup every 6 hours (**NOT** `scheduled`) |
| `0 3 * * *` | `backup_gitea.sh` | Gitea daily backup |

## .env Variables

```
OPENBAO_ROOT_TOKEN=***
OPENBAO_ADMIN_PASSWORD=***
IACGENIE_OPENBAO_TOKEN=***
LIGHTSERP_OPENBAO_TOKEN=***
TERRAFORM_OPENBAO_TOKEN=***
OPENBAO_AUTO_UNSEAL=False
```

## Critical Token Information

- **Root token**: MUST be 64+ characters. If truncated to ~26 chars, it is INVALID.
- **Admin userpass**: Username `admin`, password from `.env`. Login via `/v1/auth/userpass/login/admin`.
- **Project tokens**: Generated with per-project policies. Each token has `list` and `read` on its KV prefix.
- **Initial terraform KV was empty**: Required creating at least one secret before the token could enumerate the mount.

## Docker Compose Commands

```bash
# Force-recreate (required after .env changes — restart does NOT re-read env)
docker compose -f docker-compose-unified.yml up -d --force-recreate openbao
```

## Backup Inventory

| Type | Count | Notes |
|------|-------|-------|
| Snapshots (.snap) | 44 | All 0 bytes — API returns 403, all attempts when sealed |
| Raft DB copies (vault.db-*) | 89 | ~33 MB each, from host bind mount |
| Config backups (.hcl) | 16 | 281 bytes each |
| **Total** | | **~1,425 MB** |

Note: The 0-byte snapshot files indicate backup failures (sealed state or API errors). The Raft DB copies are the reliable backup method on this deployment.
