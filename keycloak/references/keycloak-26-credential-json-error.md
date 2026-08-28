# Keycloak 26.0 "Cannot parse the JSON" — Credential Data Pitfall

## Symptoms

Admin login fails with:
- `{"error":"unknown_error","error_description":"Cannot parse the JSON"}`
- Stack trace: `through reference chain: PasswordCredentialData["algorithmData"]->LinkedHashMap["encoded"]`

## Root Causes

### Cause 1: Wrong `algorithmData` structure
`PasswordCredentialData.algorithmData` must contain an `encoded` field that is a **simple string** (base64-encoded hash or full argon2 string). If `encoded` is missing or itself an object, Jackson's BeanDeserializer fails.

### Cause 2: Wrong `credential_data` top-level keys (Keycloak 26+)
When manually inserting a password credential into PostgreSQL, the `credential_data` JSON must use Keycloak 26's `PasswordCredentialData` schema, NOT older formats:

**WRONG** (older format, causes `UnrecognizedPropertyException`):
```json
{"hash": "...", "salt": "...", "algorithm": "pbkdf2-sha256", "iterations": 27500}
```

**WRONG** (`algorithmData` as array causes `MismatchedInputException`):
```json
{"algorithm": "pbkdf2-sha256", "hashIterations": 27500, "algorithmData": [{"salt": "...", "value": "..."}]}
```

**CORRECT** (Keycloak 26+):
```json
{
  "algorithm": "pbkdf2-sha256",
  "hashIterations": 27500,
  "additionalParameters": {"salt": "base64salt", "value": "base64hash"}
}
```

`algorithmData` must be a `LinkedHashMap<String, List<String>>` (a map), not an array. Keycloak 26 renamed the nesting from `algorithmData` to `additionalParameters` in the credential_data JSON.

### Cause 3: Stale in-memory credential cache
After updating `credential_data` directly in PostgreSQL, Keycloak **does not refresh** its in-memory credential cache. Login continues to fail until Keycloak is restarted.

### Cause 4: `KC_BOOTSTRAP_ADMIN_*` env vars don't work in `start` mode
In Keycloak 26.0, `KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD` env vars **do not create an admin user** when the server runs via `kc.sh start`. They are only consumed by `kc.sh bootstrap-admin user` command.

## Fix

### Step 1: Ensure minimal valid credential_data
```json
{"algorithm":"argon2","hashIterations":5,"algorithmData":{"encoded":"<base64-hash-string>"}}
```

### Step 2: Update via PostgreSQL
```sql
UPDATE credential SET credential_data = $CRED$<json>$$CRED$
WHERE user_id = '<uuid>' AND type = 'password' AND priority = 10;
```

### Step 3: RESTART Keycloak (mandatory — cache not refreshed)

### Step 4: Test login
```bash
curl -s -X POST 'https://auth.iacgenie.com/realms/master/protocol/openid-connect/token' \
  -d 'grant_type=password' -d 'client_id=admin-cli' \
  -d 'username=admin' -d 'password=<pw>'
```

## Admin Password Reset — Docker Network Pitfall

`kc.sh bootstrap-admin user` and `kc.sh import` start a **new Keycloak server instance** that connects to `localhost:5432` — it CANNOT reach Docker network services like the `postgres` container.

### Workaround: Use `docker run --network` with host DB params
```bash
docker run --rm --network iacgenie_iacgenie-backend \
  -e ADMIN_PASSWORD=<pw> \
  quay.io/keycloak/keycloak:26.0 \
  bootstrap-admin user \
  --username admin \
  --db postgres \
  --db-username keycloak \
  --db-password $KC_DB_PASSWORD \
  --db-url-host postgres \
  --db-url-port 5432 \
  --db-url-database keycloak \
  --no-prompt \
  --password:env ADMIN_PASSWORD
```

## Quick Checklist

| Symptom | Fix |
|---------|-----|
| "Cannot parse the JSON" | Check `algorithmData.encoded` is a plain string |
| "Invalid user credentials" after DB update | Restart Keycloak (in-memory cache) |
| Admin user not in DB | `KC_BOOTSTRAP_ADMIN_*` does not work in `start` mode — use `bootstrap-admin user` command |
| `kc.sh import` can't reach Postgres | Pass `--db-url-host=postgres` or use `docker run --network` |
