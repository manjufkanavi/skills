# Keycloak 26 Admin Credential Recovery

## Credential Table Schema (PostgreSQL)

Keycloak 26.x stores password credentials in the `credential` table with these columns:

| Column          | Type           | Nullable | Notes                                    |
|-----------------|----------------|----------|------------------------------------------|
| `id`            | varchar(36)    | NO       | Primary key                              |
| `salt`          | bytea          | YES      | Raw salt bytes (16 bytes for PBKDF2)     |
| `type`          | varchar(255)   | NO       | Usually `'PASSWORD'`                     |
| `user_id`       | varchar(36)    | YES      | FK → `user_entity.id`                    |
| `created_date`  | bigint         | YES      | Unix epoch ms                            |
| `user_label`    | varchar(255)   | YES      | Human-readable label for the credential  |
| `secret_data`   | text           | YES      | Must NOT be NULL — Keycloak calls `.replace()` on it |
| `credential_data`| text          | YES      | JSON with `{"salt","value","additionalParameters"}` |
| `priority`      | integer        | YES      | **Primitive int** — must NOT be NULL     |

### Critical Constraints

1. **`priority` is a Java `int`** — `NULL` causes `PropertyAccessException: Null value was assigned to a property of primitive type`. Always set to `1` for password credentials.
2. **`secret_data` is called with `.replace()`** in `JpaUserCredentialStore.toModel()` — `NULL` causes `NullPointerException`. Set to `''::text` (empty string) if not needed.
3. **`salt` column (bytea) and `credential_data.salt` (base64 string) must match** — Keycloak reads `salt` from the bytea column for hash verification, not from the JSON inside `credential_data`.

### Credential Data JSON Format

```json
{
  "salt": "<base64-encoded 16 bytes>",
  "value": "<base64-encoded PBKDF2-SHA256 hash>",
  "additionalParameters": {
    "dkLen": 32,
    "algorithm": "pbkdf2-sha256",
    "iterations": "216000",
    "digestIterations": 1
  }
}
```

### Updating a Password Credential via SQL

```sql
-- Update the bytea salt column (use decode for hex input)
UPDATE credential SET
  salt = decode('6dc45094...', 'hex'),
  credential_data = '{"salt":"<base64>","value":"<base64>","additionalParameters":{"dkLen":32,"algorithm":"pbkdf2-sha256","iterations":"216000","digestIterations":1}}'::text,
  secret_data = ''::text,
  priority = 1,
  created_date = EXTRACT(EPOCH FROM NOW())::bigint
WHERE id = '<credential-id>';
```

### Generating a PBKDF2-SHA256 Hash in Python

```python
import hashlib, base64

password = "the-admin-password"
salt_b64 = "bcRQlNoPMFIzFdYH/gMK4w=="  # from credential_data.salt
salt_bytes = base64.b64decode(salt_b64)
hash_val = hashlib.pbkdf2_hmac(
    "sha256", password.encode(), salt_bytes, 216000, dklen=32
)
hash_b64 = base64.b64encode(hash_val).decode()
```

### Deleting a User's Password Credential

```sql
DELETE FROM credential
WHERE user_id = (
    SELECT id FROM user_entity
    WHERE realm_id = '<realm-id>' AND username = 'admin'
) AND type = 'PASSWORD';
```

## `kc.sh` Commands and Networking Gotchas

### `kc.sh import` and `kc.sh bootstrap-admin` Start Their Own Instance

Both commands start a **new Keycloak server instance** inside the container. This instance uses the default JDBC connection (`localhost:5432`) and **cannot reach Docker network services** like the `postgres` container.

**Symptom:**
```
Connection to localhost:5432 refused. Check that the hostname and port are correct.
```

**Workaround:** Pass correct database connection flags:
```bash
docker exec iacgenie_keycloak /opt/keycloak/bin/kc.sh import \
  --db postgres \
  --db-url-host=postgres \
  --db-url-port=5432 \
  --db-url-database=keycloak \
  --db-username=keycloak \
  --db-password="$KC_DB_PASSWORD" \
  --dir /opt/keycloak/data
```

### `--import-realm` vs `kc.sh import`

| Feature              | `--import-realm` (start flag) | `kc.sh import` (command)       |
|----------------------|-------------------------------|--------------------------------|
| Trigger              | First boot only                | Manual, any time               |
| File location        | `$KCBASE/data/realm-export.json` | Directory or file path    |
| DB required          | No (creates realm before DB)  | Yes (must connect to existing DB) |
| Multiple realms      | Single realm file only        | Directory with multiple files  |
| Overwrites existing  | No (only on first boot)       | Yes                            |

## Why Admin Login Fails — Checklist

When `curl -s -X POST http://127.0.0.1:8083/realms/master/protocol/openid-connect/token -d 'grant_type=password&client_id=admin-cli&username=admin&password=...'` returns `"invalid_grant"`:

1. **User disabled** — `SELECT enabled FROM user_entity WHERE username = 'admin'` returns `false`
2. **Realm disabled** — `SELECT enabled FROM realm WHERE name = 'master'` returns `false`
3. **No password credential** — `SELECT count(*) FROM credential WHERE user_id = ... AND type = 'PASSWORD'` returns `0`
4. **`priority` is NULL** — Causes `PropertyAccessException` (check logs)
5. **`secret_data` is NULL** — Causes `NullPointerException` (check logs)
6. **Hash mismatch** — Password in `.env` differs from the one used at initial boot; the DB hash was created with a different password
7. **Wrong realm ID** — User exists but in a different realm (check `realm_id` column)
8. **`kc.sh bootstrap-admin` was used** — Creates a temp credential that doesn't work with the password grant flow

## In-Memory Credential Caching (CRITICAL)

**Keycloak caches all credential data in memory on startup.** If you modify the `credential` table directly via SQL, the running instance continues to use the **old cached values** until a full container restart.

**Symptom:** After SQL INSERT/UPDATE to `credential` table, login still returns `JsonParseException: Cannot parse the JSON` — the error message shows the OLD hash, not the new one.

**Debug step:** `docker logs <kc> | tail -5` — check if the hash in the error matches what's currently in the DB.
**Fix:** `docker compose restart keycloak` to clear the cache and reload from DB.

**Important:** This means you CANNOT hot-fix an admin password by updating the DB and just waiting — a restart is mandatory.

## Known Wrong Credential Formats (Dead Ends)

The following formats have been tried and ALL fail with `JsonParseException` or `UnknownPropertyException` in Keycloak 26.x:

| Attempted `credential_data` value | Error |
|---|---|
| Plain base64 hash `W6l5lHnooGkrun...` | `JsonParseException: Unrecognized token 'W6l5lHnoo...'` |
| JSON `{\"hash\": \"...\"}` | `UnknownPropertyException: property 'hash'` |
| JSON `{\"encoded\": \"...\"}` | `UnknownPropertyException: property 'encoded'` |
| JSON `{\"hashIterations\": 27500, \"algorithm\": \"pbkdf2-sha256\", \"encoded\": \"...\"}` | `UnknownPropertyException` |
| JSON `{\"hashIterations\": 27500, \"algorithm\": \"pbkdf2-sha256\", \"encoded\": \"...\", \"salt\": \"...\"}` | `UnknownPropertyException` |
| `{PBKDF2}hash:salt` | `JsonParseException` |

**The only format that works is the one documented above** (with `value`, `salt`, and `additionalParameters` keys). If the other formats seem to insert correctly, they will STILL fail at login because Jackson can't map the fields to `PasswordCredentialModel` properties.

## SSH + PostgreSQL Shell Quoting Pitfall

When generating SQL on your local machine and piping it via SSH to `docker exec psql`, **the shell strips or misinterprets JSON double quotes**. The resulting SQL inserts `{hashIterations: ...}` (unquoted keys) instead of `{"hashIterations": ...}`.

**Symptom:** SQL reports `INSERT 0 1` (success) but login fails with `JsonParseException` — the credential_data in the DB shows unquoted keys.

**Diagnosis:** `docker exec postgres psql -c "SELECT credential_data FROM credential WHERE ..."` — if keys lack double quotes, the INSERT was corrupted by the shell.

**Safe patterns:**
- Use Python on the remote machine to generate and write the SQL file, then pipe it: `docker exec -i postgres psql -f /tmp/kc.sql`
- Use `chr(39)` in Python to embed SQL single quotes without shell interference
- Write the SQL file locally and `scp` it to the VM, then run `docker exec -i psql -f /path/on/vm`
- Use `docker cp` to put the file inside the container, then `docker exec psql -f /container/path`

## KC 26 Admin Redirect Behavior

- `/admin/` → `302 → /admin/master/console/` (always master realm)
- `/admin/<realm>/` → the specified realm's admin console
- Custom realms are NOT auto-created; must be provisioned via admin API or realm import
