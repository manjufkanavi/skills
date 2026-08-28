---
name: keycloak
version: 2
description: Debug, configure, and maintain Keycloak in Docker Compose — startup, realm import, admin auth, database schema, and migration gotchas.
---

# Keycloak Docker Troubleshooting

Debug, configure, and maintain Keycloak in Docker Compose.

## CRITICAL: kcadm.sh stdin broken in Keycloak 26

`kcadm.sh create/update/delete` commands silently drop stdin in Keycloak 26 Quarkus. ALL write operations via `docker exec` return "unable to read contents from stream". See references/keycloak-26-kcadm-stdin-broken.md and references/keycloak-26-kcadm-limitations.md for the full workaround (use Admin REST API via curl or Python + urllib instead).

## WORKAROUND: kcadm.sh config file approach for password reset

When `KC_BOOTSTRAP_ADMIN_PASSWORD` fails to create/update the admin user (Keycloak 26 Quarkus), use kcadm.sh's config file approach:

1. Create a `kcadm.config` file inside the container at `/opt/keycloak/.keycloak/kcadm.config`:
   ```yaml
   server=http://localhost:8083
   realm=master
   user=admin
   ```

2. Set the password via `KC_CLI_PASSWORD` env var and `set-password`:
   ```bash
   docker exec iacgenie_keycloak bash -c "export KC_CLI_PASSWORD='***' && /opt/keycloak/bin/kcadm.sh set-password --username admin"
   ```

3. Restart Keycloak to clear credential cache: `docker compose restart keycloak`

A ready-to-use script is provided at scripts/kc-admin-reset.sh.

## Quick Diagnostic Checklist — Admin Auth Flow

When Keycloak refuses to start or log in, walk these in order:

When writing files with `write_file` or `skill_manage` action=write_file, the system replaces `***` sequences with nothing, breaking code that contains token/secret strings (e.g., `Authorization: Bearer ***`). Always:
1. Write the file content first, then patch the broken lines
2. Use Python string concatenation (`'Bearer ' + token`) instead of inline f-strings with secrets
3. Or use a heredoc via `ssh host << 'EOF'` to bypass the file-writing tool entirely

See `references/keycloak-26-kcadm-stdin-broken.md` for more context.

## Quick Diagnostic Checklist

When Keycloak refuses to start or log in, walk these in order:

1. **Health**: `docker logs <container> | tail -10` — look for `ERROR` or `health: starting`
2. **DB connectivity**: Can Keycloak reach the Postgres container? (`docker exec iacgenie-postgres psql -U keycloak -d keycloak -c "SELECT 1;"`)
3. **Schema**: Is `public` schema present and granted to `keycloak` role? (`psql -U postgres -d keycloak -c "SELECT nspname, nspacl FROM pg_namespace WHERE nspname = 'public';"`)
4. **Search path**: Does the `keycloak` role inherit `search_path TO public`? (`psql -U keycloak -d keycloak -c "SHOW search_path;"`)

## Realm Import Failures (most common)

### Problem
Keycloak 26.0 `start-dev --import-realm` rejects realm export JSON with errors like:
- `Unrecognized field "otpEnabled"`
- `Unrecognized field "otpPolicyCodeLength"`
- `Unrecognized field "realms"`

### Root Cause
Keycloak 26 removed/renamed several realm export fields. The export format changed from 25 → 26. Also, putting multiple realms inside a `realms: [...]` array is no longer supported in the single-file import.

### Fix
**Option A (preferred):** Remove `--import-realm` and create realms via Admin REST API.

**Option B:** Export a single-realm format (no `realms` wrapper, no `otpEnabled`/`otpPolicyCodeLength`/`otpRecoveryAuthnCodeFormat` fields). Each realm gets its own file.

### Common removed fields to strip from old exports
- `otpEnabled`, `otpRecoveryAuthnCodeFormat`, `otpPolicyCodeLength`
- `realms` (top-level wrapper — use single-realm format instead)

## Admin Login Fails

### "Account is not fully set up"
Corrupted credential data or required action row. Fix via SQL:
```sql
SELECT user_id, required_action FROM user_required_action
  WHERE user_id IN (SELECT id FROM user_entity WHERE username = 'admin');
DELETE FROM user_required_action WHERE user_id IN (SELECT id FROM user_entity WHERE username = 'admin');
SELECT substring(secret_data, 1, 50) FROM credential
  WHERE user_id = (SELECT id FROM user_entity WHERE username = 'admin');
-- If it looks like a JWT (eyJ...) instead of {"value":...}, the credential is corrupted
```

### "Realm not enabled"
Master realm's `enabled` column is `false`:
```sql
UPDATE realm SET enabled = true WHERE name = 'master';
```

### "Invalid user credentials" — Verify the password hash matches
**Symptom:** `.env` has a password, it passes through PBKDF2 verification, but admin login still fails. Multiple admin users may exist, or the token endpoint uses a different admin user than expected.

**Step 1 — Verify password against DB hash:**
```bash
# Get the salt and hash from the credential_data column for the admin user
docker exec iacgenie_postgres psql -U keycloak -d keycloak \
  -c "SELECT credential_data FROM credential WHERE user_id = (SELECT id FROM user_entity WHERE username='admin' ORDER BY id LIMIT 1);"

# Run the verification script (included in keycloak skill)
python3 ~/.hermes/skills/keycloak/scripts/verify-kc-password.py 'Kc8xL2mNp9Qr4vWy7zBf3jHa5dGe6tRu'
# It will prompt for salt (base64) and stored hash (base64), then print MATCH or no match
```

**Step 2 — Check for multiple admin users blocking auth:**
```sql
-- If multiple admin users exist, Keycloak may pick the wrong one
SELECT id, username FROM user_entity WHERE username='admin';
```

**Step 3 — Clean up all admin users and let Keycloak recreate:**
```sql
-- Step A: Delete credentials first (breaks FK)
DELETE FROM credential WHERE user_id IN (SELECT id FROM user_entity WHERE username='admin');

-- Step B: Delete from dependent tables (FK constraints)
DELETE FROM user_role_mapping WHERE user_id IN (SELECT id FROM user_entity WHERE username='admin');
DELETE FROM user_consent WHERE user_id IN (SELECT id FROM user_entity WHERE username='admin');
DELETE FROM user_consent_client_scope WHERE user_id IN (SELECT id FROM user_entity WHERE username='admin');

-- Step C: Delete the user entities
DELETE FROM user_entity WHERE username='admin';
```

After cleanup, restart Keycloak. On next boot with `KC_BOOTSTRAP_ADMIN_*` set (or `KEYCLOAK_ADMIN_PASSWORD`), a fresh admin user is created.

**Step 4 — Alternative: Use bootstrap-admin to force-create:**
```bash
# Run bootstrap-admin as a separate container with --network flag
docker run --rm --network iacgenie_iacgenie-backend \
  quay.io/keycloak/keycloak:26.0 \
  /opt/keycloak/bin/kc.sh bootstrap-admin user \
  --username admin \
  --password "NewPasswordHere" \
  --no-prompt \
  --db postgres \
  --db-url-host postgres \
  --db-url-port 5432 \
  --db-url-database keycloak \
  --db-username keycloak \
  --db-password "$KC_DB_PASSWORD"
```

## PostgreSQL Schema Issues

### "no schema has been selected to create in"
After `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`, JPA/Hibernate connection doesn't inherit the search_path. Liquibase fails to create its lock table.

**Fix:** All three steps:
```sql
DROP SCHEMA public CASCADE; CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO keycloak;
ALTER DATABASE keycloak SET search_path TO public;
ALTER ROLE keycloak SET search_path TO public;
docker restart iacgenie-postgres  -- ALTER DATABASE only applies to new connections
docker restart iacgenie-keycloak
```

**Alternative:** Add `?currentSchema=public` to the JDBC URL in the compose file.

## Environment Variable Changes (Keycloak 26)

| Old (≤25)                    | New (26+)                    |
|------------------------------|------------------------------|
| `KEYCLOAK_ADMIN`             | `KC_BOOTSTRAP_ADMIN_USERNAME` |
| `KEYCLOAK_ADMIN_PASSWORD`    | `KC_BOOTSTRAP_ADMIN_PASSWORD` |

**NOTE:** Keycloak 26 Quarkus also accepts `KEYCLOAK_ADMIN_PASSWORD` (legacy Docker var) at runtime — it works for both admin username and password. However, the template `.env.j2` uses `KC_BOOTSTRAP_*` names which are the canonical KC 26 variables. If the deployed `.env` has `KEYCLOAK_ADMIN_PASSWORD`, it still works — but for consistency, use `KC_BOOTSTRAP_ADMIN_PASSWORD` in templates.

**Ansible template note:** The `keycloak/.env.j2` template uses `KC_BOOTSTRAP_ADMIN_PASSWORD` and `KC_DB_PASSWORD`, but the actual deployed `.env` on the VM uses `KEYCLOAK_ADMIN_PASSWORD` and `KC_DB_PASSWORD`. Both work because Keycloak 26 accepts both. If you update the template, the generated `.env` will change — test after deployment.

### Docker Compose Compatibility: KEYCLOAK_ADMIN_USER/PASSWORD

The docker-compose.yml references `${KEYCLOAK_ADMIN_USER}` and `${KEYCLOAK_ADMIN_PASSWORD}` but the Keycloak role only generates `KC_BOOTSTRAP_*` vars. **Must add both sets to the `.env.j2` template:**

```
KEYCLOAK_ADMIN_USER={{ keycloak_admin_user | default('admin') }}
KEYCLOAK_ADMIN_PASSWORD=*** keycloak_admin_password | default('CHANGE_ME_IN_VAULT') }}
KC_BOOTSTRAP_ADMIN_USERNAME={{ keycloak_admin_user | default('admin') }}
KC_BOOTSTRAP_ADMIN_PASSWORD=*** keycloak_admin_password | default('CHANGE_ME_IN_VAULT') }}
```

If `KEYCLOAK_ADMIN_USER` or `KEYCLOAK_ADMIN_PASSWORD` are missing from the merged `.env`, Keycloak will fail with `bootstrap-admin-username available only when bootstrap admin password is set`.

## Password Recovery — bootstrap-admin CLI

Keycloak 26 no longer supports `kc.sh reset-password`. Use `bootstrap-admin` instead:

```bash
# Check available commands
docker exec iacgenie_keycloak /opt/keycloak/bin/kc.sh bootstrap-admin --help
docker exec iacgenie_keycloak /opt/keycloak/bin/kc.sh bootstrap-admin user --help

# Create/reset admin user non-interactively
docker exec iacgenie_keycloak \
  /opt/keycloak/bin/kc.sh bootstrap-admin user \
  --username admin \
  --password "NewSecurePass123!" \
  --no-prompt \
  --http-port 8080
```

Options for `bootstrap-admin user`:
- `--username` — admin username (default: `temp-admin`)
- `--no-prompt` — run non-interactively
- `--password:env` — read password from env var instead of CLI arg

## Health Check

Keycloak 26 Quarkus may not expose `/health/ready` on the HTTP port. Use these checks instead:

```bash
# Check if port is listening (most reliable)
ss -tlnp | grep 8080

# Try the admin API endpoint (returns JSON on KC 26)
curl -s http://127.0.0.1:8083/realms/master | python3 -c "import sys,json; r=json.load(sys.stdin); print('Realm:', r.get('realm'))"

# Keycloak 26 Admin API base
curl -s http://127.0.0.1:8083/admin/realms/master
```

When Keycloak is behind nginx proxy on port 8083 (host-mapped from container 8080), use `127.0.0.1:8083` for admin API calls.

### ⚠️ Keycloak 26 Admin Console JS Fails with 405 (Admin API Port Not Exposed)

**Symptom:** Keycloak admin console loads HTML but shows "Loading the Administration Console" → "Something went wrong". The admin console JS bundle loads (200 OK), but subsequent XHR/fetch calls to `/admin/master/realms/master` etc. return 405 Method Not Allowed.

**Root cause:** In Keycloak 26, the admin REST API runs on a **separate admin port** (9000 by default, accessible via `--http-admin-port`). The admin console JS makes API calls to paths like `/admin/master/realms/master`, but when Nginx proxies these to the **public HTTP port** (8080), the public HTTP endpoint does NOT handle those API calls — it only serves the admin console HTML and static assets. The admin API endpoints require the admin port.

**Debugging:**
```bash
# Check if admin API responds
curl -sI 'https://auth.iacgenie.com/admin/master/'
# 405 = admin API port not exposed or not configured

# Test on direct HTTP port
curl -sI 'http://127.0.0.1:8083/admin/master/'
# 405 confirms the issue is on the HTTP port

# Check if admin port 9000 is exposed
docker ps | grep keycloak | grep 9000
# Empty = admin port NOT exposed

# Check Keycloak startup args for admin port
docker inspect <kc-container> --format '{{.Config.Cmd}}' 2>/dev/null
# Look for --http-admin-port in the command
```

**Fix — expose admin port in docker-compose.yml.j2:**
```yaml
keycloak:
  image: quay.io/keycloak/keycloak:26.0
  command:
    - start
    - --http-enabled=true
    - --http-port=8080
    - --http-admin-port=9000   # ← REQUIRED for admin REST API
    - --hostname=https://auth.iacgenie.com
    - --hostname-admin=https://auth.iacgenie.com
  ports:
    - "127.0.0.1:8083:8080"
    - "127.0.0.1:9000:9000"  # ← EXPOSE admin port
```

**Important:** The admin port must be exposed for the admin console to work. Without it, the admin console JS makes API calls that hit the HTTP endpoint (which rejects them with 405).

### The `/admin/` Redirect Problem

Visiting `/admin/` on a Keycloak 26.x instance always redirects to `/admin/master/console/` — the **master** realm's admin console, not the custom realm. This happens because:

1. `/admin/` has no realm path in the URL
2. Keycloak defaults to the `master` realm when no realm is specified
3. Keycloak does NOT auto-create custom realms on startup (even with `--hostname`)

**Symptom:** `curl -sI https://auth.iacgenie.com/admin/` returns `302 → /admin/master/console/` — the admin panel loads but with the internal master realm, not the `iacgenie` realm.

### Admin Token Acquisition

**CRITICAL:** In Keycloak 26, use the OIDC token endpoint (NOT the admin API endpoint) to get a token. The `kcadm.sh get-token` subcommand does not exist in KC 26.

```bash
# Get admin token from OIDC endpoint (use the HOST-MAPPED port, e.g. 8083)
curl -s -X POST http://127.0.0.1:8083/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=admin-cli&username=admin&password=YOUR_PASS&realm=master"
```

The response contains `access_token` which is used for subsequent admin API calls:
```bash
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:8083/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=admin-cli&username=admin&password=YOUR_PASS&realm=master" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Use it with the admin API
curl -s http://127.0.0.1:8083/admin/realms \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**NOTE:** Both the token endpoint and the admin API use the **host-mapped port** (e.g., `8083`). The internal container port `8080` does not expose the admin API. When `docker-compose.yml` maps `127.0.0.1:8083:8080`, use port `8083` in all curl commands from the host.

### Realm Provisioning on First Boot

**CRITICAL: Keycloak 26.0.x does NOT support `--hostname-url` or `--hostname-admin-url` flags.** These were introduced in 26.3+. On KC 26.0.8, using them causes startup failure: `Unknown option: '--hostname-url'`.

```bash
# WRONG (fails on KC 26.0):
--hostname-url https://auth.iacgenie.com --hostname-admin-url https://auth.iacgenie.com/admin

# RIGHT for KC 26.0:
--hostname=https://auth.iacgenie.com --hostname-admin=https://auth.iacgenie.com
```

**Environment variable equivalents (work across all KC 26.x):**
```bash
KC_HOSTNAME=https://auth.iacgenie.com
KC_HOSTNAME_ADMIN=https://auth.iacgenie.com
```

**To determine which flags your KC version supports:**
```bash
docker exec <kc-container> /opt/keycloak/bin/kc.sh start --help 2>&1 | grep -i hostname
```

### Realm Provisioning on First Boot

Keycloak 26+ does NOT auto-create custom realms. You must provision them:

**Option A: Admin REST API (preferred)**
```bash
# Create realm via API
curl -s -X POST http://127.0.0.1:8080/admin/master/realms \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"realm": "iacgenie", "enabled": true}'
```

**Option B: Realm import file (single realm only)**
```bash
# Deploy realm.json to /opt/keycloak/data/import/realm.json
# Start with: --import-realm
```

See `templates/keycloak-realm-api-create.py` for a full automation script.
See `templates/keycloak-realm-create.py` for a pre-written script to create the iacgenie realm and admin user (fill in credentials before running).

## CRITICAL: Database Driver at Build Time (Keycloak 26+)

**The single most common Keycloak 26 deployment failure:** `--db-url-host=postgres` (and other `--db-url-*` args) at **runtime** only set connection parameters. They do NOT change the database driver. The driver is baked in at **build time** via `kc.sh build --db postgres`.

### Symptoms of this bug:
- `kc.sh show-config` shows `kc.db = dev-file (Persisted)` instead of `postgres`
- `Installed features: [..., jdbc-h2, ...]` — H2 is the active driver
- Admin user credentials exist in PostgreSQL but login fails with 401
- Realms provisioned via admin API appear to work (running on H2) but data is lost on restart if you think you're using PostgreSQL

### Correct build procedure:
```bash
# Build a custom Keycloak image WITH PostgreSQL driver baked in
docker run --name kc-build quay.io/keycloak/keycloak:26.0 build --db postgres
docker commit kc-build quay.io/keycloak/keycloak:26.0-pg
docker rm kc-build

# Verify the driver is baked in
docker run --rm quay.io/keycloak/keycloak:26.0-pg kc.sh show-config | grep "^kc.db"
# Expected: kc.db = postgres (Persisted)
```

### Correct deployment with built image:
```yaml
# docker-compose.yml
keycloak:
  image: quay.io/keycloak/keycloak:26.0-pg   # Must be the --db postgres built image
  command:
    - start
    - --db=postgres               # Tells runtime which driver to use (now guaranteed available)
    - --db-password=${KC_DB_PASSWORD}
    - --hostname=https://auth.iacgenie.com
    - --hostname-admin=https://auth.iacgenie.com
  environment:
    KC_DB_PASSWORD: "${KC_DB_PASSWORD}"
  volumes:
    - ./keycloak.conf:/opt/keycloak/conf/keycloak.conf:ro
```

### DO NOT use `--optimized` with `build` command:
- `--optimized` is a **startup** option (`kc.sh start --optimized`)
- `kc.sh build` does NOT accept `--optimized` — it always builds an optimized image
- Passing `--optimized` to `build` silently fails

### Alternative: Mount config file (bypasses build):
Mount a custom `keycloak.conf` with `db=postgres` to avoid rebuilding the image. See `templates/keycloak.conf.j2`.

### Pitfall: `docker commit` captures the build CMD
When you commit a container after `kc.sh build`, the container's CMD gets overwritten. The committed image will have `CMD [kc.sh, build, --db, postgres]` instead of `kc.sh start`. Either:
1. Fix the CMD: `docker commit --change 'CMD ["/opt/keycloak/bin/kc.sh", "start"]' ...`
2. Or override the CMD in docker-compose: `command: [start, --http-enabled=true, ...]`

## CRITICAL: Admin Console Crash ("somethingWentWrongDescription")

When visiting `https://auth.iacgenie.com/` (root path), Keycloak redirects to `/admin/master/console/`. If the master realm admin user has NO password credential in the **active database**, the admin console JavaScript bundle fails to load and shows "Something went wrong".

**Root cause chain:**
1. Admin user exists in PostgreSQL but Keycloak is running on H2 (see driver bug above)
2. OR admin user was created by `KC_BOOTSTRAP_ADMIN_USERNAME` but `KC_BOOTSTRAP_ADMIN_PASSWORD` was not set or not resolved
3. OR admin credential was corrupted/missing in the database

**Fix:** Ensure the admin user has a proper `PASSWORD` credential in the active database. See `templates/kc-admin-credential-insert.py` for the credential format.

## CRITICAL: Keycloak 26 bootstrap-admin behavior

`KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD` create a **temporary** admin user, not one with a proper password credential. The user is created with `kc.sh bootstrap-admin user` which sets a temporary credential. To create a real password credential, you must either:
1. Set `KEYCLOAK_ADMIN` and `KEYCLOAK_ADMIN_PASSWORD` environment variables (these work alongside bootstrap vars in KC 26)
2. Or use the `--password:env` flag with `bootstrap-admin user` after startup

**Important:** `bootstrap-admin user --password:env KC_ADMIN_PASS` reads from an env var INSIDE the container and hashes the password — it does NOT require knowing the hash beforehand.

### ⚠️ `KC_BOOTSTRAP_ADMIN_*` env vars do NOT create admin in `start` mode (KC 26.0)

In Keycloak 26.0, `KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD` environment variables **do not create an admin user** when Keycloak runs via `kc.sh start`. They are only consumed by the `kc.sh bootstrap-admin user` command. This means if you rely solely on these env vars in docker-compose, **no admin user will be created** — you'll get "No admin user found" or blank DB.

**Workaround:** Use BOTH sets of env vars in docker-compose:
```yaml
environment:
  KEYCLOAK_ADMIN: admin
  KEYCLOAK_ADMIN_PASSWORD: <password>
  KC_BOOTSTRAP_ADMIN_USERNAME: admin
  KC_BOOTSTRAP_ADMIN_PASSWORD: <password>
```

Or use `kc.sh bootstrap-admin user` as a one-time command after first boot (see `references/keycloak-26-credential-json-error.md`).

### ⚠️ `start-dev` with PostgreSQL does NOT create bootstrap admin

The `bootstrap-admin` mechanism only works with the **embedded H2 database**, not PostgreSQL. When `start-dev` runs with `--db=postgres`, the admin user is NOT created because `bootstrap-admin` internally uses H2 even when other database flags are passed.

**Symptom:** `start-dev --db=postgres` starts successfully, but no admin user exists → login returns 401 or "No admin user found".

**Workaround for PostgreSQL deployments:** (a) Start with H2 first to create admin, then switch to PostgreSQL, or (b) Create the admin user via the Admin REST API after initial container start, or (c) Directly insert into the PostgreSQL database using the correct PBKDF2 hash (NOT Argon2 — see "NEVER use direct database Argon2 hash inserts" below).

**Prevention:** For PostgreSQL deployments, always bootstrap admin credentials separately or use the Admin API after initial container start.

### ⚠️ Passing password via SSH requires heredoc quoting

Shell interpolation strips `$` characters from passwords like `Kc8xL2mNp9Qr4vWy7zBf3jHa5dGe6tRu` when passed via `docker run -e KEYCLOAK_ADMIN_PASSWORD=value`. Use either:
- `docker run -e KEYCLOAK_ADMIN_PASSWORD='$KC_PASS'` with `$KC_PASS` set in the shell
- Or heredoc with single-quoted delimiter: `ssh host <<'EOF'` (no expansion)
- Or write password to file and read at runtime: `-e KEYCLOAK_ADMIN_PASSWORD=$(cat /tmp/kc_pass)`

### ⚠️ Auth Wrapper Default KEYCLOAK_URL Redirects to Localhost

**Symptom:** Dashboard services (ClamAV, CrowdSec, PageGen) redirect to `http://127.0.0.1:8083` instead of the public Keycloak URL. Users see a broken login flow.

**Root cause:** The shared auth wrapper source code has `'http://127.0.0.1:8083'` as the default fallback for `KEYCLOAK_URL`:
```javascript
const KC_URL = process.env.KEYCLOAK_URL || 'http://127.0.0.1:8083';
```
When the env var is not set, falls through, or is accidentally removed, the app uses the localhost URL.

**Fix:** Always set `KEYCLOAK_URL: "https://auth.iacgenie.com"` explicitly in Ansible env vars for every dashboard container. After changing the source code default, restart ALL auth wrapper containers.

**Verification:** `curl -sL -o /dev/null -w "%{url_effective}\n" https://clamav.iacgenie.com/login` should return a URL starting with `https://auth.iacgenie.com`.

See `references/auth-wrapper-default-keycloak-url.md` for full details.

### Important: `kc.sh import` and `kc.sh bootstrap-admin` Start Their Own Instance

Both commands start a **new Keycloak server instance** inside the container. This instance uses the default JDBC connection (`localhost:5432`) and **cannot reach Docker network services** like the `postgres` container.

**Symptom:**
```
Connection to localhost:5432 refused. Check that the hostname and port are correct.
```

### ⚠️ `docker exec ... bash -c` runs as root — psql fails with "role 'root' does not exist"

When running `psql` inside a Docker container via `docker exec <container> bash -c 'psql ...'`, the `bash -c` runs as the **root OS user**. psql uses the OS username as the PostgreSQL role, so it tries to connect as `root` which doesn't exist.

**Fix — use `-h 127.0.0.1` with `PGPASSWORD`:**
```bash
# WRONG (fails: role 'root' does not exist)
docker exec iacgenie_postgres bash -c 'psql -U postgres -d keycloak -c "SELECT 1;"'

# RIGHT (TCP connection uses PGPASSWORD, bypasses OS user mapping)
docker exec iacgenie_postgres bash -c "PGPASSWORD='***' psql -h 127.0.0.1 -U postgres -d keycloak -c 'SELECT 1;'"
```

The `-h 127.0.0.1` flag forces a TCP connection instead of a Unix socket, which makes psql use the `-U` and `PGPASSWORD` values instead of the OS username.

### ⚠️ `docker run --rm` with `--network` for cross-container DB access

When `kc.sh import` or `kc.sh bootstrap-admin` need to reach the Postgres container on a Docker network, running them inside the Keycloak container fails (localhost only). Instead, run a **fresh container on the same network**:

```bash
docker run --rm --network iacgenie_iacgenie-backend \
  -e ADMIN_PASSWORD=*** \
  quay.io/keycloak/keycloak:26.0 \
  bootstrap-admin user \
  --username admin \
  --db postgres \
  --db-username keycloak \
  --db-password "$KC_DB_PASSWORD" \
  --db-url-host postgres \
  --db-url-port 5432 \
  --db-url-database keycloak \
  --no-prompt \
  --password:env ADMIN_PASSWORD
```

The `--network` flag gives the ephemeral container access to `postgres` (the host in Docker network DNS), while `--db-url-host=postgres` tells kc.sh which host to connect to.

**Workaround for `kc.sh bootstrap-admin`:** Don't use it inside the container if the DB is on a different Docker network. Instead, use the admin REST API or direct SQL to reset the password.

## CRITICAL: Keycloak Caches Credentials in Memory

**After any direct database modification to credentials (`credential` table), Keycloak MUST be restarted.** The in-memory credential cache is not refreshed on schema changes — login attempts will use the old cached hash and fail even though the DB was updated.

**Symptom:** DB shows correct credential, login still fails with `JsonParseException` or `invalid_grant`.
**Fix:** `docker compose restart keycloak` (or `docker restart`).

## CRITICAL: Admin password does NOT update on env var change + restart

When you change `KEYCLOAK_ADMIN_PASSWORD` or `KC_BOOTSTRAP_ADMIN_PASSWORD` in the `.env` file and restart the Keycloak container, the **old password hash persists in the database**. The bootstrap variables only create the admin user on **first boot** (when no admin user exists in the DB).

**Symptom:** Updated `.env` has new password, container restarts, but admin login still fails with `invalid_user_credentials`.

**Fix — use `bootstrap-admin user` to reset:**
```bash
docker exec iacgenie_keycloak \
  /opt/keycloak/bin/kc.sh bootstrap-admin user \
  --username admin \
  --password "NewPasswordHere" \
  --no-prompt
```

This directly updates the password hash in the database, regardless of what's in `.env`.

**Alternative fix — via SQL (if bootstrap-admin fails):**
```sql
-- Delete old credential, then restart so KEYCLOAK_ADMIN_PASSWORD creates a fresh one
DELETE FROM credential
WHERE user_id = (
    SELECT id FROM user_entity
    WHERE realm_id = '<realm-id>' AND username = 'admin'
) AND type = 'PASSWORD';
```

**Important:** When manually inserting a password credential into PostgreSQL, three fields **must not be NULL**:
- `priority` — a Java primitive `int`, NULL causes `PropertyAccessException`. Always set to `1`.
- `secret_data` — Keycloak calls `.replace()` on it in `JpaUserCredentialStore.toModel()`. NULL causes `NullPointerException`. Set to `''::text`.
- `salt` (bytea column) — Keycloak reads the raw salt bytes from this column for PBKDF2 verification, not from the JSON inside `credential_data`. Must match the base64-encoded salt in `credential_data.salt`.

**Credential `credential_data` JSON format for Keycloak 26+:**
The `credential_data` field must use `PasswordCredentialData` schema:
```json
{
  "algorithm": "pbkdf2-sha256",
  "hashIterations": 27500,
  "additionalParameters": {"salt": "base64salt", "value": "base64hash"}
}
```
**NOT** `{"hash":"...","salt":"...","algorithm":"..."}` (older format → `UnrecognizedPropertyException`).  
**NOT** `{"algorithmData":[...]}` — `algorithmData` must be a map, not array → `MismatchedInputException`.

See `references/keycloak-26-credential-recovery.md` for full schema, SQL patterns, and hash-generation recipes.

## Shared Auth Wrapper — Evolution of Patterns

### v1 (Node.js/Express — legacy)
Domain-based routing via `DOMAIN_BACKEND_MAP` + `SERVICE_BACKENDS` env var. One container, one host port, Host header determines backend. See templates for legacy pattern.

### v2 (FastAPI + X-Service Header — current)
Nginx sets `X-Service` header to `backend-container:port` (e.g., `clamav-service:8080`). Auth wrapper routes based on this header instead of Host. Allows the same auth wrapper container to listen on multiple host ports (9091, 9092, 9093) each with a different `X-Service` header.

**Nginx config:**
```nginx
location / {
    proxy_pass http://127.0.0.1:9091;   # auth wrapper
    proxy_set_header X-Service "clamav-service:8080";
}
```

**Docker Compose:**
```yaml
auth_wrapper:
  build: ./shared-auth-wrapper
  ports:
    - "127.0.0.1:9091:9090"   # ClamAV
    - "127.0.0.1:9092:9090"   # CrowdSec
    - "127.0.0.1:9093:9090"   # PageGen
  environment:
    AUTH_KEYCLOAK_URL: "http://keycloak:8080"
    AUTH_REALM: "iacgenie"
    AUTH_CLIENT_ID: "auth-wrapper"
```

**Keycloak client:** Single `auth-wrapper` client with redirect URIs for ALL services:
```yaml
auth-wrapper:
  secret: "{{ auth_wrapper_secret }}"
  redirect_uris:
    - "https://clamav.iacgenie.com/*"
    - "https://crowdsec.iacgenie.com/*"
    - "https://pagegen.iacgenie.com/*"
```

### Coordinated Multi-Template Deployment

When fixing 5+ templates simultaneously (nginx, docker-compose, cloudflare, openbao, keycloak, ansible), use this workflow:

1. **Read all templates FIRST** — verify current state before patching
2. **Apply patches in dependency order:**
   - docker-compose.yml.j2 (defines services/ports)
   - nginx reverse-proxy.conf.j2 (routes traffic)
   - cloudflared.yaml.j2 (tunnel routing)
   - keycloak defaults/main.yml (client definitions)
   - openbao tasks/kv_bootstrap.yml (KV seeds)
   - .env.j2 (env vars)
   - ansible playbook roles (auth-wrapper role, client setup tasks)
3. **Verify each patch separately** before moving to the next
4. **Build the auth wrapper Docker image** — ensure `shared-auth-wrapper/` build context is symlinked in docker-compose dir
5. **Deploy via Ansible** — `ansible-playbook playbooks/services.yml`

### Auth Wrapper Keycloak Client Setup

The `keycloak_client_setup.py` script ensures Keycloak clients exist:
- Uses admin CLI login (`admin-cli` + password) to get admin token
- Creates or updates client via Admin REST API
- Sets redirect URIs, client secret, and flags (Standard Flow, Direct Access Grants)

**Ansible task:**
```yaml
- name: Keycloak | Set up auth-wrapper client
  ansible.builtin.command:
    cmd: >
      /home/mkanavi/docker/iacgenie/scripts/keycloak_client_setup.py
      --kc-url http://127.0.0.1:8080
      --realm iacgenie
      --admin-user {{ keycloak_admin_user }}
      --admin-password {{ keycloak_admin_password }}
      --client-id auth-wrapper
      --secret {{ auth_wrapper_secret }}
      --redirect-uris https://clamav.iacgenie.com/* ...
```

See `templates/auth-wrapper-server.py` for the FastAPI v2 implementation.

See `templates/auth-wrapper-server.py` for the FastAPI v2 implementation.
## Architecture (v2 — single container, multiple backends via X-Service header)

```
clamav.iacgenie.com ─┐
crowdsec.iacgenie.com├─→ 127.0.0.1:9091 (auth-wrapper) → X-Service: clamav-service:8080
pagegen.iacgenie.com─┘    127.0.0.1:9092 (auth-wrapper) → X-Service: crowdsec-service:8080
                           127.0.0.1:9093 (auth-wrapper) → X-Service: pagegen-service:3031
```

Each subdomain is routed to the correct backend via the `DOMAIN_BACKEND_MAP` in the app:
```javascript
const DOMAIN_BACKEND_MAP = {
  'clamav.iacgenie.com': 'clamav',
  'crowdsec.iacgenie.com': 'crowdsec',
  'pagegen.iacgenie.com': 'pagegen',
  'search.iacgenie.com': 'searxng'
};
```

And `SERVICE_BACKENDS` env var:
```
SERVICE_BACKENDS=clamav:9092,crowdsec:3033,pagegen:3032,searxng:8084,default:9090
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PORT` | Container listen port | `9090` |
| `KEYCLOAK_URL` | Public Keycloak URL | `https://auth.iacgenie.com` |
| `KEYCLOAK_REALM` | Keycloak realm name | `iacgenie` |
| `KEYCLOAK_CLIENT_ID` | OIDC client ID | `auth-wrapper` |
| `KEYCLOAK_CLIENT_SECRET` | Client secret from Keycloak | `Lw9xP4...2kYn` |
| `SESSION_SECRET` | Express session secret | `random-string-here` |
| `SERVICE_BACKENDS` | Comma-separated `name:port` pairs | `clamav:9092,crowdsec:3033,pagegen:3032,searxng:8084` |
| `SERVICE_NAME` | Display name in dashboard | `Auth-Wrapper` |
| `SERVICE_TITLE` | Page title | `IaCGenie Services` |

### Keycloak Client Setup

Create a **single OIDC client** in Keycloak (`auth-wrapper`) with:
- Standard Flow enabled
- Implicit Flow: disabled
- Direct Access Grants: **enabled**
- Redirect URIs (must be exact, wildcards do NOT work in KC 26):
  - `https://clamav.iacgenie.com/callback`
  - `https://crowdsec.iacgenie.com/callback`
  - `https://pagegen.iacgenie.com/callback`
  - `https://search.iacgenie.com/callback`
  - `https://clamav.iacgenie.com/*`
  - `https://crowdsec.iacgenie.com/*`
  - `https://pagegen.iacgenie.com/*`
  - `https://search.iacgenie.com/*`

### Cookie Pitfall — secure=false Behind Reverse Proxy

**CRITICAL:** The session cookie must use `secure: false` when the app runs behind a reverse proxy (nginx, Cloudflare):

```javascript
cookie: { httpOnly: true, secure: false, maxAge: 300000 }
```

**Why:** The internal connection between nginx and the Node.js container is HTTP. If `secure: true`, the browser drops the cookie, causing a login loop. The external connection (browser ↔ Cloudflare) is HTTPS, but the internal hop is HTTP.

### Keycloak Client Setup

Create a **single OIDC client** in Keycloak (e.g., `auth-wrapper`) with:
- Standard Flow enabled
- Client authentication: Client Secret
- Redirect URI: `https://<service>.iacgenie.com/callback`
- All services share the same client + secret

### Cookie Pitfall — secure=false Behind Reverse Proxy

**CRITICAL:** The session cookie must use `secure: false` when the app runs behind a reverse proxy (nginx, Cloudflare):

```javascript
cookie: { httpOnly: true, secure: false, maxAge: 300000 }
```

**Why:** The internal connection between nginx and the Node.js container is HTTP. If `secure: true`, the browser drops the cookie, causing a login loop. The external connection (browser ↔ Cloudflare) is HTTPS, but the internal hop is HTTP.

See `templates/auth-wrapper-app.js` for a complete working template with login, callback, and dashboard routes.

### Healthcheck Pitfall — wget Requires Full URL

**CRITICAL:** Docker healthcheck with `wget` must include the full URL:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:9091/health || exit 1
```

**Wrong:** `wget -qO- /health` — wget treats `/health` as a hostname and fails with "bad address"
**Right:** `wget -qO- http://127.0.0.1:9091/health` — wget connects to the correct host

### Docker Port Cleanup Pitfall

After `docker rm -f <container>`, the `docker-proxy` process may still hold the port (LISTEN state persists). Starting a new container on the same port fails with:
```
Bind for 127.0.0.1:<PORT> failed: port is already allocated
```

**Symptom:** `ss -tlnp | grep <PORT>` shows the port as LISTEN, but no container is using it.

**Fix — kill the docker-proxy holder:**
```bash
sudo fuser -k <PORT>/tcp   # kills whatever is holding the port
sleep 5                     # let docker release the socket
docker run ... -p 127.0.0.1:<PORT>:<CONTAINER_PORT> ...
```

**Workaround alternatives:**
- `docker system prune -f` then wait 5s+ before restarting containers
- Use a different host port temporarily: `-p 127.0.0.1:9096:9090`
- Remove container then run `ss -tlnp | grep <PORT>` to verify the port is truly free before `docker run`

**Prevention:** Always run `docker rm -f` then `sleep 5` before the next `docker run` on the same port.

### Nginx Proxy Config

```nginx
server {
    listen 443 ssl;
    server_name clamav.iacgenie.com;

    location / {
        proxy_pass http://127.0.0.1:9091;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## CRITICAL: Auth Redirect Loop to 127.0.0.1:8083 (Missing Realm)

**Symptom:** User navigates to a protected dashboard (e.g. `https://clamav.iacgenie.com/`), gets redirected to Keycloak login, but instead of showing the login page, the browser jumps to `127.0.0.1:8083` — a localhost URL that doesn't work from the outside.

**Root cause:** The Keycloak realm specified in the dashboard's `KEYCLOAK_REALM` env var doesn't exist in Keycloak. Keycloak returns HTTP 404 for the auth endpoint (`/realms/<bad-realm>/protocol/openid-connect/auth`), which the auth-wrapper or dashboard interprets as a failure and redirects to the raw Keycloak URL (`127.0.0.1:8083`).

### Debugging Steps

1. **Check what realm the dashboard expects:**
   ```bash
   docker exec iacgenie_clamav env | grep KEYCLOAK_REALM
   ```

2. **Check what realms Keycloak actually knows:**
   ```bash
   # Via HTTP (fastest):
   curl -s http://127.0.0.1:8083/realms/
   # Returns JSON with all known realm names

   # Via Admin API (if admin token works):
   curl -s http://127.0.0.1:8083/admin/realms \
     -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool

   # Via direct DB query:
   docker exec iacgenie_postgres psql -U keycloak -d keycloak -c "SELECT name, enabled FROM realm;"
   ```

3. **Test the Keycloak auth endpoint directly:**
   ```bash
   curl -sv https://auth.iacgenie.com/realms/iacgenie/.well-known/openid-configuration
   # 404 or 500 = realm doesn't exist or is broken
   # 200 with JSON = realm exists and is healthy
   ```

4. **Fix:**
   - **Quick fix (recommended):** Change the dashboard env to use an existing realm (`master`):
     ```bash
     docker update --env KEYCLOAK_REALM=master iacgenie_clamav
     docker restart iacgenie_clamav
     ```
   - **Proper fix:** Create the missing realm via Admin REST API (see "Realm Provisioning on First Boot" above)

### Prevention

When provisioning new dashboards, always verify the target realm exists BEFORE deploying:
```bash
docker exec iacgenie_keycloak /opt/keycloak/bin/kc.sh start-dev \
  -c "curl -s http://localhost:8080/realms/" | grep '"name":"iacgenie"'
```

Or check before deploying:
```bash
curl -s http://127.0.0.1:8083/realms/ | python3 -m json.tool | grep -c '"name"'
```

### Related: `default_role` Null in Broken Realm

If a realm was partially created via direct SQL (missing required fields), Keycloak will crash with:
- `Default Role is null for Realm <name>` — missing `default_role` UUID in realm table
- `getBrowserFlow() is null` — missing authentication flow models

**These broken realms must be deleted via SQL before Keycloak can serve the remaining realms:**
```sql
DELETE FROM client WHERE realm_id = '<broken-realm-id>';
DELETE FROM keycloak_role WHERE realm_id = '<broken-realm-id>' OR client IN (SELECT id FROM client WHERE realm_id = '<broken-realm-id>');
DELETE FROM realm_attribute WHERE realm_id = '<broken-realm-id>';
DELETE FROM realm WHERE id = '<broken-realm-id>';
```

After deletion, **restart Keycloak** to clear the in-memory realm cache.

## Nginx Reverse Proxy: Keycloak Admin & Static Assets

When Keycloak is behind nginx, the admin console and static assets need explicit proxy locations. Without these, the admin console loses all CSS/JS (blank page) and public login returns 403.

**Required locations in the Keycloak HTTPS server block:**

```nginx
server {
    listen 443 ssl http2;
    server_name auth.iacgenie.com;

    # Root redirect → public login page (NOT admin console)
    location = / {
        return 302 https://auth.iacgenie.com/realms/iacgenie/web-auth/login-page;
    }

    # Admin console proxy (CSS, JS, admin API)
    location /admin/ {
        proxy_pass http://127.0.0.1:8083/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Static assets (CSS, JS, images)
    location /resources/ {
        proxy_pass http://127.0.0.1:8083/resources/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Public endpoints (login, account, API)
    location /realms/ {
        proxy_pass http://127.0.0.1:8083/realms/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Well-known endpoints
    location /.well-known/ {
        proxy_pass http://127.0.0.1:8083/.well-known/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Key rules:**
- Root `/` should redirect to the **public login page** (`/realms/<realm>/`), NOT `/admin/`
- The admin console uses `<base href="/resources/...">` which resolves to absolute paths — nginx must proxy `/resources/` explicitly
- Both `/admin/` and `/resources/` locations need `proxy_redirect off;` to prevent broken redirects
- When using `KC_HTTP_RELATIVE_PATH: /auth`, the admin UI paths change to `/auth/admin/` and `/auth/resources/` — adjust proxy_pass accordingly

## Common Pitfall: Wildcard DNS + Nginx Server_Name Fallthrough

If accessing a hostname that has no matching `server_name` block in nginx returns a 302 redirect to Keycloak, it's the **nginx wildcard fallthrough pattern**:

1. DNS wildcard `*.iacgenie.com` → Cloudflare
2. Cloudflare tunnel wildcard ingress → nginx port 80
3. Nginx receives `Host: <hostname>` with no matching `server_name` block
4. Nginx falls through to the first server block for that port
5. The first server block on port 80 is often the Keycloak (auth) vHost
6. Keycloak returns `302 → /admin/master/console/` or `302 → auth.iacgenie.com/admin/`

**Debugging steps:**
```bash
# Check if your hostname has a server_name block
ssh vm "grep -n 'server_name <hostname>' /etc/nginx/conf.d/iacgenie.conf"

# Check nginx error log for rewrite/redirect
ssh vm "tail -20 /var/log/nginx/error.log"

# Verify DNS resolves
dig <hostname>.iacgenie.com +short
```

**Fix:** Add a `server_name <hostname>;` block in the nginx template if one doesn't exist. The new block must exist in BOTH the HTTP (port 80) and HTTPS (port 443) sections.

**IacGenie catch-all signature:** a hostname with no matching `server_name` falls to the catch-all block, which on IacGenie returns `404 '{"error": "Not found"}'` (JSON, `content-type: application/octet-stream`). Cloudflare's tunnel catch-all ingress forwards that body, and browsers surface it as **`ERR_INVALID_RESPONSE`** rather than a normal 404 page. Also confirm the backend port actually listens — a template pointing Keycloak at `127.0.0.1:9003` fails because Keycloak's HTTP publishes **host port 8083** (container 8080). Verify before editing: `docker exec <nginx-container> sh -c "curl -sS -m5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8083/"`.

## CRITICAL: Keycloak 26 Redirect URI Validation — Wildcards Don't Work

**Symptom:** Auth flows fail with **"Invalid parameter: redirect_uri"** even though the redirect URI appears to be registered. The realm check succeeds, the client exists, but Keycloak rejects the OIDC authorization request.

**Root cause:** Keycloak 26 does NOT support wildcard matching in redirect URI validation. URIs like `https://*.iacgenie.com/callback` do NOT match `https://clamav.iacgenie.com/callback` — the `*` wildcard only works in the Keycloak admin UI's input field, not in runtime validation.

### How to check and fix

```bash
# Check what redirect URIs are actually registered for a client:
docker exec iacgenie_postgres psql -U keycloak -d keycloak -c "
  SELECT c.client_id, r.value 
  FROM redirect_uris r 
  JOIN client c ON r.client_id = c.id 
  JOIN realm re ON c.realm_id = re.id 
  WHERE re.name = 'iacgenie' AND c.client_id = 'auth-wrapper';
"

# If you see wildcard entries, DELETE them and INSERT exact URIs:
# (Also update client_attributes for good measure)
DELETE FROM redirect_uris WHERE client_id = '<client-uuid>';
INSERT INTO redirect_uris (client_id, value) VALUES
  ('<client-uuid>', 'https://clamav.iacgenie.com/callback'),
  ('<client-uuid>', 'https://pagegen.iacgenie.com/callback'),
  ('<client-uuid>', 'https://crowdsec.iacgenie.com/callback');
```

### ⚠️ Keycloak Caches Realm Data in Memory

**After ANY direct database modification to `redirect_uris`, `realm`, `client`, or `client_attributes` tables, Keycloak MUST be restarted.** The in-memory realm cache is not refreshed:

```bash
docker restart iacgenie_keycloak
# Wait ~20s for startup
curl -s https://auth.iacgenie.com/realms/iacgenie/.well-known/openid-configuration
```

### Keycloak 26 Redirect URI Storage Schema

Redirect URIs are stored in a **separate table**, not in `client_attributes`:

```sql
-- redirect_uris table:
--   client_id (FK) | value (VARCHAR 255)
-- This is the PRIMARY source for runtime validation.

-- client_attributes table:
--   client_id (FK) | name (VARCHAR) | value (TEXT)
-- Can store post.logout.redirect.uris but NOT used for inbound redirect validation.
```

**Table columns differ from older Keycloak versions:**
- `redirect_uris.value` — NOT `c.redirect_uris` (no such column on `client` table)
- `client_attributes.name` — NOT `client_attributes.attribute` (column renamed in KC 26)
## See Also
- `templates/auth-wrapper-v2-app.js` — Full Express.js OIDC gateway template with multi-backend routing
- `references/auth-wrapper-v2-multi-backend.md` — Multi-backend auth wrapper v2: architecture, deployment, troubleshooting
- `references/auth-wrapper-default-keycloak-url.md` — Default Keycloak URL pitfall in shared auth wrappers
- `references/docker-pitfalls.md` — Express secure cookie behind reverse proxy, Docker HEALTHCHECK wget full URL, orphan containers, overlay2 permissions
- `references/auth-wrapper-v2-multi-backend.md` — Session notes: multi-backend auth wrapper v2 architecture, deployment pattern, troubleshooting (port cleanup, client_secret missing, clamav-web-client)
## See Also
- `templates/auth-wrapper-v2-app.js` — Full Express.js OIDC gateway template with multi-backend routing
- `references/auth-wrapper-v2-multi-backend.md` — Multi-backend auth wrapper v2: architecture, deployment, troubleshooting
- `references/auth-wrapper-default-keycloak-url.md` — Default Keycloak URL pitfall in shared auth wrappers
- `references/docker-pitfalls.md` — Express secure cookie behind reverse proxy, Docker HEALTHCHECK wget full URL, orphan containers, overlay2 permissions
- `references/keycloak-26-export-fields.md` — Fields removed/renamed in Keycloak 26 realm export
- `references/keycloak-multi-tenant-setup.md` — Keycloak multi-tenant RBAC architecture
- `references/keycloak-26-credential-recovery.md` — Admin credential table schema, SQL patterns, password hash generation, admin login failure checklist
- `references/keycloak-26-realm-import-modification.md` — Export→modify→import workflow: rename realm, regenerate UUIDs (preserving clientIds), replace JSON-key references, add clients/users, common import errors
- `references/keycloak-26-credential-json-error.md` — "Cannot parse the JSON" error, credential_data format (`additionalParameters`, not `algorithmData` as array), KC_BOOTSTRAP_ADMIN pitfall, docker network workaround
- `references/keycloak-missing-realm-redirect-loop.md` — Diagnosing and fixing auth redirect loops caused by missing Keycloak realms
- `references/keycloak-26-redirect-uri-regex.md` — Why `https://*.domain.com/callback` wildcards fail in KC 26 redirect URI validation, exact-URI required, SQL table schema, restart requirement
- `references/keycloak-2026-08-10-admin-auth-debug.md` — Session transcript: multiple admin users, corrupted credential_data, PBKDF2 hash verification, `bash -c` root user pitfall
- `references/keycloak-26-kcadm-stdin-broken.md` — The stdin bug in Keycloak 26 kcadm.sh (ALL create/update/delete commands fail), full Python/urllib workaround, curl approach with OIDC token endpoint
- `references/keycloak-26-kcadm-limitations.md` — Quick reference: what kcadm.sh commands still work vs broken in KC 26
- `references/keycloak-26-kcadm-config-file-workaround.md` — kcadm config file + set-password approach for password reset
- `scripts/kc-admin-reset.sh` — Automated admin password reset using kcadm config file + set-password
- `scripts/verify-kc-password.py` — PBKDF2 password hash verification
- `scripts/keycloak-26-diagnostics.py` — Automated health-check script
- `references/multi-template-deployment.md` — Coordinated 5+ template deployment workflow


## Consolidated Multi-Tenant Patterns (absorbed sibling skill)

> Sibling skill consolidated here; full detail retained in the archived package at `~/.hermes/skills/.archive/multi-tenant-architecture/`.

### `multi-tenant-architecture` — Keycloak realm multi-tenancy
Multi-tenant infrastructure patterns — Keycloak realm setup, tenant isolation, and deployment. See archived `multi-tenant-architecture/`.
