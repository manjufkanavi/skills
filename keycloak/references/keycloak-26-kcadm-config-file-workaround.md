# kcadm.sh Config File Approach for Keycloak 26 Admin Password Reset

## Problem
In Keycloak 26 Quarkus, `KC_BOOTSTRAP_ADMIN_PASSWORD` only works when there's NO admin user in the database. Once an admin user exists (even with a corrupted/unknown password), KC_BOOTSTRAP_ADMIN_PASSWORD is silently ignored.

## Solution: kcadm.sh Config File + set-password
kcadm.sh can load credentials from a config file at `/opt/keycloak/.keycloak/kcadm.config`, bypassing the need for interactive console input or stdin.

### Step-by-Step

1. **Create kcadm config file** inside the Keycloak container:
   ```bash
   docker exec iacgenie_keycloak bash -c "mkdir -p /opt/keycloak/.keycloak && cat > /opt/keycloak/.keycloak/kcadm.config << 'CONF'
   server=http://localhost:8083
   realm=master
   user=admin
   CONF"
   ```

2. **Set the password** using KC_CLI_PASSWORD env var:
   ```bash
   docker exec iacgenie_keycloak bash -c "export KC_CLI_PASSWORD='***' && /opt/keycloak/bin/kcadm.sh set-password --username admin 2>&1"
   ```

3. **Restart Keycloak** to clear credential cache:
   ```bash
   docker compose restart keycloak
   ```

### Config File Format
```yaml
server=http://localhost:8083
realm=master
user=admin
password=newpass123  # Optional: can also be set via KC_CLI_PASSWORD env var
```

### Important Notes
- The config file path is hardcoded in kcadm.sh: `/opt/keycloak/.keycloak/kcadm.config`
- The file must be writable by the `keycloak` OS user inside the container (chown if needed)
- KC_CLI_PASSWORD takes precedence over `password:` in config file
- The password is NOT saved to the config file — only server/realm/user are stored there

### Why This Works
kcadm.sh reads the config file on startup (unlike stdin-based commands which are broken in KC 26). The `set-password` command uses the config to establish an authenticated session, then changes the admin password via Admin REST API.

### Alternative: Direct SQL
If kcadm.sh doesn't work, delete the admin user's password credential via psql and restart:
```sql
DELETE FROM credential WHERE user_id = (SELECT id FROM user_entity WHERE username='admin') AND type='password';
```

### Pitfalls Discovered in Session (2026-08-28)
1. **KC_BOOTSTRAP_ADMIN_PASSWORD_FILE** in keycloak.conf takes precedence over KC_BOOTSTRAP_ADMIN_PASSWORD env var — but the file path (`/run/secrets/keycloak_admin_password`) doesn't exist on disk, creating a confusing double-reference situation.
2. **Keycloak 26 creates "temporary" admin user** — even with KC_BOOTSTRAP_ADMIN_PASSWORD set, the initial user may have a random password shown in logs. The kcadm approach reliably sets it to the desired value.
3. **Credential cache** — after any password change, Keycloak MUST be restarted or it will use the old cached hash.
4. **SSH output masking** — running commands via SSH that contain `***` patterns in grep/regex can cause bash syntax errors due to shell globbing. Use heredocs or direct file writes instead of inline grep patterns with `***`.
