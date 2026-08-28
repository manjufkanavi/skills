# Gitea 1.27 Runner Authentication Debugging

## Session context

- Date: 2026-08-01
- Gitea version: 1.27.0 (Go 1.26.5)
- Runner binary: `act_runner v0.6.1` (Gitea runner, go-woodpecker based)
- VM: `192.168.0.118` (user: `mkanavi`)
- Runner config: `/home/mkanavi/.runner`
- Runner systemd: `/etc/systemd/system/gitea-runner.service`
- Postgres DB: `dc01d16c31a0_iacgenie-postgres` (user: `gitea`, db: `gitea`)

## Symptoms

Runner logs:
```
Error: unknown: rpc error: code = Unauthenticated desc = unregistered runner
```

Runner crashes in a restart loop (exit-code=1).

## Root Cause

The `action_runner` table in Postgres was **empty** — all runner records were lost during a database migration. The runner config (`/home/mkanavi/.runner`) pointed to a now-orphaned runner ID.

## Database Schema (Gitea 1.27)

### `action_runner_token` table — Registration tokens

| Column       | Type         | Purpose                          |
|-------------|--------------|----------------------------------|
| `id`        | bigint (PK)  | Auto-increment                  |
| `token`     | varchar      | **Plaintext** — what the runner sends |
| `owner_id`  | bigint       | Admin user who created the token |
| `repo_id`   | bigint       | Scoped to a specific repo (NULL = instance-wide) |
| `is_active` | boolean      | Must be true for auth to pass   |
| `created`   | bigint       | Unix timestamp                   |
| `updated`   | bigint       | Unix timestamp                   |
| `deleted`   | bigint       | Soft-delete timestamp            |

**No foreign key** linking to `action_runner`. The link is implicit: the runner's UUID from the config matches the `action_runner.uuid`.

### `action_runner` table — Runner records

| Column            | Type         | Purpose                            |
|-------------------|--------------|-------------------------------------|
| `id`              | bigint (PK)  | Auto-increment                     |
| `uuid`            | char         | Runner's unique identifier         |
| `name`            | varchar      | Human-readable name                |
| `version`         | varchar      | Runner protocol version            |
| `owner_id`        | bigint       | Admin user who registered it       |
| `repo_id`         | bigint       | Scoped to a repo (NULL = instance) |
| `token_hash`      | varchar      | SHA256(token + salt) — auth token |
| `token_salt`      | varchar      | Salt for token hashing (often empty)|
| `ephemeral`       | boolean      | Single-use runner                  |
| `is_disabled`     | boolean      | Soft-disable                       |
| `created/updated` | bigint       | Unix timestamps                    |

## Authentication Flow (gRPC)

```
Runner (.runner config) ──token──► gRPC Declare() ──token──► Gitea server
                                                    │
                                          Lookup in action_runner_token.token
                                                    │
                                          Lookup in action_runner.uuid (matching)
                                                    │
                                          Verify token_hash = SHA256(token + salt)
                                                    │
                                          Return runner UUID if match
```

**Key insight:** `action_runner_token` stores the plaintext token (for registration). `action_runner` stores the `token_hash` (for authentication). These are two different purposes for the same token value.

## Debugging Steps That Were Tried

1. **Direct DB insert** — Inserted matching token and hash into both tables. Runner still failed. Investigation: the runner's token in `.runner` config didn't match the hash computed from the DB insert (config had old token value).

2. **Fix hash mismatch** — Updated DB `token_hash` to `SHA256(config_token)`. Runner still failed.

3. **Admin API** — `POST /api/v1/admin/runners` → 404. Confirmed absent in Gitea 1.27.

4. **Web UI** — `/-/admin/actions/runners` → 303 redirect to `/user/settings/change_password` because the admin password had been recently reset via CLI, triggering a "must change password" gate.

5. **HTTPS debugging** — `Secure` flag on Gitea session cookies prevents HTTP-based curl debugging. Login via HTTPS succeeds but the page redirects to password-change.

6. **CLI password reset** — `docker exec -u 1000 gitea gitea admin user change-password` works but creates the password-change gate.

## Verification Commands

```bash
# Check runner status
systemctl status gitea-runner --no-pager
journalctl -u gitea-runner --no-pager -n 5

# Check runner config
cat /home/mkanavi/.runner

# Verify token match in DB
docker exec dc01d16c31a0_iacgenie-postgres psql -U gitea -d gitea -c "SELECT * FROM action_runner;"
docker exec dc01d16c31a0_iacgenie-postgres psql -U gitea -d gitea -c "SELECT * FROM action_runner_token;"

# Compute expected hash locally
python3 -c "import hashlib; print(hashlib.sha256(b'your-token-here').hexdigest())"
```

## Key SQL Queries

```sql
-- Check all runners (not just deleted ones)
SELECT id, uuid, name, is_disabled, token_hash FROM action_runner WHERE deleted = 0;

-- Check all registration tokens
SELECT id, token, is_active, repo_id FROM action_runner_token WHERE deleted = 0;

-- Find by UUID (link between tables)
SELECT r.*, t.token FROM action_runner r
JOIN action_runner_token t ON r.uuid::text = t.token
WHERE r.uuid = 'your-uuid-here';
```

## Future Workaround for Gitea 1.27

Until Gitea restores runner registration API/UI:
- Keep a backup of the `.runner` config file
- Maintain a backup of the token and token_hash values from the DB
- If the runner needs to be re-registered, reconstruct the DB entries from backup rather than trying to generate a new token
- Consider using Gitea's built-in secret management to store the registration token
