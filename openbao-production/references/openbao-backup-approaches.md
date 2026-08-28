# Backup Approach Guide

## When to Use Each Method

| Scenario | Method | Priority |
|----------|--------|----------|
| Raft volume bind-mounted to host | Copy `raft.db` from host + config files | 1 (primary) |
| Dev mode / no Raft bind mount | `docker exec` tar export from container | 2 |
| File backend storage | Export `/openbao/file/` from container | 3 |
| Consul / other backend | Export the backend's data via its API/tools | N/A |
| Both host mount AND container data | Combine both sources | Best effort |

## Method 1: Host Bind Mount (Recommended)

```bash
# Copy raft data
cp ~/docker/iacgenie/openbao_raft/raft.db ~/backups/raft_$(date +%Y%m%d).db

# Copy config
cp ~/docker/iacgenie/openbao-prod.hcl ~/backups/config_$(date +%Y%m%d).hcl

# Or create full tarball
cd ~/docker/iacgenie
tar czf ~/backups/openbao_$(date +%Y%m%d).tar.gz \
  openbao_raft/raft.db \
  openbao-prod.hcl \
  openbao_data/certs/ \
  openbao_data/audit/
```

**Pros:** Fast, reliable, no API permissions needed
**Cons:** Requires pre-configured bind mounts

## Method 2: Docker Exec Tar Export

Use when data is inside the container with no host bind mount:

```bash
# Export entire OpenBao data directory
mkdir -p /tmp/openbao_backup
docker exec iacgenie-openbao tar czf - /openbao/ | tar xzf - -C /tmp/openbao_backup

# Export specific subdirectory
docker exec iacgenie-openbao tar czf - /openbao/raft/ | tar xzf - -C /tmp/openbao_backup/raft/
```

**Pros:** Works regardless of bind mount setup
**Cons:** Slower, requires container to be running and accessible

## Method 3: API Snapshot (Secondary)

```bash
export VAULT_TOKEN=***
curl --insecure --header "X-Vault-Token: $VAULT_TOKEN" \
  -L https://127.0.0.1:8200/v1/sys/storage/raft/snapshot \
  -o /tmp/openbao_snapshot.snap
```

**Pros:** Consistent snapshot, includes all secrets
**Cons:** May fail with permission errors on restricted containers; requires auth token

## Full Backup Script Pattern

See the updated `backup_openbao.py` for a comprehensive approach that:
1. Checks host-side Raft data
2. Checks host-side config files
3. Tries Docker exec exports for Raft, file, and data directories
4. Backs up init keys if present
5. Creates a single tarball with all found data
6. Retains last 10 backups
