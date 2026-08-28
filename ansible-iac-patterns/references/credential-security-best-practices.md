# Security Best Practices

## Never Commit Plaintext Credentials to Ansible Defaults

When working with Ansible roles that manage infrastructure services, **NEVER embed real credentials in role defaults (`defaults/main.yml`)**:

**Wrong:**
```yaml
# defaults/main.yml — DO NOT DO THIS
keycloak_admin_password: "hAaIa219fq5VzAP81SDyNuBV"
openbao_root_token: "hVRa8G..."
```

**Correct:**
```yaml
# defaults/main.yml — SAFE sentinel pattern
keycloak_admin_password: "CHANGE_ME_IN_VAULT"
openbao_root_token: "CHANGE_ME_IN_VAULT"
```

## Proper Credential Flow

1. **Extract** credentials from the live VM (e.g., `grep KEYCLOAK_ADMIN_PASSWORD .env.keycloak | cut -d= -f2-`)
2. **Store** in Ansible Vault: `ansible-vault edit inventory/group_vars/all.yml`
3. **Reference** via `{{ vault_keycloak_admin_password }}` in templates
4. **Never** commit the vault file to git (`.vault_key` and vault-ed `.yml` files go in `.gitignore`)

## Keycloak-Specific

When provisioning Keycloak clients and extracting secrets:
1. Use the base64 transport pattern to run provisioning scripts on the VM
2. Extract client secrets via the Keycloak Admin API
3. Store secrets in OpenBao KV (not in Ansible defaults or git)
4. Reference OpenBao paths in `.env` files

## OpenBao-Specific

1. Root token stored in `init_keys.json` on the VM — read from there at runtime
2. Service tokens generated via OpenBao API during Ansible bootstrap
3. NEVER hardcode OpenBao tokens in Ansible inventory or defaults
