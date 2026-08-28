# Unified Nginx Template Pattern

## When to use
When the live nginx config was manually deployed (not from Ansible template) or when the Ansible template is stub/outdated. Replace a stub template with a complete config generated from the live VM.

## Workflow
1. Dump live config: `ssh newvm "cat /etc/nginx/conf.d/iacgenie.conf" > /tmp/full.conf`
2. Render Ansible template locally: `python3 -c "import jinja2; ..."` → validate it compiles
3. Patch template with any new vHosts (e.g., platform, lightserp)
4. Replace template with full config (from live dump + patches)
5. Render again → `scp` to VM → `sudo cp` → `sudo nginx -t` → `sudo nginx -s reload`

## Key structural decisions
- **HTTP section**: separate server blocks per vHost (one per subdomain) — avoids duplicate `location /` errors in proxy pass mode
- **HTTPS section**: separate server blocks per vHost with full SSL + security headers
- **Catch-all**: HTTP `server { listen 80 default_server; return 301 https://$host }` for external users; HTTPS catch-all returns 404
- **Root handlers**: use `location = /` (exact match) for root-level redirects/405s, then `location /` for proxy. The `=` prefix gives it higher priority.

## Common root handler patterns
- **API root (no backend handler)**: `location = / { return 405 '{"message":"API root not available"}'; }`
- **Tool root (redirect to main app)**: `location = / { return 302 https://app.example.com; }`
- **UI root (proxy to frontend)**: `location / { proxy_pass http://127.0.0.1:3001; }`

## File naming convention
- Live config: `/etc/nginx/conf.d/iacgenie.conf`
- Ansible template: `templates/nginx-unified.conf.j2`
- Ansible task deploy dest: `/etc/nginx/conf.d/iacgenie.conf` (MUST match live file name)
- Backup: `iacgenie.conf.bak` (NOT loaded — trailing `.bak` excluded from `*.conf` glob)

## CORS with nginx
- Server-level `add_header 'Access-Control-Allow-Origin' '*' always;` works for simple responses
- `if ($request_method = 'OPTIONS') { return 204; }` must be inside `location /` block, NOT at server level
- CORS headers in exact-match location: must explicitly `add_header` for each header in that location block
