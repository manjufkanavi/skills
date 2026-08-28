# OpenBao Nginx Proxy: HTTPS vs HTTP Pitfall

**Date:** 2026-08-14

## Problem

Nginx vHost for `vault.iacgenie.com` was configured with:
```nginx
proxy_pass https://127.0.0.1:8200;
```

This caused a TLS handshake failure because:
1. Cloudflare terminates TLS → sends HTTP to Cloudflared
2. Cloudflared forwards to Nginx on port 80 → Nginx 443 SSL block matches
3. Nginx tries `proxy_pass https://127.0.0.1:8200` → Nginx initiates TLS handshake
4. OpenBao on port 8200 only serves HTTP → "Client sent an HTTP request to an HTTPS server"
5. Browser receives the error → shows TLS error page

## Fix

Change `proxy_pass https://127.0.0.1:8200;` → `proxy_pass http://127.0.0.1:8200;`

## General Rule

When Nginx terminates TLS at the edge:
- `proxy_pass https://` → use when backend serves HTTPS (has its own TLS cert)
- `proxy_pass http://` → use when backend serves HTTP (Nginx handles TLS)

**OpenBao serves HTTP internally only** — never use `https://` in proxy_pass for OpenBao.
Same applies to: Keycloak (8080), Postgres (no HTTP), Redis (no HTTP), MinIO (internal HTTP).
