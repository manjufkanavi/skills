# TLS Admin Pattern — Local HTTPS with Wrong Cert Hostname

## Problem

OpenBao runs with TLS enabled, using a Let's Encrypt cert for `vault.iacgenie.com`.
Admin scripts connect to `https://127.0.0.1:8200` — the cert hostname does NOT match
the connection target. Standard `ssl.create_default_context()` will reject the connection.

## Fix — No-Verify SSL Context

```python
import ssl, urllib.request, json

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

token = "root-token-from-init_keys.json"

# Make API call
req = urllib.request.Request(
    "https://127.0.0.1:8200/v1/sys/health",
    headers={"X-Vault-Token": token}
)
resp = urllib.request.urlopen(req, context=_ssl_ctx)
health = json.loads(resp.read())
print(health)
```

## When This Happens

1. OpenBao HCL has `tls_disable = 0` with Let's Encrypt cert
2. Admin/backup scripts run on the same host as OpenBao, connecting via 127.0.0.1
3. Cloudflare tunnel handles external HTTPS, Nginx proxies to 127.0.0.1:8200
4. Internal scripts need to reach OpenBao via 127.0.0.1:8200 over HTTPS

## Important Notes

- This is SAFE for local connections — no external exposure
- The cert IS valid and IS a real Let's Encrypt cert — just the hostname doesn't match 127.0.0.1
- Never disable TLS in production — only skip hostname verification for local connections
- The OpenBao CLI (`bao`) has its own TLS handling — use `-address=http://127.0.0.1:8200` as a workaround
