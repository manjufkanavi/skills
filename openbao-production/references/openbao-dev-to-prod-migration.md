# OpenBao: Dev Mode → Production Migration

## Context

OpenBao starts in dev mode (insecure, memory-backed, token auth) and is later
migrated to production mode (TLS, Raft storage, Shamir key sharing). This is a
**stateful migration** — the data survives the restart, but the auth tokens change.

## Key Observations from Session (2026-07-22)

1. **Old dev-mode `.env` tokens become INVALID** after production migration.
   The `OPENBAO_ROOT_TOKEN` and `BAO_DEV_ROOT_TOKEN_ID` from `.env` no longer work.
   The new root token is generated during `sys/init` and stored in `init_keys.json`.

2. **Two bootstrap scripts exist** — use the VM's production script:
   - Repo: `iacgenie/docker/openbao/bootstrap.sh` (dev-mode, KV-v2 only)
   - VM: `/home/mkanavi/docker/iacgenie/bootstrap_openbao.sh` (production, handles init/unseal/seed/status)

3. **Production config replaces dev config** — `openbao-prod.hcl` uses:
   - `listener "tcp"` with TLS enabled (`tls_disable = 0`)
   - `storage "raft"` at `/openbao/raft`
   - `api_addr = "https://..."` (HTTPS, not HTTP)

4. **BusyBox wget inside container** can't handle TLS or custom headers —
   use `curl` from the host or `docker cp` to export certs.

5. **Userpass credential backend** may be enabled during production setup —
   check with: `curl -sk https://vault.iacgenie.com/v1/auth/userpass/users?list=true \
   --header "X-Vault-Token: <token>"`

## Migration Verification Checklist

- [ ] Raft data exists at `/openbao/raft`
- [ ] TLS certs exist at `/openbao/data/certs/` (server.crt, server.key, ca.crt)
- [ ] `openbao-prod.hcl` has `tls_disable = 0` and `storage "raft"`
- [ ] Container command is `server -config=/openbao/data/openbao-prod.hcl`
- [ ] API responds on HTTPS: `curl -sk https://127.0.0.1:8200/v1/sys/health`
- [ ] New root token from `init_keys.json` works: `curl -sk ... --header "X-Vault-Token: <new>"`
- [ ] Old `.env` tokens are documented as stale (don't reuse)
- [ ] `bootstrap_openbao.sh` on VM handles init/unseal/seed/status

## Common Pitfalls

- **Connecting to old token → "permission denied"** — The old dev token is gone.
  Read the new root token from `init_keys.json` or run `bootstrap_openbao.sh status`.
- **Using HTTP instead of HTTPS** — Production OpenBao listens on port 8200 with TLS.
  `curl http://...` will get TLS handshake error. Use `curl -sk https://...`.
- **BusyBox wget vs curl** — Container ships BusyBox wget (no TLS header support).
  Use host-side curl or `docker exec ... wget --no-check-certificate`.
