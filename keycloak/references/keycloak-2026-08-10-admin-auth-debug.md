# Keycloak Admin Auth Debugging — Session 2026-08-10

## Context

Failed to authenticate to Keycloak admin API via token endpoint. The password in `.env` (`Kc8xL2mNp9Qr4vWy7zBf3jHa5dGe6tRu`) was known but all login attempts returned `401 invalid_user_credentials`.

## Root Cause Discovery

### Step 1: Password verification
Extracted the stored PBKDF2 credential from PostgreSQL:
```sql
SELECT credential_data FROM credential
WHERE user_id = '4183c335-2a41-4351-a7ab-244e7d4c818f'
  AND type = 'password';
```

Result: `{"algorithm":"pbkdf2-sha256","hashIterations":27500,"additionalParameters":{"salt":"5Gi6jmiSgVj624ODftgGSw==","value":"L4+4C3PodzGy43+hTbKmCED25RzQXmiYpOROnMK4jRg="}}`

Used Python PBKDF2 verification script — password **MATCHED** perfectly. The password in `.env` is correct.

### Step 2: Multiple admin users
Found 3 admin users in the database:
- `788f0006-fcb8-47bb-b6aa-4e6b89009350` — ORIGINAL (corrupted credential, `{hash:...},{algorithmData:[...]}` format → parse error)
- `3a657eea-4267-4909-8031-8ef92cd74102` — Created by start-dev restart
- `4183c335-2a41-4351-a7ab-244e7d4c818f` — Created by start-dev restart (the working one)

The old admin user (`788f0006...`) had **corrupted `credential_data`** with `{algorithmData:[...]}` (array instead of map). Keycloak crashed when loading it, causing all admin auth to fail.

### Step 3: Root cause chain
1. Original admin user created with proper credentials
2. At some point, credential_data became corrupted (possibly via direct SQL insert or import)
3. `start-dev` created new admin users, but the old corrupted one was still in DB
4. Keycloak tried to load ALL admin credentials and hit the parse error
5. ALL admin auth failed — including the new, valid admin users

### Fix attempted
Tried to delete the old admin user from PostgreSQL. However, `docker exec ... bash -c 'psql ...'` failed because `bash -c` runs as root and psql uses root as the PG role. Fixed by using `-h 127.0.0.1` with `PGPASSWORD`.

The old admin user couldn't be deleted due to FK constraints from `user_role_mapping`.

### What remains
The admin users still exist (deletion failed). The password auth still fails. The `start-dev` mode with Postgres doesn't auto-create admin users on boot (it only works with embedded H2).

## Key Learnings

1. **PBKDF2 verification** is the fastest way to confirm if a password is correct — doesn't require admin API access
2. **Corrupted credential_data** (`{algorithmData:[...]}`) blocks ALL admin auth in Keycloak — the engine crashes before it gets to the correct user
3. **Multiple admin users** can accumulate and cause confusion — always check how many exist
4. **`bash -c` in `docker exec` runs as root** — psql needs `-h 127.0.0.1` and `PGPASSWORD` workaround
5. **Keycloak 26 `start-dev` + Postgres** doesn't recreate admin user on restart — only `start-dev` with embedded DB does this

## Aftermath

Nginx config was fixed (admin/resources proxy paths deployed). Auth wrapper env vars are correct. Keycloak clients need to be created via admin API once admin access is restored.

## Recovery Options

1. **Direct SQL insert** — Generate PBKDF2 hash for desired password, insert into credential table, restart Keycloak
2. **Use bootstrap-admin from separate container** — `docker run --network ... kc.sh bootstrap-admin user`
3. **Switch to embedded DB** — Remove Postgres, use `start-dev` with no DB args, let Keycloak auto-create admin
