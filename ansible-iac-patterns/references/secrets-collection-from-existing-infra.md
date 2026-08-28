# Collecting Secrets from Existing Infrastructure

When running Ansible against a live VM that already has services deployed with
manual `.env` files, collect actual credentials **before** the first playbook
run. This avoids encrypting placeholder values that will be overwritten at
runtime.

## Pattern

Use a Python helper script on the **Ansible control machine** (not the target VM)
to SSH into the VM, extract `.env` values, and output an Ansible `group_vars`
YAML file:

```python
import subprocess

result = subprocess.run(
    ["ssh", "-o", "StrictHostKeyChecking=no",
     f"{user}@{vm_ip}", "cat /path/to/.env"],
    capture_output=True, text=True
)
```

Then map extracted values to Ansible variables:

```yaml
# inventory/group_vars/all.yml
---
# SSH settings
ssh_port: 22
ssh_password_authentication: "no"
ssh_permit_root_login: "no"
ssh_public_keys:
  - ssh-ed25519 AAAA... comment

# Database
postgres_super_password: "real-value-from-env"
postgres_app_password: "real-value-from-env"
redis_password: "real-value-from-env"

# Service credentials
minio_root_password: "real-value-from-env"
openbao_root_token: "real-value-from-env"
keycloak_admin_password: "real-value-from-env"
gitea_admin_password: "real-value-from-env"

# API keys
cloudflare_tunnel_token: "real-value-from-env"
jwt_secret: "real-value-from-env"
```

## Key Rules

1. **Use the .env file the VM actually runs.** Check which `.env` is referenced
   in the Docker Compose file (`env_file` directive), not just any `.env` on disk.
2. **Verify with `docker inspect`.** Cross-reference container environment
   variables against the collected values.
3. **Never commit real secrets to git.** If storing the collected file, use
   `ansible-vault encrypt` or store it outside the repo.
4. **Handle missing env vars.** Some services (LightSerp, Gitea) may store
   tokens in OpenBao rather than `.env`. Include fallbacks:
   `lightserp_openbao_token: "{{ vars_dict.get('LIGHTSERP_OPENBAO_TOKEN', 'CHANGE_ME') }}"`.
5. **Postgres `.pgpass`.** If Postgres uses password auth via `.pgpass`,
   include the `.pgpass` file in the deployment (contains host:port:db:user:pass).

## Common `.env` File Locations

| Service | Typical Path |
|---|---|
| IacGenie unified stack | `/home/<user>/docker/<proj>/.env` |
| Cloudflare tunnel | `/home/<user>/docker/<proj>/cloudflared/config.yml` |
| Gitea data | `/home/<user>/docker/<proj>/gitea_data/conf/app.ini` |
| Keycloak import | `/home/<user>/docker/<proj>/keycloak/` realm JSON files |
| OpenBao config | `/home/<user>/docker/<proj>/openbao_data/openbao-prod.hcl` |

## Troubleshooting

- **`ssh` key not found** — Use `--key-file ~/.ssh/newvm_key` or configure
  `~/.ssh/config` with the identity file.
- **Permission denied reading `.env`** — The file may only be readable by root.
  Use `sudo cat` inside the SSH command if needed.
- **Ansible YAML duplicate keys** — Be careful when multiple sections define
  the same variable (e.g., `docker_network_name` in both Docker and Cloudflare
  sections). Only one value survives.
