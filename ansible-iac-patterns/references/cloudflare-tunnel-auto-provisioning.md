# Cloudflare Tunnel Auto-Provisioning via Ansible

Automates the entire Cloudflare tunnel lifecycle: binary install, account login, tunnel creation, credential placement, config deployment, and service management.

## Prerequisites

A Cloudflare API token with permissions:
- **Zone.Zone > Read**
- **Cloudflare Tunnel > Manage**

Generate at: `https://dash.cloudflare.com/profile/api-tokens`

## Setup

1. **Store the API token** in `group_vars/cloudflare_tunnel.yml`:
   ```yaml
   cloudflared_api_token: "your-token-here"
   ```

2. **Encrypt with Ansible Vault**:
   ```bash
   ansible-vault encrypt group_vars/cloudflare_tunnel.yml
   ```

3. Run the playbook — no manual steps needed.

## Automation Flow (Role Tasks)

| Step | Task | Detail |
|------|------|--------|
| 1 | Check binary | `stat /usr/bin/cloudflared` |
| 2 | Download binary | Fetch from GitHub releases if missing |
| 3 | Install binary | `copy` to `/usr/bin/cloudflared` |
| 4 | Ensure user dir | `mkdir -p /home/mkanavi/.cloudflared` |
| 5 | Check cert.pem | `stat /home/mkanavi/.cloudflared/cert.pem` |
| 6 | Tunnel login | `cloudflared tunnel login` via API token (piped) or interactive fallback |
| 7 | Check creds file | `stat /etc/cloudflared/<name>.json` |
| 8 | Create tunnel | `cloudflared tunnel create <name>` — `args: creates: ...` for idempotency |
| 9 | Move credentials | `mv ~/.cloudflared/<name>.json /etc/cloudflared/<name>.json` |
| 10 | Deploy config | Template `cloudflared.yaml.j2` → `/etc/cloudflared/config.yml` |
| 11 | Deploy service | Template `cloudflared.service.j2` → `/etc/systemd/system/cloudflared.service` |
| 12 | Start service | `systemd: state=started, name=cloudflared` |

## Key Idempotency Patterns

### args: creates: (task skips if file exists)
```yaml
- name: "Cloudflare | Create tunnel"
  ansible.builtin.command: "cloudflared tunnel create {{ cloudflared_tunnel_name }}"
  args:
    creates: /home/mkanavi/.cloudflared/{{ cloudflared_tunnel_name }}.json
  when: not cloudflared_creds.stat.exists
```

### args: creates: with env var (login)
```yaml
- name: "Cloudflare | Tunnel login via API token"
  ansible.builtin.shell: |
    set -euo pipefail
    echo "CfApiToken={{ cloudflared_api_token }}" | cloudflared tunnel login
  environment:
    CF_ACCOUNT_TAG: "{{ cloudflared_account_tag | default('') }}"
  args:
    creates: /home/mkanavi/.cloudflared/cert.pem
  when:
    - cloudflared_api_token is defined
    - cloudflared_api_token != 'CHANGE_ME_IN_VAULT'
    - not cloudflared_cert.stat.exists
```

### Two-path execution (API vs interactive)
```yaml
# Path A: API token provided — automated login
- name: Tunnel login via API token
  when: cloudflared_api_token != 'CHANGE_ME_IN_VAULT'

# Path B: No token — fallback to interactive (prompt required)
- name: Tunnel login — interactive (fallback)
  when: cloudflared_api_token is undefined or == 'CHANGE_ME_IN_VAULT'
  ignore_errors: true
```

## Group Vars Template

```yaml
# group_vars/cloudflare_tunnel.yml
# Encrypt with: ansible-vault encrypt group_vars/cloudflare_tunnel.yml
# Token: https://dash.cloudflare.com/profile/api-tokens
# Permissions: Zone.Zone > Read + Cloudflare Tunnel > Manage
cloudflared_api_token: "CHANGE_ME_IN_VAULT"
cloudflared_account_tag: "{{ lookup('env', 'CF_ACCOUNT_TAG') | default('') }}"
cloudflared_tunnel_name: iacgenie-tunnel
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Cannot determine default origin certificate path` | `~/.cloudflared/cert.pem` missing | Run `cloudflared tunnel login` first |
| `error parsing YAML` in tunnel config | Credentials JSON at wrong path | Ensure `/etc/cloudflared/<name>.json` exists |
| `tunnel already exists` error | `creates:` path differs from where CLI writes | Check CLI output, verify `creates:` path matches |
| Login hangs with API token | Invalid token or wrong permissions | Verify token at https://dash.cloudflare.com/profile/api-tokens |
| `userdir` not found | `/home/mkanavi/.cloudflared` not created | Role creates it — check `owner: mkanavi` |

## When Automation Fails (Manual Recovery)

If the automation cannot proceed (no network, invalid token, permissions issue), fall back to manual steps:

```bash
# 1. Install cloudflared (if not installed)
wget https://github.com/cloudflare/cloudflared/releases/download/2025.6.0/cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/bin/cloudflared
sudo chmod +x /usr/bin/cloudflared

# 2. Login interactively (opens URL in browser)
cloudflared tunnel login

# 3. Create tunnel
cloudflared tunnel create iacgenie-tunnel

# 4. Move credentials
mv ~/.cloudflared/iacgenie-tunnel.json /etc/cloudflared/

# 5. Start service
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared
```

## References

- Cloudflare Tunnel docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Cloudflared CLI reference: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
- API Token creation: https://dash.cloudflare.com/profile/api-tokens
