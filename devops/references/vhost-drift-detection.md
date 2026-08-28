# Nginx VHost server_name Drift Detection

**Pattern:** When a vHost redirects to the wrong service (e.g., gitea redirects to Keycloak login page), the root cause is often a `server_name` mismatch between nginx and other config files.

## Symptoms

- Domain returns 301/302 redirect to unexpected location
- Domain returns 404 when direct access to the backend port returns 200
- Curl with explicit Host header shows different behavior than curl to domain

## Debugging Steps

### 1. Check nginx server_name for the domain
```bash
grep -n 'server_name <domain>' /etc/nginx/conf.d/*.conf
# If output is empty or shows a DIFFERENT server_name, that's the bug
```

### 2. Test with explicit Host header
```bash
# Direct nginx access — bypasses cloudflare
curl -sI http://127.0.0.1:80/ -H 'Host: gitea.iacgenie.com'
# Expected: 200 OK for a working vHost

# Over cloudflare
curl -sI https://gitea.iacgenie.com/
# Expected: 200 OK
```

### 3. Cross-reference all config files
```bash
# Nginx
grep 'server_name' /etc/nginx/conf.d/iacgenie.conf | grep gitea

# Cloudflare tunnel
grep 'gitea' /etc/cloudflared/config.yml

# Keycloak SSO client redirect URI
# Check in Keycloak admin → Clients → gitea → Valid redirect URIs

# Docker compose port bindings
grep -A5 'gitea:' /home/mkanavi/docker/iacgenie/docker-compose.yml | grep ports
```

### 4. Fix the mismatch
```bash
# Update nginx server_name to match the canonical domain name
sudo sed -i 's/server_name git\.iacgenie\.com;/server_name gitea.iacgenie.com;/g' /etc/nginx/conf.d/iacgenie.conf

# Reload nginx (NO reload for cloudflared — use restart)
sudo nginx -t && sudo systemctl reload nginx
```

### 5. Verify
```bash
curl -sL -o /dev/null -w 'HTTP %{http_code} → %{url_effective}\n' https://gitea.iacgenie.com/
curl -sL -o /dev/null -w 'HTTP %{http_code} → %{url_effective}\n' http://127.0.0.1:3000/
```

## Real Example

**Problem:** `gitea.iacgenie.com` → 301 → `auth.iacgenie.com/realms/iacgenie/web-auth/login-page`

**Root cause:** nginx had `server_name git.iacgenie.com;` instead of `server_name gitea.iacgenie.com;`

**Impact:** HTTP 301 from nginx default_server block, then HTTPS fallback to first matching server block (auth.iacgenie.com), which redirects to Keycloak.

**Fix:** `sed -i 's/server_name git\.iacgenie\.com;/server_name gitea.iacgenie.com;/g' /etc/nginx/conf.d/iacgenie.conf`

**Prevention:** When renaming or creating a vHost, update ALL references at once:
- Nginx server_name (both HTTP and HTTPS blocks)
- Cloudflare tunnel ingress rule
- Cloudflared config.yml ingress rule
- Keycloak SSO client redirectUris
- DNS record (if not using wildcard)
- Any hardcoded references in app config
