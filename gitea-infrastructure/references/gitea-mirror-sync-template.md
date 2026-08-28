# Gitea → GitHub Mirror Sync (Pull Mirror)

This script periodically pulls from GitHub and updates Gitea's main branch when diverged. It's the recommended approach when the Gitea mirrors API returns 404.

## Setup

1. **Deploy keys:** Each Gitea repo needs a deploy key added to the corresponding GitHub repo (for read access). See `references/push-mirror-database.md`.

2. **Gitea user:** Ensure the Gitea admin username is correct — it may NOT be `admin`. Check with:
   ```bash
   docker exec iacgenie-gitea gitea admin user list
   ```

3. **Install the sync script:**
   ```bash
   scp sync-gitea-mirrors.sh mkanavi@192.168.0.118:/home/mkanavi/bin/
   chmod +x /home/mkanavi/bin/sync-gitea-mirrors.sh
   ```

## Cron Setup

Run every 5-15 minutes via cron on the VM:
```bash
*/5 * * * * env -i HOME=/home/mkanavi PATH=/usr/bin:/usr/sbin:/bin:/sbin /home/mkanavi/bin/sync-gitea-mirrors.sh >> /var/log/gitea-sync-cron.log 2>&1
```

**Critical:** The `env -i` is REQUIRED on macOS. Without it, `TMPDIR=/var/folders/...` inherited from the cron environment causes `mktemp` to fail because the mkanavi user can't write there.

## How It Works

1. For each repo (iacgenie, lightserp, iacgenie-unified-infra):
   - Uses the correct SSH deploy key to clone GitHub as bare
   - Compares GitHub's `main` SHA with Gitea's `main` SHA
   - If different, updates Gitea's ref to match GitHub's HEAD
   - Logs: `[MIRRORED]` or `[UP-TO-DATE]` or `[FAIL]`

2. A log file at `/var/log/gitea-sync.log` tracks all operations with timestamps.

## Known Limitations

- **One-directional:** GitHub → Gitea only. Pushes to Gitea do NOT mirror back to GitHub.
- **No merge conflicts:** Since Gitea simply adopts GitHub's main branch SHA, any local changes made directly in Gitea will be overwritten on next sync.
- **API mismatch after DB restore:** After restoring an old backup DB, some Gitea API endpoints (commits, git refs) may return 404. This script bypasses the API entirely by using `git` commands on bare repos.

## Quick Reference

| Repo | SSH Key | GitHub URL |
|------|---------|------------|
| iacgenie | `~/.ssh/gitea_iacgenie_deploy_key` | `git@github.com:manjufkanavi/iacgenie.git` |
| lightserp | `~/.ssh/gitea_lightserv_deploy_key` | `git@github.com:manjufkanavi/lightserp.git` |
| iacgenie-unified-infra | `~/.ssh/gitea_iacgenie-unified-infra_deploy_key` | `git@github.com:manjufkanavi/iacgenie-unified-infra.git` |
