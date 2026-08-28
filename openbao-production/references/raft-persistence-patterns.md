# OpenBao Raft Storage Persistence Patterns

## Storage Layout

In the IacGenie deployment (192.168.0.118), the storage structure is:

### Host Paths

```
/home/mkanavi/docker/iacgenie/openbao_raft/     ← Bind-mounted Raft data
├── vault.db                                     ← Main raft database (Raft logs + KV data)
├── helpers/
└── snapshots/                                   ← Autopilot snapshots
```

### Container Paths

```
/openbao/data/openbao-prod.hcl                   ← Config (bind-mounted)
/openbao/data/raft/                               ← Raft data (bind-mounted from host)
/openbao/data/certs/                              ← TLS certs (bind-mounted from host)
/openbao/data/service_tokens/                     ← Service tokens (bind-mounted from host)
/openbao/logs/openbao.log                         ← Logs (writeable container layer)
```

### Key Insight: Raft Data Lives in the Raft Directory, NOT /openbao/data

The `vault.db` and all raft state is stored under `/openbao/data/raft/` inside the container,
which is bind-mounted from the host. This is CORRECT for persistence — the host directory
is the source of truth.

### What Needs to Persist

| Item | Location | Persistence Method |
|------|----------|--------------------|
| Raft data (vault.db, helpers, snapshots) | `/openbao/data/raft/` | Bind mount from host |
| Config (`openbao-prod.hcl`) | `/openbao/data/openbao-prod.hcl` | Bind mount from host |
| TLS certs | `/openbao/data/certs/` | Bind mount from host |
| Logs | `/openbao/data/openbao.log` | Container writable (OK to lose) |

### Crash Recovery

1. Verify `raft.db` exists in host path: `ls -la ~/docker/iacgenie/openbao_raft/raft/`
2. Verify ownership: `ls -la ~/docker/iacgenie/openbao_raft/` (must be mkanavi:mkanavi, NOT root)
3. If ownership wrong: `sudo chown -R mkanavi:mkanavi ~/docker/iacgenie/openbao_raft/`
4. Restart: `docker compose -f docker-compose-unified.yml up -d --force-recreate openbao`
5. If sealed: run bootstrap script unseal
6. Verify: `curl -sfk https://127.0.0.1:8200/v1/sys/health`

### Backup Strategy

**Bash script method** (preferred): `/home/mkanavi/docker/iacgenie/scripts/openbao-backup.sh`
- Cron: `0 */6 * * *` (every 6 hours)
- Backups: `/home/mkanavi/docker/iacgenie/openbao_raft/backups/` and `/home/mkanavi/backups/openbao/<ts>/`

### Pitfalls

- **Raft.db ownership**: Files must be owned by `mkanavi:mkanavi` (not root, not openbao uid). If backup/copy changes ownership, OpenBao won't start. Fix: `sudo chown -R mkanavi:mkanavi ~/docker/iacgenie/openbao_raft/`
- **Don't mix up `/openbao/data/` and `/openbao/raft/`**: The raft database is inside `/openbao/raft/` (the host bind mount is at `openbao_raft/`, not `openbao_data/`). Config lives at `/openbao/data/openbao-prod.hcl` (host: `openbao_data/openbao-prod.hcl`).
- **`openbao_raft` is NOT `openbao_data`**: The compose file declares two separate volumes. `openbao_raft` maps to the raft data directory. `openbao_data` maps to config/certs. Confusing these causes `No such file or directory` on config reads.
- **`docker compose restart` vs `up -d --force-recreate`**: Restart does NOT pick up env changes or volume remounts. Always use `up -d --force-recreate` after config or .env changes.
