# ERR_INVALID_RESPONSE Through Cloudflare Tunnel — Design-Gap vs Drift

**When:** A `*.iacgenie.com` subdomain returns `ERR_INVALID_RESPONSE` in the browser, but DNS resolves to Cloudflare IPs, the app container is Up/healthy, and the cloudflared tunnel shows `Registered tunnel connection` in logs.

**Key insight:** A dry run showing `changed=0` does **NOT** mean the service works. It means *live state == Ansible templates* — which can BOTH be missing the routing. The outage is a **design gap** (the feature never existed in the source of truth), not **config drift** (something diverged from the templates).

## Root cause

Cloudflare edge forwards an origin response it cannot parse as HTML. In the IacGenie stack this happens when:
- No nginx `server_name` block matches the hostname, AND
- No cloudflared tunnel `ingress` rule matches the hostname,
so traffic falls to the catch-all (`server_name _;` → `return 301 https://iacgenie.com`) or to a catch-all returning a JSON 404.

Observed body on the edge: `{"error":"Not found"}` — 22 bytes, `content-type: application/octet-stream`. Cloudflare surfaces this as `ERR_INVALID_RESPONSE`.

## Diagnostic order (all read-only)

```bash
# 1. DNS — must resolve to Cloudflare IPs, NOT the server public IP
dig +short keycloak.iacgenie.com
# expect 104.21.x.x / 172.67.x.x. Public server IP => DNS misconfigured.

# 2. Cloudflare edge response (through the tunnel)
curl -sI https://keycloak.iacgenie.com/
# 404 / application/octet-stream / content-length: 22 => origin returned non-HTML (design gap),
# NOT a tunnel outage. A 301/200 here would point at nginx.

# 3. Direct to nginx (bypass Cloudflare) — does nginx have a vHost for it?
curl -sI -H 'Host: keycloak.iacgenie.com' http://127.0.0.1:80/
# 301 to landing page   => nginx has NO vHost for this hostname (falls to catch-all)
# 200                  => nginx has the vHost (then the problem is upstream/keycloak)

# 4. Dry run — the decisive check
ansible-playbook -i inventory/hosts.ini <playbook> --check --diff -l iacgenie-server
# changed=0  => live matches templates  => DESIGN GAP (routing never existed in templates)
# changed=N  => live diverged           => CONFIG DRIFT (re-run playbook to remediate)
```

## Distinguish the two failure classes

| Signal | Meaning | Fix |
|---|---|---|
| Dry run `changed=0`, service unreachable | **Design gap** — routing never added to templates | Edit Ansible templates, then redeploy |
| Dry run `changed=N`, service unreachable | **Config drift** — live diverged from templates | Re-run the playbook |
| App container `unhealthy`/crash loop | Upstream problem (keycloak/nginx config) | Fix the service, not the routing |

## Fix path (edit Ansible source of truth, then redeploy via Docker)

1. **nginx-container role** (`nginx-unified.conf.j2`): add a dedicated server block mirroring an existing vHost.
2. **cloudflare_tunnel role** (`cloudflared.yaml.j2`): add an **explicit** ingress (don't rely on the catch-all): `hostname: keycloak.iacgenie.com; service: http://127.0.0.1:80`.
3. **keycloak role** (`keycloak.conf.j2`): add `keycloak.iacgenie.com` as a hostname so Keycloak mints correct admin/redirect URLs (it was configured for `auth.iacgenie.com` only).
4. **Re-run the dry run** → it now shows the *exact diff* your edits produce → review → apply → verify end-to-end.

## Observed specifics (IacGenie, 2026-08-26)

- `keycloak.iacgenie.com`: no nginx vHost, no tunnel ingress → catch-all → 404 `{"error":"Not found"}`.
- Keycloak container healthy on `127.0.0.1:8083`; `keycloak.conf` hostname = `auth.iacgenie.com` only.
- cloudflared catch-all rule: `*.iacgenie.com → nginx:80`.
- DNS already pointed to Cloudflare edge (104.21.67.88 / 172.67.219.34) — DNS was not the issue.
