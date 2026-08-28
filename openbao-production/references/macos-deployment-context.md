# macOS Deployment Context

## Environment

| Item | Value |
|------|-------|
| Host | Manjunaths-Mac-Studio (macOS 26.5.2) |
| Home | /Users/manjunathkanavi |
| Docker | 29.2.1 |
| Compose | v5.1.0 |

## Key Difference from Linux VM

The **Linux VM** (192.168.0.118, user mkanavi) is the production OpenBao server.
The **Mac Studio** is a development/local management host.

| Aspect | Linux VM | Mac Studio |
|--------|----------|------------|
| OpenBao path | `/home/mkanavi/docker/iacgenie/` | `~/docker/iacgenie/` |
| SSH access | Direct (root user) | Local (user user) |
| Docker socket | Via ssh or direct | Local socket |
| OpenBao running | Yes (production) | No (not deployed locally) |
| Backup scripts | `/home/mkanavi/docker/iacgenie/scripts/openbao-backup.sh` | `~/docker/iacgenie/backup_openbao.py` (local copy) |
| .env file | `/home/mkanavi/docker/iacgenie/.env` | Does not exist locally |

## Diagnostic Checklist When Backup Fails on Mac

If a backup script fails with "No backup data found" on the Mac:

1. **Check if the script targets the right environment**: `ls -la ~/docker/iacgenie/openbao_raft/` — if empty, OpenBao isn't running locally (expected).
2. **Check if OpenBao is running**: `docker ps | grep openbao` — if nothing shows, no local instance.
3. **For production backup**: SSH to the VM or run the backup script on the VM itself.
4. **Never assume failure = broken OpenBao** when running on the Mac Studio. The scripts are written for the Linux VM.

## Files on Mac Studio

| File | Path | Purpose |
|------|------|---------|
| Backup script | `~/docker/iacgenie/backup_openbao.py` | macOS-compatible Python backup |
| Bootstrap script | `~/docker/iacgenie/bootstrap_openbao.sh` | Init/unseal/seed |
| Deploy script | `~/docker/iacgenie/deploy_openbao.sh` | Docker compose deploy |
| OpenBao config | `~/docker/iacgenie/openbao-prod.hcl` | Raft storage config |
| Client script | `~/docker/iacgenie/openbao_client.py` | Python API client |
| Update script | `~/docker/iacgenie/update_openbao.py` | Config updates |
| Old backup script | `~/docker/iacgenie/vault_backup.sh` | Legacy bash backup (has Linux paths) |
| Raft dir | `~/docker/iacgenie/openbao_raft/` | Bind mount target (empty if not running) |
| Backups dir | `~/docker/iacgenie/openbao_raft/backups/` | Backup storage (empty) |
