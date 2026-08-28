# OpenBao Secret Migration Workflow

## Context
Standard workflow for migrating secrets from `.env` files and Ansible defaults into OpenBao KV v2. Based on comprehensive migration across iacgenie, lightserp, and terragenius platforms.

## When to Use
- Setting up OpenBao for the first time on new infrastructure
- Migrating from .env file secrets to centralized vault
- Consolidating multiple service credentials into a single vault

## Prerequisites
- OpenBao server running and accessible
- Admin/root token available (in ~/.bash_profile or via `bao init`)
- Service read-only policies created (see main SKILL.md)

## Step-by-Step Workflow

### 1. Discover existing secrets
```bash
find ~/ ~/projects ~/.hermes/git_clone_dir -name ".env*" -exec grep -il "PASSWORD\|SECRET\|KEY\|TOKEN" {} \;
find iacgenie-platform/infra/ansible/roles/ -name "main.yml" -exec grep -il "password\|secret\|key" {} \;
```

### 2. Map secrets to OpenBao KV paths
Structure: `{mount}/data/services/{service_name}`

```
iacgenie/kv/data/services/
├── iacgenie    postgres    redis    minio
├── keycloak    gitea       searxng  openbao
├── pagezen     nsqd

lightserp/kv/data/services/
terraform/kv/data/services/
```

### 3. Extract live credentials (if VM SSH accessible)
```bash
ssh newvm "docker exec iacgenie_backend env | grep -i 'PASSWORD\|SECRET'"
ssh newvm "cat /home/mkanavi/docker/iacgenie/infra.env"
```

### 4. Store secrets in OpenBao (CRITICAL: use @filename syntax)
```bash
# WRONG - only last field stored:
# bao kv put -mount=iacgenie/kv services/myapp f1="v1" f2="v2"

# CORRECT - JSON file:
echo '{"f1":"v1","f2":"v2"}' > /tmp/fields.json
bao kv put -mount=iacgenie/kv services/myapp @/tmp/fields.json
rm /tmp/fields.json
```

> **CLI bug:** `bao kv put` only stores the first `key=value` pair. Always use `@filename` for multi-field secrets.

### 5. Create read-only service tokens
```bash
bao token create -policy=iacgenie-service -ttl=720h -period=720h -display-name=iacgenie-service
bao token create -policy=lightserp-service -ttl=720h -period=720h -display-name=lightserp-service
bao token create -policy=terraform-service -ttl=720h -period=720h -display-name=terraform-service
```

> **CRITICAL:** Policy name in `-policy=` must EXACTLY match a `bao policy list` entry. Wrong name = token created without access, and it CANNOT be fixed. Always verify first.

### 6. Verify all stored secrets
```bash
bao kv list -prefix=true -mount=iacgenie/kv
bao kv get -format=json -mount=iacgenie/kv services/iacgenie
```

## Troubleshooting

### Cloudflare WAF blocks Python HTTP calls
Route all API calls through `bao` CLI via subprocess:
```python
import subprocess
subprocess.run([bao_bin, "kv", "get", "-format=json", ...])
```

### KV put only stores one field
Known CLI bug. Use `@filename` with JSON instead of `key=value` arguments.

### Token access denied after creation
Verify policy exists: `bao policy list`. Token names and policy names must match exactly.

### SSH to VM unavailable
Only ports 80/443 may be open via firewall. Check with:
```bash
nc -z -w 2 192.168.0.118 22
# or scan: python3 -c "import socket; s=socket.socket(); s.settimeout(2); r=s.connect_ex(('192.168.0.118',22)); print('OPEN' if r==0 else 'CLOSED'); s.close()"
```

## Files Generated
- `shared/docs/SECURITY_REPORT.md` — Main security report
- `shared/docs/openbao/VERIFIED.json` — Pre-SSH verification data
- `shared/docs/openbao/LIVE_VERIFIED.json` — Post-SSH live credential data
- Backup script: `/home/mkanavi/scripts/openbao_backup.sh` on VM
