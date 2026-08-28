# Multi-Template Coordinated Deployment

## When to use
When fixing 5+ templates simultaneously across nginx, docker-compose, cloudflare, openbao, keycloak, and ansible. Typical scenario: resolving infrastructure failures that span multiple services.

## Workflow

### 1. Read all templates first
Before making any changes, read every template you'll modify:
- `nginx/templates/reverse-proxy.conf.j2`
- `docker-compose-generator/templates/docker-compose.yml.j2`
- `cloudflare_tunnel/templates/cloudflared.yaml.j2`
- `keycloak/defaults/main.yml`
- `openbao/tasks/kv_bootstrap.yml`
- `docker-compose-generator/templates/.env.j2`

### 2. Identify changes needed per template
| Template | Typical Changes |
|----------|----------------|
| nginx | proxy_pass fixes, port changes, vHost renames |
| docker-compose | New services, port changes, command args |
| cloudflare | Hostname changes, service key renames |
| keycloak | New clients, redirect URIs |
| openbao | New KV seeds, credential vars |
| .env | New env vars for new services |
| ansible | New roles, role ordering |

### 3. Apply patches in dependency order
1. docker-compose.yml.j2 — defines what runs
2. nginx reverse-proxy.conf.j2 — routes traffic to what runs
3. cloudflared.yaml.j2 — tunnel routing
4. keycloak defaults/main.yml — client definitions
5. openbao kv_bootstrap.yml — KV seeding
6. .env.j2 — env vars
7. ansible playbook — role ordering and task addition

### 4. Build and deploy auth wrapper
- Ensure `shared-auth-wrapper/` build context exists
- Symlink in docker-compose directory
- Build context must have Dockerfile + server.py
- Deploy via ansible (auth-wrapper role)

### 5. Deploy via Ansible
```bash
ansible-playbook playbooks/services.yml
```

## Common pitfalls

- **Port conflicts**: New services may conflict with existing ports. Check `docker ps` before assigning ports.
- **Keycloak client not created**: The client setup script must run after Keycloak is running. It gets an admin token via admin-cli login.
- **X-Service header mismatch**: Nginx must set the correct `X-Service` header matching the auth wrapper's expected backend address.
- **OpenBao KV path mismatch**: New KV paths must match what the services expect when reading from KV.
