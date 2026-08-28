# OpenBao Production Hardening — Runbook

## Self-Signed vs Real Cert Detection

```bash
# Check cert details
openssl x509 -in /path/to/certs/server.crt -subject -issuer -dates -noout -ext subjectAltName

# Self-signed: issuer == subject (e.g., both CN=vault.iacgenie.com)
# Real: issuer = "R3" (Let's Encrypt) or similar CA
# Missing SAN extension = clients will reject the cert
```

## Bootstrap Script Unseal Bug (CRITICAL)

The default `bootstrap_openbao.sh` has broken Python string literals in the `do_unseal()` function:

```python
# BROKEN (missing quotes around dict keys and variable):
key1=$(python3 -c "
import json, base64
data = json.loads(open(/init_keys.json).read())
print(base64.b64decode(data[unseal_keys_b64][0]).hex())
")
```

**Fix:** Quote all Python strings properly:
```python
# CORRECT
key1=$(python3 -c "
import json, base64
data = json.loads(open('/init_keys.json').read())
print(base64.b64decode(data['unseal_keys_b64'][0]).hex())
")
```

Symptoms: `NameError: name 'unseal_keys_b64' is not defined` or `FileNotFoundError` when running `bootstrap_openbao.sh unseal`.

## Nginx HTTPS Configuration Pattern

When adding HTTPS to an existing HTTP-only Nginx vhost:

1. Keep the `listen 80` block for ACME challenge (certbot uses it)
2. Add `listen 443 ssl` block with identical proxy settings
3. Point SSL certs to `/etc/letsencrypt/live/<domain>/fullchain.pem` and `privkey.pem`
4. Optionally redirect HTTP→HTTPS (but NOT during cert provisioning — certbot needs port 80)

## Certificate Renewal

Certbot certificates expire every 90 days. Set up automated renewal:

```bash
# Test renewal dry-run (no changes)
certbot renew --dry-run

# Deploy as cron (daily, runs at system boot too via systemd timer)
echo "0 0,12 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx; docker compose -f /path/compose.yml restart iacgenie-openbao'" | crontab -
```

## OpenBao Raft Persistence

OpenBao state persists via Raft storage at a host-mounted directory:
- Data: `openbao_raft/`
- Config: `openbao_data/openbao-prod.hcl`
- Certs: `openbao_data/certs/`

The `restart: unless-stopped` policy in docker-compose ensures the container restarts automatically. However, certs and keys must survive container recreation — always store them in bind-mounted volumes.

## Cloudflare Tunnel Consideration

The Cloudflare Tunnel already routes `*.iacgenie.com` to nginx:80. If you use Cloudflare's "Full" SSL mode, TLS terminates at Cloudflare edge and the tunnel handles encryption end-to-end. For true origin-to-edge security, still provision a real cert on the VM so nginx→cloudflared traffic is also encrypted.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `curl -k https://...` works, browser says "not secure" | Self-signed cert | Provision Let's Encrypt |
| certbot: "DNS problem: TXT record not found" | GoDaddy API not working / DNS propagation | Check API key/secret, wait 2-5 min |
| certbot: "port 80 already in use" | Nginx running | Use `--dns-godaddy` plugin instead of webroot |
| OpenBao won't start after cert change | Wrong cert/key pair mismatch | Verify modulus match: `openssl x509 -noout -modulus -in cert | md5sum` vs `openssl rsa -noout -modulus -in key | md5sum` |
| `docker restart` doesn't pick up new certs | Certs changed but no reload | `docker compose up -d --force-recreate openbao` |