# OpenBao Health Check TLS Mismatch

## Problem
When the deployed `openbao-prod.hcl` has `tls_disable = 0` (TLS enabled) but the Docker compose health check uses `http://127.0.0.1:8200`, the container goes unhealthy. This is a common deployment drift where the config file diverges from the template.

## Symptoms
- `docker ps` shows `unhealthy` for `iacgenie_openbao`
- Container logs: `http: TLS handshake error from 127.0.0.1:X: client sent an HTTP request to an HTTPS server`
- Health check returns: `wget: server returned error: HTTP/1.0 400 Bad Request`
- Nginx proxy to `http://127.0.0.1:8200` fails to establish TLS between nginx and OpenBao
- `proxy_ssl_server_name on` and `proxy_ssl_verify off` in nginx become **no-ops** because proxy_pass is `http://`

## Diagnosis
```bash
# 1. Check deployed config
grep tls_disable /home/mkanavi/docker/iacgenie/data/openbao/openbao-prod.hcl

# 2. Check ansible template
grep tls_disable ~/iacgenie-platform/infra/ansible/roles/openbao/templates/openbao-prod.hcl.j2

# 3. Check health check in running container
docker inspect iacgenie_openbao --format "{{.Config.Healthcheck.Test}}"

# 4. Check logs for TLS errors
docker logs iacgenie_openbao 2>&1 | grep "TLS handshake" | tail -5

# 5. Test HTTP vs HTTPS manually (inside container)
docker exec iacgenie_openbao sh -c "wget --no-check-certificate -q -O - http://127.0.0.1:8200/v1/sys/health 2>&1 || echo 'HTTP FAIL'"
docker exec iacgenie_openbao sh -c "wget --no-check-certificate -q -O - https://127.0.0.1:8200/v1/sys/health 2>&1 || echo 'HTTPS FAIL'"
```

## Root Cause
The ansible template `openbao-prod.hcl.j2` conditionally sets `tls_disable` based on a variable `openbao_tls_enabled`. However:
- The deployed file was manually edited (or earlier deploy run without the variable)
- The file shows `tls_disable = 0` but should be `tls_disable = 1` for HTTP/HTTP access
- The HCL config file at `/data/openbao/openbao-prod.hcl` is the authoritative one (referenced by compose command)

## Fix

### Option A: Disable TLS on OpenBao (recommended — TLS terminates at Nginx)
1. Update the ansible template `openbao-prod.hcl.j2`:
```hcl
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = 1
}
api_addr     = "http://127.0.0.1:8200"
cluster_addr = "http://127.0.0.1:8201"
```
2. Run ansible playbook to deploy
3. Restart OpenBao: `docker compose up -d openbao`

### Option B: Keep TLS, Fix Health Check
If TLS must remain enabled (direct access use case):
1. Update compose health check:
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget --no-check-certificate -q -O /dev/null https://127.0.0.1:8200/v1/sys/health"]
```
2. Update nginx proxy_pass to `https://127.0.0.1:8200` with `proxy_ssl_verify off`

## Prevention
- The ansible `openbao-prod.hcl.j2` template defaults `openbao_tls_enabled` to `false`
- Always verify the deployed file matches the template after any config changes
- The ansible `openbao` role should ensure both deploy paths get consistent configs:
  - `/home/mkanavi/docker/iacgenie/openbao_raft/openbao-prod.hcl`
  - `/home/mkanavi/docker/iacgenie/data/openbao/openbao-prod.hcl` (authoritative)
