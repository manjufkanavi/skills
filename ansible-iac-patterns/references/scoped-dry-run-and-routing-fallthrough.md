# Scoped Dry-Run & Nginx Routing-Fallthrough (IacGenie)

Session-specific technique for safely validating Ansible changes against a live VM, and diagnosing "site unreachable" subdomain outages.

## Part 1 — Scoped Dry-Run (identify the diff without touching production)

Goal: show exactly what Ansible *would* write to the live server, read-only, before applying.

### Why not just `ansible-playbook --check --diff site.yml`
- Full site runs every role, including roles with **network-hanging shell tasks** (e.g. the keycloak role's "Set up auth-wrapper client" task runs a Python script that opens a connection to OpenBao/keycloak and hangs).
- `ansible-playbook` has **no `--stop-at-task`** flag (only `--start-at-task`), so you can't stop mid-playbook.

### Technique: temporary scoped playbook
Create a throwaway playbook that `include_role`s only the config-generating roles you care about, run with `--check --diff --limit <host>`, then delete it.

```yaml
# playbooks/_tmp_dryrun.yml (temporary — delete after use)
- hosts: all
  become: true
  serial: 1
  gather_facts: false
  tasks:
    - name: "DRYRUN | nginx-container role"
      ansible.builtin.include_role: { name: nginx-container }
    - name: "DRYRUN | cloudflare_tunnel role"
      ansible.builtin.include_role: { name: cloudflare_tunnel }
```

```bash
ansible-playbook -i inventory/hosts.ini playbooks/_tmp_dryrun.yml --check --diff --limit iacgenie-server
```

Omit network-hanging roles (keycloak's client-setup shell) from the scoped playbook — the module still *executes* the command in dry-run, so it hangs.

### Interpreting `changed=0`
`changed=0` means **live matches the templates** — but that can be a *design gap*, not "no drift". If live == templates and both simply lack a routing rule, the subdomain won't work even though the dry-run shows zero changes. **Always cross-check `changed=0` against whether the target hostname has an nginx `server_name` + a cloudflared ingress.** See Part 2.

## Part 2 — Routing-fallthrough outage (subdomain → ERR_INVALID_RESPONSE / 404)

### Root cause pattern
When a public subdomain (e.g. `keycloak.iacgenie.com`) has **no matching nginx `server_name` block`, requests fall through to nginx's catch-all. On IacGenie the catch-all is:

```nginx
server {
    listen 443 ssl default_server;
    server_name _;
    ...
    return 404 '{"error": "Not found"}';
}
```

Cloudflare's tunnel catch-all ingress (`*.iacgenie.com` → nginx:443) forwards that JSON 404. Browsers render it as **`ERR_INVALID_RESPONSE`** (not a normal 404 page) because the body is non-HTML `application/octet-stream`.

### Second failure: stale proxy_pass port
A template may point a vHost at a **dead backend port**. On IacGenie, the old `auth.iacgenie.com` block proxied to `127.0.0.1:9003`, but Keycloak's HTTP actually publishes **host port 8083** (container 8080). Nothing listens on 9003 → even a matching `server_name` fails. **Always verify the real backend port before editing a template:**

```bash
# Confirm what the backend actually returns on a candidate port
docker exec <nginx-container> sh -c "curl -sS -m5 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8083/"
# Keycloak HTTP publishes host port 8083 (container 8080); management iface 9000.
docker ps --filter name=keycloak --format '{{.Names}} {{.Ports}}'
```

### Fix (in Ansible source of truth, then redeploy via Docker)
1. Add a dedicated `server_name <subdomain>;` block in the nginx template (`roles/nginx-container/templates/nginx-unified.conf.j2`) proxying to the **correct host-mapped port** (Keycloak → `8083`).
2. Ensure keycloak's `keycloak.conf.j2` `hostname` matches the public subdomain.
3. Cloudflare tunnel `catch_all *.iacgenie.com` ingress already covers unknown subdomains — **no cloudflared edit needed** for routing; the fix is purely in the nginx vHost template.
4. Redeploy: run the nginx-container (and keycloak) roles **without** `--check`.

### Verification after deploy
```bash
curl -sS -I https://<subdomain>.iacgenie.com/   # expect Keycloak 200/302, NOT 404 / ERR_INVALID_RESPONSE
docker exec <nginx-container> nginx -t           # config still valid
```
