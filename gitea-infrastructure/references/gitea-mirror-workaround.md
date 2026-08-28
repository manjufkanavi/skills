# Gitea Mirrors — When API Returns 404

## Problem

In Gitea 1.23.x, mirror API endpoints return **404**:

```
POST /api/v1/repos/{owner}/{repo}/mirror       → 404
POST /api/v1/repos/{owner}/{repo}/mirrors       → 404
POST /api/v1/repos/{owner}/{repo}/mirror-sync   → 200 OK (accepts request but may not start sync)
```

The mirror table exists in the DB but the API route is not registered. Use direct SQL insertion.

## Detection

Test the endpoint before attempting mirrors:

```bash
TOKEN=*** -s -o /dev/null -w '%{http_code}' \
  "http://127.0.0.1:3000/api/v1/repos/manjufkanavi/iacgenie/mirrors" \
  -H "Authorization: token $TOKEN"
# If 404 → use DB workaround below
```

## Workaround: Direct Database Insert

### Step 1: Get repo ID

```bash
docker exec iacgenie_postgres psql -U gitea -d gitea \
  -c "SELECT id, name, owner_id FROM repository WHERE owner_id = 1 AND name = 'iacgenie';"
# → id | name          | owner_id
# →  1 | iacgenie      |        1
```

### Step 2: Verify mirror table exists

```bash
docker exec iacgenie_postgres psql -U gitea -d gitea -c "\dt mirror"
```

**Actual Gitea 1.23.x `mirror` table schema (verified 2026-08-05):**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | bigint | not null | `nextval('mirror_id_seq')` |
| `repo_id` | bigint | | |
| `interval` | bigint | | |
| `enable_prune` | boolean | not null | `true` |
| `updated_unix` | bigint | | |
| `next_update_unix` | bigint | | |
| `lfs_enabled` | boolean | not null | `false` |
| `lfs_endpoint` | text | | |
| `remote_address` | varchar(2048) | | |

### Step 3: Insert mirror entries

```bash
GITHUB_PAT="your-github-pat"
OWNER="manjufkanavi"

docker exec iacgenie_postgres psql -U gitea -d gitea <<'SQL'
-- Insert pull mirrors for all repos (Gitea 1.23 schema)
INSERT INTO mirror (repo_id, interval, enable_prune, updated_unix, next_update_unix, lfs_enabled, lfs_endpoint, remote_address)
VALUES
  (1, 3600, true, EXTRACT(EPOCH FROM NOW())::BIGINT, 0, false, '',
   'https://${GITHUB_PAT}@github.com/manjufkanavi/iacgenie.git'),
  (2, 3600, true, EXTRACT(EPOCH FROM NOW())::BIGINT, 0, false, '',
   'https://${GITHUB_PAT}@github.com/manjufkanavi/iacgenie-unified-infra.git'),
  (3, 3600, true, EXTRACT(EPOCH FROM NOW())::BIGINT, 0, false, '',
   'https://${GITHUB_PAT}@github.com/manjufkanavi/LightSerp.git');

-- CRITICAL: mark repos as mirrors in the repository table
UPDATE repository SET is_mirror = true
WHERE id IN (1, 2, 3);
SQL
```

**⚠️ Critical: Always update `repository.is_mirror = true`.** Without this flag:
- Gitea's UI shows repos as regular repos (not mirrors)
- Mirror sync jobs may not trigger
- The mirror functionality is incomplete

### Step 4: Trigger initial sync

```bash
TOKEN=*** repo in iacgenie iacgenie-unified-infra LightSerp; do
  curl -s -X POST \
    "http://127.0.0.1:3000/api/v1/repos/${OWNER}/${repo}/mirror-sync" \
    -H "Authorization: token $TOKEN" \
    -w "\n%{http_code}"
  echo "  → $repo"
done
```

### Step 5: Verify mirrors are set up

```bash
docker exec iacgenie_postgres psql -U gitea -d gitea -t \
  -c "SELECT m.id, r.name, m.remote_address, m.interval, m.enable_prune, m.updated_unix, r.is_mirror FROM mirror m JOIN repository r ON m.repo_id = r.id;"
```

Expected output:
```
  1 | iacgenie               | https://github.com/manjufkanavi/iacgenie.git | 3600 | t | <epoch> | t
  2 | iacgenie-unified-infra | https://github.com/manjufkanavi/iacgenie-unified-infra.git | 3600 | t | <epoch> | t
  3 | LightSerp              | https://github.com/manjufkanavi/LightSerp.git | 3600 | t | <epoch> | t
```

### Step 6: Verify repo content

```bash
for repo in iacgenie iacgenie-unified-infra lightserp; do
  echo "=== $repo ==="
  git --git-dir=/home/mkanavi/docker/iacgenie/data/gitea/git/repositories/manjufkanavi/$repo.git log --oneline -3
done
```

## Mirror Architecture Decision

```
GitHub ──(pull mirror, 1h)──→ Gitea (internal CI/CD)
↑                                 ↑
Push here only                    Actions run here
                                  on mirrored code
```

**Rule: Push to GitHub only.** Gitea pulls hourly via pull mirror. This avoids infinite sync loops.

## Common Pitfalls

1. **Missing `is_mirror = true`** — mirror table entries alone are insufficient; the repository table flag must also be set
2. **Wrong column names** — Gitea 1.23 uses `remote_address` (not `source`), `enable_prune` (not `is_prune`), `interval` as `bigint` (seconds, not duration string)
3. **Wrong mirror table schema** — older references show `source`, `is_prune`, `has_slack`, `is_task` columns — these are from an older Gitea version. Use the schema above.
4. **Case-sensitive repo paths** — Gitea stores repos in lowercase dirs (`lightserp.git`) even if the repo name is `LightSerp`. Use the lowercase filesystem path when checking bare repos.
5. **Trigger sync before verifying** — `mirror-sync` API returns 200 but the actual git fetch may take time. Wait or check bare repo `git log` to confirm content was pulled.
6. **Env vars in heredocs** — Use `<<'SQL'` (single-quoted delimiter) to prevent bash from expanding variables inside the SQL heredoc.

## Integration with Ansible

The `gitea_mirror` Ansible role encapsulates this entire workflow:
- Verifies mirror table exists
- Inserts mirror entries via psql
- Sets `is_mirror = true` on repos
- Triggers initial sync via API
- Reports status

Add to `services.yml` roles list under Phase 10.5.

## Decision Guide

| Situation | Approach |
|-----------|----------|
| Gitea < 1.23, mirrors API works | Use API: `POST /api/v1/repos/{owner}/{repo}/mirrors` |
| Gitea 1.23.x, API returns 404 | Direct DB insert + `is_mirror` update (above) |
| Need pull from GitHub | Use GitHub PAT in `remote_address` URL |
| Need push to GitHub | Use deploy key or SSH URL (push mirror) |
| Reliable two-way sync | Cron-based script OR mirror + push mirror carefully |
