# Infrastructure Credential Audit Pattern

## When to Use

When asked to audit, review, or document authentication credentials for any service running in the IacGenie infrastructure (Docker containers on the VM).

## The Audit Workflow

### Step 1: Inventory Docker Containers

```bash
ssh mkanavi@192.168.0.118 "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
```

### Step 2: Read the .env Files

The primary credential source is `/home/mkanavi/docker/iacgenie/.env`. Secondary: `.env.monitoring`, per-service `.env` files.

```bash
ssh mkanavi@192.168.0.118 "cat /home/mkanavi/docker/iacgenie/.env"
ssh mkanavi@192.168.0.118 "cat /home/mkanavi/docker/iacgenie/.env.monitoring"
```

### Step 3: Extract Individual Values

Some values are masked (`***`) in the `.env` file. Extract with `cut`:

```bash
# For non-masked values:
ssh mkanavi@192.168.0.118 "grep '^PASSWORD=*** /home/mkanavi/docker/iacgenie/.env | cut -d= -f2-"
```

**⚠️ Pitfall:** Many passwords contain `#`, `!`, `*`, `$`, `^`, `&` — shell metacharacters that break `grep` patterns. **Avoid `grep '^KEY=***` — use `cut` after `cat` or Python to parse.**

### Step 4: Cross-Reference with `init_keys.json`

For OpenBao, the `.env` may show a masked token. The `init_keys.json` in the Raft data directory is authoritative:

```bash
ssh mkanavi@192.168.0.118 "cat /home/mkanavi/docker/iacgenie/data/openbao_raft/init_keys.json"
```

### Step 5: Map to Nginx Public URLs

Check the Nginx config to see which services are publicly accessible and through which domain:

```bash
ssh mkanavi@192.168.0.118 "sudo cat /etc/nginx/conf.d/iacgenie.conf"
```

### Step 6: Build the Credential Matrix

| Service | Username | Password | Auth Method | File Location | Public URL |
|---------|----------|----------|-------------|---------------|------------|
| Keycloak | `admin` | from .env | Direct | `docker/iacgenie/.env` | `auth.iacgenie.com` |
| Grafana | `admin` | from .env.monitoring | Direct | `docker/iacgenie/.env.monitoring` | `grafana.iacgenie.com` |
| ... | ... | ... | ... | ... | ... |

## Where Passwords Are Stored

| File | Purpose | Notes |
|------|---------|-------|
| `docker/iacgenie/.env` | Main services (Keycloak, MinIO, Postgres, Redis, Gitea, SearXNG, LightSerp, etc.) | Some values masked as `***` |
| `docker/iacgenie/.env.monitoring` | Grafana admin password | May have truncated display output |
| `docker/iacgenie/data/openbao_raft/init_keys.json` | OpenBao root token + unseal keys | **Canonical source**, not `.env` |
| Ansible `.env.j2` templates | Template defaults (placeholders only) | Use `defaults/main.yml` — mostly empty |
| OpenBao KV v2 | Service tokens, app secrets | Runtime source — read via API |
| `.bash_profile` (VM) | System env vars (Cloudflare API key, etc.) | Not in Docker compose |

## Common Masking Patterns

1. **`***` literal** — The actual token value was replaced with three asterisks in the `.env` file. This is **not** a Python unpacking operator or shell glob — it's the literal text `***`.
2. **Truncated display** — Terminal output may be truncated. `cut -d= -f2-` gets the full value, but the terminal display may still show abbreviated output.
3. **`CHANGE_ME` placeholder** — Default values in Ansible templates. Indicates the value should be set via extra-vars or vault.

## Verification Tips

- **Grafana**: Login at `grafana.iacgenie.com` with username `admin` and password from `.env.monitoring`
- **Keycloak**: Login at `auth.iacgenie.com` with username `admin` and password from `.env`
- **MinIO**: Login at `minio.iacgenie.com` with `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` from `.env`
- **Gitea**: Login at `git.iacgenie.com` with `admin` and `GITEA_ADMIN_PASSWORD` from `.env`
- **OpenBao**: Use root token from `init_keys.json`, not from `.env`
