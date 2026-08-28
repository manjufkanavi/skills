# Session Notes — 2026-08-16 OpenBao Backup

## Context
Cron job triggered `backup_openbao.py scheduled` on IacGenie VM (192.168.0.118).

## Issues Encountered & Resolved

### Issue 1: Wrong Action Argument
- **Error:** `backup_openbao.py: error: argument action: invalid choice: 'scheduled'`
- **Fix:** Use `backup` action, not `scheduled`
- **Already documented in:** `references/openbao-backup-args.md`

### Issue 2: OpenBao Unreachable from Host
- **Error:** `Connection refused` on `http://127.0.0.1:8200`
- **Root cause:** Container uses bridge network (`iacgenie_iacgenie-backend`), NOT host mode, despite compose file declaring `network_mode: host`
- **Diagnosis:** `ss -tlnp | grep 8200` showed nothing on host; `docker exec wget` inside container worked
- **Fix:** Patched script BAO_ADDR to container bridge IP (172.29.1.8), then used `docker exec wget --header` pattern instead

### Issue 3: Container User Mismatch
- **Compose says:** `user: "1000:1000"`
- **Actual:** Container runs as `100:1000` (Docker user namespace remapping)
- **Symptom:** `open /openbao/raft/vault.db: permission denied` crash loop
- **Fix:** `sudo chown -R 100:1000 /home/mkanavi/docker/iacgenie/openbao_raft/`
- **Already documented in:** "Docker User Namespace Override" pitfall

### Issue 4: BusyBox wget Syntax
- **Inside container:** wget is BusyBox v1.37.0, uses `--header` not `-H`
- **Pattern:** `wget -q -O - URL --header='Header: value'`

## Backup Result
- **Snapshot:** `openbao-snapshot-20260816T162132Z.snap` — 45,596 bytes
- **SHA256:** `80f13137da364ca0b109667fb76c7ad14fc5e1e3a735d4699b340d1970735862`
- **vault.db copy:** `vault.db-20260816T162208Z` — 16,801,792 bytes
- **Config copy:** `openbao-config-20260816T162208Z.hcl` — 1,211 bytes
- **Location:** `/home/mkanavi/docker/iacgenie/openbao_raft/backups/`
- **Status:** SUCCESS

## Skills Updated
- `openbao-production`: Added "Compose Network Mode Mismatch" pitfall
- `openbao-production`: Added BusyBox wget fallback section to backup fallback
- `openbao-production`: Added troubleshooting decision tree step for host API reachability
- `openbao-production`: Added new reference file `references/openbao-busybox-wget-pattern.md`
