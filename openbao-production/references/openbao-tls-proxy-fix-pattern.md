# OpenBao TLS/HTTP Proxy Fix Checklist

When OpenBao runs behind Nginx (TLS terminated at proxy), every component that talks to OpenBao must use HTTP, not HTTPS. This checklist ensures no file is missed.

## Files to Audit

| # | File | What to Change |
|---|------|----------------|
| 1 | `templates/openbao-prod.hcl.j2` | `tls_disable = 1`, remove `tls_cert_file`/`tls_key_file`/`tls_client_ca_file`, change `cluster_addr` and `api_addr` from `https://` to `http://` |
| 2 | `files/prod.hcl` | Same changes as #1 (backup reference copy) |
| 3 | `templates/openbao.service.j2` | `--user 100:1000` for namespace remapping, correct volume paths (`openbao_raft` not `data/openbao_raft`), correct container name |
| 4 | `files/openbao_injector.py` | Default addr → `http://127.0.0.1:8200`, remove `ssl` import, remove `ssl_ctx` params, remove HTTPS upgrade logic |
| 5 | `files/backup_openbao.py` | `BAO_ADDR` → `http://`, remove `_ssl_ctx`, remove `context=_ssl_ctx` from all `urlopen()` calls, remove `import ssl` |
| 6 | `files/seed_openbao_kv.py` | Default `OPENBAO_ADDR` → `http://`, remove `context=ssl.create_default_context()` from `urlopen()`, remove `import ssl` |
| 7 | `files/configs/iacgenie-backend.json` | `openbao_addr` → `http://127.0.0.1:8200` |
| 8 | `files/configs/lightserp-api.json` | `openbao_addr` → `http://127.0.0.1:8200` |
| 9 | `files/configs/iacgenie-lightserp.json` | `openbao_addr` → `http://127.0.0.1:8200` |
| 10 | `docker-compose-unified.yml` | Listener `tls_disable=1`, correct resource limits, correct container name |
| 11 | `files/openbao-health-cron.sh` | Correct compose file name and container name |

## Verification Command

After applying all changes, grep for remaining HTTPS references:

```bash
grep -rn 'https://127.0.0.1:8200' infra/ansible/roles/openbao/
grep -rn 'ssl.create_default_context' infra/ansible/roles/openbao/
grep -rn 'context=_ssl_ctx' infra/ansible/roles/openbao/
```

All three should return zero results. Any match means a file was missed.

## Common Pitfalls

1. **Partial fix** — Only changing `prod.hcl` but leaving `openbao_injector.py` on HTTPS. Services using the injector (backend, lightserp) will fail to start.
2. **Backup script SSL** — `backup_openbao.py` uses SSL context for API calls. If not removed, backup cron jobs fail silently.
3. **Seed script SSL** — `seed_openbao_kv.py` uses SSL for KV writes. Will fail on HTTP endpoint.
4. **Service config JSONs** — The injector reads `openbao_addr` from these JSON files. Must match the HTTP addr.
5. **Systemd template diverges** — The systemd service template must use the same `tls_disable=1` config and correct user namespace mapping.
