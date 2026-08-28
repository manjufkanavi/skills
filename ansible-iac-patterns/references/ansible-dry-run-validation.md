# Ansible Dry-Run Validation

## Purpose

Pre-deployment validation procedure to verify Ansible playbooks are structurally sound before the first real run on a target system.

## Quick Start

```bash
cd iacgenie-deploy
ansible-playbook --check --diff playbooks/bootstrap.yml -i inventory/hosts.yml
ansible-playbook --check --diff playbooks/services.yml -i inventory/hosts.yml
ansible-playbook --check --diff playbooks/site.yml -i inventory/hosts.yml
```

## Handler Gap Detection

```bash
# All notify: references across all roles
grep -rh 'notify:' roles/*/tasks/ 2>/dev/null \
  | sed 's/.*notify: *//' | sed 's/ *$//' | sort -u \
  > /tmp/notified_handlers.txt

# All defined handler names
for f in roles/*/handlers/main.yml; do
  [ -f "$f" ] && grep 'name:' "$f" | sed 's/.*name: *//' | sed 's/ *$//'
done | sort -u > /tmp/defined_handlers.txt

# Missing handlers (in notify but not defined)
comm -23 /tmp/notified_handlers.txt /tmp/defined_handlers.txt
```

### Known Missing Handlers (2026-08-02 Session)

| Missing Handler | Referenced In | Fix |
|----------------|---------------|-----|
| `Reload docker compose` | `roles/docker-compose-generator/tasks/compose.yml:10` | Add to `handlers/main.yml` |
| `Wait for containers to be healthy` | `roles/docker-compose-generator/tasks/deploy.yml:12` | Add to `handlers/main.yml` |

### Known Empty Handler Files (2026-08-02 Session)

| Role | File | Status |
|------|------|--------|
| `docker-compose-generator` | `handlers/main.yml` | Empty stub (2 notify refs, 0 handlers) |
| `user_management` | `handlers/main.yml` | Empty stub (0 notify refs) |

## Inventory Format Fixes

### YAML Inventory (Current — Produces Warnings)
```yaml
all:
  children:
    servers:
      hosts:
        iacgenie-server:
          ansible_host: 192.168.0.118
```
**Warning:** `Failed to parse inventory with 'auto' plugin: no root 'plugin' key found`

### Fixed Version
```yaml
---
plugin: yaml
all:
  children:
    servers:
      hosts:
        iacgenie-server:
          ansible_host: 192.168.0.118
```

### INI Alternative
```ini
[servers]
iacgenie-server ansible_host=192.168.0.118 ansible_user=mkanavi

[docker_hosts:children]
servers
```

## Placeholder Secret Detection

```bash
# Search all roles for common placeholder patterns
grep -rE 'REPLACE_WITH_|TODO_|PUT_YOUR_|CHANGE_ME_|EXAMPLE_' roles/ 2>/dev/null
```

**Known placeholders (2026-08-02 session):**
- `REPLACE_WITH_ACTUAL_KEY` in SSH key templates (common + user_management roles)
- Would cause wrong SSH key to be deployed on first run

## Deployed vs Retrospective Detection

| Indicator | Deployed by Ansible | Retrospective (manual VM) |
|-----------|---------------------|---------------------------|
| Compose file dates predate commits | ❌ | ✅ |
| Ansible repo files on VM | ✅ | ❌ |
| `.vault_key` on VM | ✅ | ❌ |
| Playbook runs logged | ✅ | ❌ |

## Handler Template

Copy-paste template for new handlers:

```yaml
---
# Handlers for <role-name>
- name: Restart <service>
  ansible.builtin.service:
    name: <service>
    state: restarted
  listen: "Restart <service>"
```

For Docker container services:

```yaml
---
# Handlers for <role-name>
- name: Restart <service>
  ansible.builtin.command: docker compose -p iacgenie restart <service>
  listen: "Restart <service>"
```
