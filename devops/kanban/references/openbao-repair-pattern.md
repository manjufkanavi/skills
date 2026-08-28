# OpenBao Repair and Hardening Pattern

## When to Use

- User asks to fix unhealthy OpenBao
- OpenBao is sealed and won't unseal
- OpenBao health check failing
- OpenBao permissions or security hardening needed
- Migrating secrets from `.env` into OpenBao
- Adding multi-tenant KV engines

## Common Issues and Fixes

### Issue 1: Unseal CLI Fails (HTTPS vs HTTP Mismatch)

**Symptom:** `docker exec iacgenie_openbao bao operator unseal <key>` returns:
```
http: server gave HTTP response to HTTPS client
```

**Root cause:** The `bao` CLI defaults to HTTPS. If the server is configured with `OPENBAO_ADDR=http://127.0.0.1:8200`, the bare `bao` command tries to connect to port 8201 over HTTPS.

**Fix:** Add `-address=http://127.0.0.1:8200` to all `bao` CLI commands:
```bash
docker exec iacgenie_openbao bao operator unseal -address=http://127.0.0.1:8200 <key>
docker exec iacgenie_openbao bao operator list-seal-status -address=http://127.0.0.1:8200
docker exec iacgenie_openbao bao status -address=http://127.0.0.1:8200
```

**Ansible fix:** In `roles/openbao/tasks/unseal.yml` and all policy/KV/bootstrap tasks, change all API URLs from `https://127.0.0.1:8200` to `http://127.0.0.1:8200` (or use `https://` consistently with `validate_certs: false` for self-signed certs).

### Issue 2: Health Check Returns 503 (Sealed)

**Symptom:** `wget -q -O /dev/null http://127.0.0.1:8200/v1/sys/health` returns 503. Container shows `unhealthy`.

**Root cause:** OpenBao is in sealed state. The HTTP status 503 means "sealed/standby", not a network issue.

**Fix:** 
1. First fix the unseal CLI (Issue 1 above)
2. Then update the docker-compose healthcheck to verify seal status, not just HTTP 200:
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -q -O - http://127.0.0.1:8200/v1/sys/health | grep -q '\"sealed\":false'"]
```

**Diagnostic:**
```bash
docker exec iacgenie_openbao bao operator list-seal-status -address=http://127.0.0.1:8200
# Look for "sealed": true → needs unseal
# Look for "sealed": false → healthy
```

### Issue 3: World-Writable Data Directories

**Symptom:** `drwxrwxrwx` (777) on raft data and backup directories.

**Root cause:** Docker volume mounts inherit wide permissions. OpenBao runs as root inside the container, writing files with mode 777.

**Fix:** Add permission hardening in `roles/openbao/tasks/main.yml`:
```yaml
- name: "OpenBao | Fix raft data ownership and permissions"
  ansible.builtin.file:
    path: "{{ openbao_raft_data_dir }}"
    state: directory
    owner: mkanavi
    group: mkanavi
    mode: "0750"
    recurse: true

- name: "OpenBao | Fix raft DB file permissions"
  ansible.builtin.file:
    path: "{{ item }}"
    mode: "0640"
  loop: "{{ openbao_raft_data_dir }}/raft/*.db"
  failed_when: false
```

### Issue 4: TLS Disabled But Certs Exist on Disk

**Symptom:** TLS certificates present (`ca.crt`, `server.crt`, `server.key`) but `tls_disable = 1` in config.

**Fix:** Update `openbao-prod.hcl`:
```hcl
listener "tcp" {
  address        = "0.0.0.0:8200"
  tls_cert_file  = "/openbao/storage/server.crt"
  tls_key_file   = "/openbao/storage/server.key"
  tls_client_ca_file = "/openbao/storage/ca.crt"
}
```

And update `OPENBAO_ADDR` to `https://` in docker-compose env vars.
Update ansible roles to use `validate_certs: false` (self-signed).

### Issue 5: Missing Multi-Tenant KV Engines

**Symptom:** Only `iacgenie/kv` exists, but `lightserp/*` and `terraform/*` secrets need separate namespaces.

**Fix:** In `roles/openbao/tasks/kv_bootstrap.yml`, add engine mounts:
```yaml
- name: "OpenBao | Enable lightserp/kv engine"
  uri:
    url: "https://127.0.0.1:8200/v1/sys/mounts/lightserp/kv"
    method: POST
    body:
      type: kv
      options:
        version: "2"

- name: "OpenBao | Enable terraform/kv engine"
  uri:
    url: "https://127.0.0.1:8200/v1/sys/mounts/terraform/kv"
    method: POST
    body:
      type: kv
      options:
        version: "2"
```

## Repair Procedure (Order Matters)

1. **Fix unseal CLI** (address flag) → service can be unsealed
2. **Fix health check** (verify seal=false) → service shows healthy
3. **Fix permissions** (750 for dirs, 640 for files) → security hardening
4. **Verify** (restart cycle) → confirms persistence
5. **Enable TLS** (optional, uses existing certs)
6. **Fix routing** (Docker hostname vs 127.0.0.1)
7. **Migrate secrets** (from .env to KV)
8. **Add multi-tenant engines** (isolated namespaces)
9. **Document** (runbook, INFRA-DESIGN.md update)

## Verification Checklist

After any OpenBao repair, verify:
- [ ] `docker inspect --format='{{.State.Health.Status}}' iacgenie_openbao` → `healthy`
- [ ] `bao operator list-seal-status -address=...` → `"sealed": false`
- [ ] `/v1/sys/health` returns HTTP 200 with `"sealed":false`
- [ ] Raft data dir permissions: `750` for dirs, `640` for files
- [ ] Backup dir permissions: `750`
- [ ] Service restart test: `docker stop + docker start` cycle succeeds
- [ ] All KV engines accessible: `bao sys list`
- [ ] Service tokens readable via API

## OpenBao 2.6.0 Notes

- `bao operator unseal` CLI removed — use Python requests PUT to `/v1/sys/unseal` for API-based unseal, OR use the CLI with `-address` flag
- Token discovery: check `init_keys.json` → `new_root_token` field first, then `.vault-token`, then `.env`
- 26-char tokens are valid (some look like garbage but are valid root tokens)
- `tls_disable = 1` means the listener accepts HTTP on port 8200; TLS cert files must still be mounted in the container even when disabled
- Raft storage path must be writable by the OpenBao user (usually root or openbao) inside the container

## OpenBao Behind Nginx — Complete TLS Flip

When OpenBao is behind Nginx (TLS terminated at proxy), the entire TLS stack must be disabled across ALL files. A partial fix causes silent failures.

**Reference:** `references/openbao-tls-proxy-fix-pattern.md` in the `service-security-audit` skill contains the full 11-file checklist.

**Key rule:** After flipping, run these three greps — all must return zero results:
```bash
grep -rn 'https://127.0.0.1:8200' infra/ansible/roles/openbao/
grep -rn 'ssl.create_default_context' infra/ansible/roles/openbao/
grep -rn 'context=_ssl_ctx' infra/ansible/roles/openbao/
```
