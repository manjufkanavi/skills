# Raft Snapshot Key Mismatch — Diagnostic & Recovery

## Problem

When OpenBao raft data is restored from a snapshot (e.g., `vault.db` copy or `raft.db` restore), the unseal keys embedded in the raft database may differ from `init_keys.json` on disk. The `init_keys.json` file reflects the keys from the initialization time, but if the raft data was restored from a snapshot created at a DIFFERENT time, the keys won't match.

## Symptoms

1. All unseal keys fail with `cipher: message authentication failed`
2. The first key may be "accepted" (returns `1/2 progress`) but the second key always fails
3. This pattern repeats for every key set tried (Aug 9 keys, Aug 7 keys, July 27 keys, etc.)

## Root Cause

The raft database was created or restored from a snapshot at a time when DIFFERENT unseal keys were active. The `init_keys.json` on disk reflects a different initialization than what's actually in the raft data.

Common scenarios:
- Raft data restored from a backup snapshot that was created before the latest reinitialization
- `vault.db` copied from an older backup overwriting the current data
- Multiple `init_keys.json` files with different keys, and the wrong one is being used

## Diagnosis

```bash
# Check when raft data was last modified (vs when init_keys.json was created)
ls -la /home/mkanavi/docker/iacgenie/openbao_raft/vault.db
ls -la /home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json

# Check for raft backups — the snapshot creation time tells you when the data was captured
ls -la /home/mkanavi/docker/iacgenie/openbao_raft/backups/openbao-snapshot-*.snap | tail -5

# Check for vault.db backups — these show when the data was last backed up
ls -la /home/mkanavi/docker/iacgenie/openbao_raft/backups/vault.db-*.db | tail -5

# Check ALL init_keys.json files for different key sets
find /home/mkanavi/docker/iacgenie/ -name 'init_keys.json' -exec echo "=== {} ===" \; -exec cat {} \; 2>/dev/null
```

## The "Accepted" Key Trap

When unsealing, the `bao` CLI may return `1/2 progress` for a key that is NOT actually valid for this sealed state. The "accepted" response only means the key **format** is valid (correct base64 encoding, correct length), NOT that it can decrypt the stored keys.

**Why this is misleading:** It suggests the key is correct and only needs the second key. In reality, the key is rejected during the decryption phase (which happens after the format check), and the "1/2 progress" is a false positive.

**Action:** When this pattern occurs (first key "accepted", second key fails), do NOT try more key combinations. The keys are fundamentally incompatible with the raft data.

## Recovery

**Reinitialize OpenBao** (this is the only option when no key set works):

1. Stop the container: `docker compose stop openbao`
2. Wipe ALL storage data:
   - `<raft_parent>/vault.db`
   - `<raft_parent>/raft/raft.db`
   - `<raft_parent>/init_keys.json`
   - Any `*.bolt`, `*.wal` files
3. Fix ownership to container UID (usually 100)
4. Start the container
5. Run `bao operator init -key-shares=3 -key-threshold=2 -format=json`
6. **Immediately** save the output to `init_keys.json` on the VM (chmod 600)
7. Unseal with the new keys

## Prevention

1. **Always save `init_keys.json` to both the VM and a secure local backup** after every initialization
2. **Verify key compatibility** before restoring raft data: unseal test with one key from the target set before committing the restore
3. **Never restore raft data from a snapshot** without first verifying the snapshot was created with compatible keys
4. **Document key sets** in a file (e.g., `openbao-key-history.txt`) with timestamps and purposes
