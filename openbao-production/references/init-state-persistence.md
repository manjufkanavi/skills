# Init State Persistence

OpenBao/Vault stores init state in multiple places. When reinitializing, delete ALL:

| Path | Description | Criticality |
|------|-------------|-------------|
| `<raft_parent>/vault.db` | BoltDB with raft metadata + init state | **CRITICAL** — most commonly missed |
| `<raft_parent>/raft/raft.db` | Raft consensus database | High |
| `<raft_parent>/init_keys.json` | Manually saved init keys | Low |
| `<data_dir>/vault.db` | BoltDB (legacy) | Low |

Example (IacGenie):
```
openbao_raft/vault.db            ← MUST DELETE (init state)
openbao_raft/raft/raft.db        ← MUST DELETE
openbao_raft/init_keys.json      ← MUST DELETE
openbao_data/vault.db            ← DELETE if exists
```

Detection:
```bash
find /openbao_raft/ /openbao_data/ \( -name "*.db" -o -name "*.bolt" -o -name "init_keys.json" \) -print
```

Common mistake: only wiping raft.db → vault.db still has init state → `{"initialized": true}` on restart.