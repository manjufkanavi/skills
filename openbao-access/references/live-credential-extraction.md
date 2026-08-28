# Live Credential Extraction Workflow

Extract live credentials from a running VM for OpenBao secret management.

## When to Use

- Initial secret migration (moving from .env files to OpenBao)
- Credential rotation (updating expired passwords)
- Emergency access (when a service credential is unknown)
- Security audit (verifying what's actually deployed)

## Extraction Steps

### 1. SSH to VM

```bash
ssh -o ConnectTimeout=10 newvm "echo SSH_OK"
```

If SSH is refused, the VM may have restarted or SSH service stopped. Check with:
```bash
nc -z -w 2 192.168.0.118 22 && echo "SSH UP" || echo "SSH DOWN"
```

Fallback: access services through Cloudflare Tunnel.

### 2. Extract from Docker Containers

```bash
ssh newvm "docker exec iacgenie_backend env | grep -i PASSWORD"
ssh newvm "docker exec iacgenie_keycloak env | grep -i PASSWORD"
ssh newvm "docker exec iacgenie_minio env | grep -i MINIO"
```

### 3. Read Infrastructure Config Files

```bash
ssh newvm "cat /home/mkanavi/docker/iacgenie/infra.env"
ssh newvm "cat /home/mkanavi/docker/iacgenie/.env"
ssh newvm "cat /home/mkanavi/projects/terragenius/.env 2>/dev/null"
```

### 4. Map to OpenBao KV Paths

| Source | Target Path |
|--------|-------------|
| infra.env POSTGRES_* | iacgenie/kv/data/services/postgres |
| infra.env REDIS_* | iacgenie/kv/data/services/redis |
| infra.env MINIO_* | iacgenie/kv/data/services/minio |
| infra.env KEYCLOAK_* | iacgenie/kv/data/services/keycloak |
| infra.env GITEA_* | iacgenie/kv/data/services/gitea |
| per-service .env | lightserp/kv/data/services/* |
| Docker container env | Various |

### 5. Verify in OpenBao

```bash
bao kv get -format=json -mount=iacgenie/kv services/postgres
```
