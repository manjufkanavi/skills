# OpenBao Ansible Bootstrap Playbook

## Purpose

Reproducible initialization of a fresh OpenBao instance via Ansible. Covers init, unseal, secret engines, policies, and AppRole auth.

## File: `playbooks/openbao-init.yml`

Run once after first `docker-compose up` on a clean OpenBao container. The playbook:

1. **Waits for container** — polls `docker ps` until `running`
2. **Initializes** — `bao operator init -format=json`
3. **Saves keys** — writes `init_keys.json` to both raft mount paths (`chmod 0600`)
4. **Unseals** — submits keys 1 and 2 via `bao operator unseal`
5. **Enables engines** — `iacgenie/kv`, `lightserp/kv`, `transit`, `database`, `ssh`
6. **Enables AppRole** — auth method at `auth/approle/`
7. **Deploys policies** — `iacgenie-backend` (read-only KV), `lightserp` (read-only KV)
8. **Creates AppRole roles** — `iacgenie-backend` and `lightserp` with TTL 24h

## Running from Ansible

```bash
cd infra/ansible
ansible-playbook playbooks/openbao-init.yml -i inventory/
```

## Manual steps (if playbook fails)

If the playbook partially succeeds but some step fails (common with init — keys are already saved), run individual steps manually:

```bash
# 1. Wait for container
ssh mkanavi@192.168.0.118 "docker inspect --format='{{.State.Status}}' iacgenie_openbao"

# 2. Init (if not initialized)
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao operator init -address=http://127.0.0.1:8200 -key-shares=3 -key-threshold=2 -format=json"

# 3. Save keys (copy to both paths)
ssh mkanavi@192.168.0.118 "chmod 0600 /home/mkanavi/docker/iacgenie/openbao_raft/init_keys.json"

# 4. Unseal
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao operator unseal --address=http://127.0.0.1:8200 <key1>"
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao operator unseal --address=http://127.0.0.1:8200 <key2>"

# 5. Enable engines
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao secrets enable -address=http://127.0.0.1:8200 -path=iacgenie kv"
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao secrets enable -address=http://127.0.0.1:8200 -path=lightserp kv"
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao secrets enable -address=http://127.0.0.1:8200 transit"

# 6. Enable AppRole
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao auth enable -address=http://127.0.0.1:8200 approle"

# 7. Write policies (from ansible role files)
ssh mkanavi@192.168.0.118 "scp infra/ansible/roles/openbao/files/policies/* mkanavi@192.168.0.118:/tmp/"

# 8. Apply policies
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao policy write -address=http://127.0.0.1:8200 iacgenie-backend /tmp/iacgenie-backend.hcl"

# 9. Create AppRole roles
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao write -address=http://127.0.0.1:8200 auth/approle/role/iacgenie-backend policies=iacgenie-backend secret_id_ttl=0 token_num_uses=0 token_ttl=24h"
ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao bao write -address=http://127.0.0.1:8200 auth/approle/role/lightserp policies=lightserp secret_id_ttl=0 token_num_uses=0 token_ttl=24h"
```

## Key gotchas

- **`-address` flag position**: For `bao operator init`, `-address` goes BEFORE the subcommand. For `bao operator unseal`, `-address` goes AFTER. Mixed flag positions break everything.
- **Save keys to BOTH paths**: The running compose may mount `data/openbao_raft` or `openbao_raft` to `/openbao/raft`. Save to both to survive compose changes.
- **Already-initialized guard**: The playbook uses `is not search('Already Initialized')` and `failed_when: false` to handle idempotency. Manual steps need the same guard — check `bao status` first.
- **Ansible stdin limitation**: `ansible.builtin.command` does NOT support `stdin`. For policy write via stdin, use `ansible.builtin.shell` with a temp file approach (copy policy file, then `docker exec ... bao policy write ... /tmp/policy.hcl`).
- **YAML syntax check**: After editing the playbook, run `ansible-playbook --syntax-check` before running. The playbook passes syntax check but may hang in `--check` mode due to the retry loop.
