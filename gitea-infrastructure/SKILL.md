---
name: gitea-infrastructure
description: "Gitea infrastructure management — Admin password reset, Actions feature flag, runner registration, API token management, repo setup, and sync/mirroring."
version: 1.5.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [gitea, ci-cd, actions, runner, admin, infrastructure, sync, mirroring]
    related_skills: [github, dev-workflow]
---

# Gitea Infrastructure Management

Operational commands for administering a self-hosted Gitea instance: password reset, Actions enablement, runner installation, API tokens, repository setup, sync/mirroring, and email reporting.

## Prerequisites

- SSH access to the Gitea host VM
- Docker access (`docker exec` or `docker ps`)
- **SSH agent must have the key loaded** — `ssh-add ~/.ssh/newvm_key` (or appropriate key). The macOS SSH agent does NOT auto-load keys across sessions. Verify with `ssh-add -l`; if empty, add the key first.
- Gitea running in Docker (typically `iacgenie-gitea`)

## Admin Password Reset

When the original admin password is unknown or the stored hash won't match (pbkdf2/salt mismatch from manual DB edits), use the Gitea CLI via Docker:

```bash
docker exec -u 1000 <container> gitea admin user change-password \
  --username admin \
  --password 'NewPassword!' \
  --must-change-password=false
```

This is the **reliable** method. Do NOT try to manually hash passwords in the DB — Gitea's pbkdf2 format uses a salt column and `passwd_hash_algo` field (e.g. `pbkdf2$50000$50`), and matching requires the exact salt. The CLI handles hashing correctly.

### CRITICAL: `--must-change-password=false` is NOT default
If you omit `--must-change-password=false`, Gitea sets the flag that forces a password change on the NEXT login via web UI. This blocks ALL admin pages (`/admin/*`, admin Actions settings, runner registration pages) until the user completes the "change password" flow.

**Default behavior (dANGEROUS):** `docker exec -u 1000 gitea gitea admin user change-password --username admin --password X` → forces web UI password change gate.

**Correct:** Always pass `--must-change-password=false` explicitly.

### Passwords with special characters (`$`, `!`, `@`, etc.)
When passing passwords containing `$` via shell commands, the `$` gets expanded by bash. ALWAYS use:
- Single-quoted heredocs: `<<'EOF'` (NOT `<<EOF`)
- Or pass via a temp file/env var instead of inline
- Or use `docker exec -u 1000 <container> gitea ...` with the password directly (docker exec passes args through without shell expansion)

### Troubleshooting

- `change-password` subcommand (NOT `update`) — `gitea admin user update` doesn't handle password changes in Gitea 1.23+
- Use `--must-change-password=false` to skip the "update password on first login" prompt
- Passwords with special characters should be quoted in shell commands

## Gitea 1.27 Runner Registration Changes

Gitea 1.27 broke the previous runner registration paths:

- `GET/POST /api/v1/admin/runners` → **404** (endpoint removed)
- `/-/admin/actions/runners` → **303 redirect** to `/user/settings/change_password` when admin password was recently reset via CLI
- **Root cause:** `docker exec gitea gitea admin user change-password` resets the password but triggers a mandatory password-change flow on next login, blocking all admin pages

### Authentication layer change

Runner authentication is **gRPC** (`Declare` RPC), not HTTP REST. The token flow:

1. Runner sends token from `.runner` config via gRPC metadata
2. Gitea looks up token in `action_runner_token.token` (plaintext, for registration validation)
3. Gitea looks up runner in `action_runner` by UUID, verifies `token_hash = SHA256(token + salt)`
4. **Note:** `token` in `action_runner_token` ≠ `token_hash` in `action_runner` — they serve different purposes

### Credential hashing (PBKDF2) — do NOT try to crack admin passwords

Gitea stores passwords as PBKDF2 hashes with a per-user salt. There is **no way to recover or reverse the admin password** from the DB. If the CLI `change-password` command is available, use it. Otherwise, the admin is stuck until they can reach the web UI.

### CLI must run as non-root

```bash
# WRONG — Gitea refuses to run as root:
docker exec iacgenie-gitea gitea admin user change-password --username admin --password NewPass

# CORRECT — Gitea container user is gid 1000:
docker exec -u 1000 iacgenie-gitea gitea admin user change-password --username admin --password NewPass
```

Error: `F] Gitea is not supposed to be run as root`

### Admin password change triggers "change password on first login" gate

After `change-password` CLI, Gitea sets `must-change-password` flag. Next login to `/user/settings/change_password` is mandatory, and this page is required before ANY admin page (including `/-/admin/actions/runners`).

**Workaround:** If you have the original password (e.g., from `.env`), change it back with the CLI so the gate doesn't trigger. If you don't have the original, you must use the web UI to set a new password — but the `Secure` cookie flag on Gitea sessions may prevent HTTP-based debugging.

### Debugging runner auth failures (non-trivial debugging path)

When runner logs `unregistered runner` despite correct token in DB:

1. Verify the token in `.runner` config matches `action_runner_token.token` EXACTLY
2. Verify `token_hash = SHA256(token + salt)` — compute it locally and compare with `action_runner.token_hash`
3. Verify `action_runner.uuid` matches `action_runner_token.uuid` (they are linked, not by foreign key)
4. If all match, the issue is likely:
   - Version incompatibility between runner binary and Gitea
   - The `Secure` flag on Gitea's session cookies (prevents HTTP session reuse, making web UI token generation via HTTP impossible)

See `references/gitea-1-27-runner-auth-debug.md` for the full debugging transcript and database schema.

## Actions Feature Enablement

Gitea 1.23 ships with Actions **disabled by default**. All Actions API endpoints return 404 when disabled.

### Detect

```bash
docker exec <container> cat /etc/gitea/app.ini | grep -A2 '\[actions\]'
# Expected output when disabled:
# [actions]
# ENABLED = false
```

### Enable

Edit the config on the host:

```bash
sed -i 's/^ENABLED = false$/ENABLED = true/' /home/mkanavi/docker/iacgenie/gitea_data/config/app.ini
docker restart <container>
```

### Verify

After restart, `gitea actions` CLI should be available inside the container:
```bash
docker exec <container> gitea actions --help
```

## Service Renaming: `git.iacgenie.com` → `gitea.iacgenie.com`

**Date:** 2026-08-14

When renaming a Gitea subdomain, update **all** references simultaneously:

1. **Nginx vHost** — `server_name git.iacgenie.com;` → `server_name gitea.iacgenie.com;` (in BOTH HTTP and HTTPS blocks)
2. **Cloudflare tunnel config** — `hostname: git.iacgenie.com` → `hostname: gitea.iacgenie.com`
3. **Keycloak SSO client** — redirect URIs like `https://git.iacgenie.com/...` → `https://gitea.iacgenie.com/...`
4. **DNS** — if not using wildcard, update A record
5. **Any hardcoded references** in other services' `.env` files or configs

**Debugging if something breaks after rename:** If a domain returns a redirect to `auth.iacgenie.com/realms/...`, the vHost `server_name` likely wasn't updated for the new hostname — traffic falls through to the Keycloak vHost (first match on port 443).

**Fix command:**
```bash
sudo sed -i 's/server_name git\.iacgenie\.com;/server_name gitea.iacgenie.com;/g' /etc/nginx/conf.d/iacgenie.conf
sudo nginx -t && sudo systemctl reload nginx
```

## API Token Management

### Via Web UI (RELIABLE)

The Gitea 1.23 API endpoint for creating access tokens via JSON body has a known parsing bug (returns 422). **Use the web UI instead.**

1. Go to `https://<gitea>/user/settings/applications`
2. Under "Generate New Token":
   - Set Token Name
   - Select "All (public, private, and limited)" radio
   - **Expand "Select permissions"** (click the ▶ triangle)
   - Set "repository" combobox to **Read and Write**
   - Click "Generate Token"
3. Copy the displayed token immediately — it's only shown once.

### IMPORTANT: Token values CANNOT be recovered from the database

Gitea stores access tokens as `token_hash` (SHA256 of token value + `token_salt`). The plaintext token value is **never stored** — it's only displayed once at creation time.

### Via CLI (Gitea 1.27+)

```bash
# Run as the Gitea container user (UID 1000), NEVER as root
docker exec -u 1000:1000 <container> gitea admin user generate-access-token \
  --username admin \
  --token-name hermes-ci \
  --raw
```

**Gitea 1.27 scope names are strict** — invalid scopes cause immediate failure:
- `"all"` — valid (equivalent to all scopes)
- `"write:repository"`, `"read:repository"` — valid
- `"admin:org"`, `"admin:organization"`, `"admin:user"` — valid
- ❌ `"admin"` — INVALID (no scope named `admin`)
- ❌ `"write:org"` — INVALID (no scope named `write:org`)
- When in doubt, omit `--scopes` for default (all scopes).

**CRITICAL: CLI must run as non-root.** `docker exec` (without `-u 1000:1000`) → Gitea exits with `[F] Gitea is not supposed to be run as root`.

### SSH tunnel instability

SSH tunnels for the Gitea web UI **die frequently and silently**. Before relying on browser automation:
- Check tunnel health: `ps aux | grep "ssh.*-N"`
- If dead, restart the tunnel
- Use `docker exec gitea gitea` CLI commands as an alternative

## Runner Token Generation

### Per-Repo Tokens

```bash
docker exec <container> gitea actions generate-runner-token -s admin/repo-name
```

### CRITICAL: Admin Username ≠ "admin"

The default Gitea admin username is often **not** `admin`. Check with:
```bash
docker exec iacgenie-gitea gitea admin user list
```

### Runner Config URL Must Use External Endpoint

When Cloudflare Tunnel is the access path, the runner `.runner` config **must** use the external URL (`https://gitea.iacgenie.com`), NOT `http://127.0.0.1:3000`. The gRPC `Declare` RPC requires a resolvable hostname — localhost inside the runner's Docker context may not reach the host.

**Broken pattern:**
```json
{"address": "http://127.0.0.1:3000", ...}
```

**Correct pattern:**
```json
{"address": "https://gitea.iacgenie.com", ...}
```

If the runner config has the wrong address, delete it and re-register:
```bash
sudo systemctl stop gitea-runner
rm -f /home/mkanavi/.runner
cd /home/mkanavi
~/bin/gitea-runner register --instance https://gitea.iacgenie.com --token <NEW> --no-interactive
sudo systemctl start gitea-runner
```

### Runner Config URL Must Use External Endpoint

When Cloudflare Tunnel is the primary access path, the runner `.runner` config **must** use the external URL (`https://gitea.iacgenie.com`), NOT `http://127.0.0.1:3000`. The gRPC `Declare` RPC needs a hostname that resolves from the runner's container context.

**Broken pattern:**
```json
{"address": "http://127.0.0.1:3000"}
```

**Correct pattern:**
```json
{"address": "https://gitea.iacgenie.com"}
```

## Gitea "Installed But Empty" State — Detection & Remediation

A Gitea instance can be **fully installed** (INSTALL_LOCK=true, all DB tables created, homepage loads) but have **zero users and zero repos**. This happens when Gitea completed its first-run setup but the admin user was never explicitly created or was accidentally deleted.

### Detection

Run these checks in order:

```bash
# 1. Does the homepage load? (confirms Gitea is running)
curl -s http://127.0.0.1:3000/ | head -3
# → Returns HTML → Gitea is running

# 2. Is there any admin user?
docker exec iacgenie-gitea gitea admin user list
# → Empty output → NO users (this is the broken state)

# 3. Check DB directly:
docker exec iacgenie_postgres psql -U postgres -d gitea -c \
  'SELECT id, name, email, is_admin FROM "user";'
# → 0 rows → confirmed empty

# 4. Check if actions tables exist (confirms full DB schema):
docker exec iacgenie_postgres psql -U postgres -d gitea -c '\dt action_*'
# → Lists tables → DB schema is complete, just no data
```

### Remediation (Phase-by-Phase)

```bash
# Phase 1: Create admin user
docker exec -u 1000 iacgenie-gitea gitea admin user create \
  --username manjufkanavi \
  --password 'StrongPassword!' \
  --email admin@iacgenie.com \
  --admin \
  --must-change-password=false

# Phase 2: Verify user exists
docker exec iacgenie-gitea gitea admin user list

# Phase 3: Create API token (needed for mirrors, API calls)
# → Must use web UI (API has a known bug with JSON body in Gitea 1.23)
# Or via CLI:
docker exec -u 1000:1000 iacgenie-gitea gitea admin user generate-access-token \
  --username manjufkanavi \
  --token-name automation \
  --raw

# Phase 4: Enable Actions
docker exec -u 1000 iacgenie-gitea sh -c '
  sed -i "/^\\[security\\]/i [actions]\nENABLED = true" /etc/gitea/app.ini
  cat /etc/gitea/app.ini | grep -A1 "\\[actions\\]"
'
docker exec iacgenie-gitea systemctl restart gitea  # or docker restart

# Phase 5: Create repos
TOKEN=$(docker exec -u 1000:1000 iacgenie-gitea gitea admin user generate-access-token \
  --username manjufkanavi --token-name automation --raw)
for repo in iacgenie iacgenie-unified-infra LightSerp; do
  curl -s -u "manjufkanavi:$TOKEN" -X POST \
    "http://127.0.0.1:3000/api/v1/user/repos" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$repo\",\"auto_init\":false,\"private\":true,\"default_branch\":\"main\"}"
done

# Phase 6: Register runner
docker exec -u 1000 iacgenie-gitea gitea actions generate-runner-token
cd /home/mkanavi
rm -f ~/.runner
~/bin/gitea-runner register --instance https://gitea.iacgenie.com --token <NEW> --no-interactive
sudo systemctl start gitea-runner
```

### Common Causes

1. **Fresh install with `--INSTALL_LOCK=true`** — Gitea locks itself before creating the first admin user
2. **Database restored from empty backup** — tables exist but no users
3. **`gitea admin user delete`** — accidentally removed the only user
4. **Non-rootless → rootless migration** — user table reset during migration

### Runner Confirmed Running

After the above steps, verify the runner registers:
```bash
# Check runner is connecting (no more 500 errors):
docker exec iacgenie-gitea journalctl -u gitea --since "1 minute ago" | grep -c "500"
# → Should be decreasing

# Check DB:
docker exec iacgenie_postgres psql -U postgres -d gitea -c "SELECT * FROM action_runner;"
# → Should show 1 row with runner UUID
```

```bash
curl -sL 'https://dl.gitea.com/act_runner/0.6.1/act_runner-0.6.1-linux-amd64' -o ~/bin/gitea-runner
chmod +x ~/bin/gitea-runner
```

### Register Runner

```bash
~/bin/gitea-runner register --token <TOKEN> --instance https://gitea.iacgenie.com --name gitea-runner-1 --no-interactive
```

### Systemd Service

```ini
[Unit]
Description=Gitea Runner
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=mkanavi
WorkingDirectory=/home/mkanavi
ExecStart=/home/mkanavi/bin/gitea-runner daemon -c /home/mkanavi/.runner
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Troubleshooting Runner

- **`.runner` config path** — act_runner v0.6.1 reads config from `~/.runner` relative to its **working directory**, not `~/.config/`. Set `WorkingDirectory=/home/mkanavi` in systemd.
- **Actions API endpoints return 404 via REST** — `/api/v1/admin/actions/runners` do not exist in Gitea 1.23.x. Runner management is via CLI or web UI only.

### Shell Quoting Pitfalls

#### `***` in `.env` files — triple-protected variable syntax
Values prefixed with `***` in `.env` files create triple-quote hell in shell commands.

**Safe extraction pattern:**
```bash
ssh host 'python3 << '\''PYEOF'\''
with open("/path/to/.env") as f:
    for line in f:
        if "***" in line and not line.strip().startswith("#"):
            val = line.split("=", 1)[1]
            if val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            print(val)
            break
PYEOF'\''
```

#### Passwords containing `$` — bash expansion trap
The `$` character is expanded by bash even inside single-quoted heredocs passed through `ssh` when the Python code contains `***` patterns. If a password has `$` (e.g., `b$4JRq3iQOJ@eH`):
- **Never pass inline in shell**: `curl -u "admin:b$4JRq"` → bash expands `$4JR` to nothing
- **Use docker exec directly**: `docker exec -u 1000 gitea gitea ... --password 'b$4JRq3iQOJ@eH'` (args bypass shell)
- **Use Python via heredoc**: The Python script approach above avoids shell interpretation

## Repository Setup via API

```bash
curl -s -u admin:password -X POST \
  "https://gitea.iacgenie.com/api/v1/user/repos" \
  -H "Content-Type: application/json" \
  -d '{"name":"repo-name","auto_init":true,"private":false,"default_branch":"main"}'
```

Note: the endpoint is `/api/v1/user/repos` (NOT `/api/v1/repos`).

### Push Mirror Setup via API (preferred when available)

```bash
curl -s -u admin:password -X POST \
  "https://gitea.iacgenie.com/api/v1/repos/admin/repo-name/mirrors" \
  -H "Content-Type": "application/json" \
  -d '{"interval":"5m","mirror_address":"https://github.com/mkanavi/repo-name.git"}'
```

If API returns 404, see `references/gitea-mirror-workaround.md`.

### SSH → Gitea Deploy Keys

Deploy keys live on the Gitea host (VM), so generate them there and push the public key content back:

```bash
# Generate on VM, get public key content
ssh host 'ssh-keygen -t ed25519 -f /home/mkanavi/.ssh/gitea_${repo}_deploy_key -N "" -C "gitea-mirror-$repo" -q && cat /home/mkanavi/.ssh/gitea_${repo}_deploy_key.pub'

# Write pub key to temp file on local machine (needed for gh CLI)
echo "ssh-ed25519 ... gitea-mirror-repo" > /tmp/gitea_repo.pub

# Add to GitHub
gh repo deploy-key add /tmp/gitea_repo.pub -R owner/repo --title "Gitea Mirror" --allow-write
```

**CRITICAL:** `gh repo deploy-key add` requires a **file path** as its first argument and `-R owner/repo` as the second. It does NOT accept inline content, pipes, or `--public-key` flags. Passing inline or via pipe fails with "accepts 1 arg(s), received 2".

### CRITICAL: Pre-push Hook Interference with Dual-Remote Pushes

## Gitea Bare Repo Pre-receive Hooks (push workaround)

When pushing directly to Gitea's bare repos via filesystem path (bypassing HTTP API), the `pre-receive.d/gitea` hook fails:

```
remote: ./hooks/pre-receive.d/gitea: line 3: /usr/local/bin/gitea: No such file or directory
error: failed to push some refs
```

**Why:** `/usr/local/bin/gitea` exists only inside the Docker container, not on the host filesystem.

### Workaround
Temporarily remove hooks, push, restore:
```bash
BARE=/home/mkanavi/docker/iacgenie/gitea_data/data/git/repositories/manjufkanavi/repo.git
mkdir -p /tmp/hook-backup && cp -r $BARE/hooks/* /tmp/hook-backup/
rm -rf $BARE/hooks
# ... push here ...
cp -r /tmp/hook-backup/* $BARE/hooks/
rm -rf /tmp/hook-backup
```

**Better alternative:** Push through the HTTP API (e.g., `git push gitea main` from a clone that has the `gitea` remote configured) which routes through the running container where the hooks work.

## Gitea Rootless `environment-to-ini.go` Pitfall

The rootless Gitea Docker image runs `environment-to-ini.go` on startup which reads all `GITEA__section__key` env vars and **overwrites** `/etc/gitea/app.ini` with merged values. Missing env vars get reset to defaults on restart.

### Symptoms
- `INSTALL_LOCK` set in app.ini but Gitea still shows installation page after restart
- `GITEA__security__INSTALL_LOCK` not in `docker exec container env` output
- Config changes in bind-mounted app.ini get silently overwritten

### Diagnosis
```bash
docker exec <container> env | grep GITEA
docker exec <container> cat /etc/gitea/app.ini | grep INSTALL_LOCK
```

### Fix
Add missing env var to compose file and force-recreate (NOT restart):
```bash
# In docker-compose.yml, add under environment:
GITEA__security__INSTALL_LOCK: "true"
docker compose -f docker-compose.yml up -d --force-recreate gitea
```

## Gitea Rootless Migration — Data Loss Pattern

When migrating Gitea from a **non-rootless image** (`gitea/gitea:1.23.4`) to the **rootless variant** (`gitea/gitea:latest-rootless`), the container's data directory structure changes:

- Non-rootless: repos stored under `/data/gitea/data/git/repositories/<user>/`
- Rootless: repos expected under `/data/gitea/git/repositories/<user>/` (different path)

**Symptoms:**
- `docker logs` shows Gitea starting normally (no migration errors)
- `GET /api/v1/user/repos` returns the repos (repo metadata in DB is intact)
- `GET /api/v1/repos/admin/<repo>/commits/main` → 404 (objects inaccessible)
- `docker exec` into Gitea → `find / -name HEAD -type f` returns nothing (objects appear missing)

**Root cause:** The rootless image creates a new data directory layout. The old repos exist on disk under the old path (`/data/gitea/data/git/repositories/manjufkanavi/`) but Gitea looks in the rootless path (`/data/gitea/git/repositories/`).

**Fix:**
1. **Restore the backup database** (if available): `docker cp gitea_data/data/gitea.db.backup iacgenie-gitea:/data/gitea/gitea.db`
2. **Verify repos appear:** `wget -qO- 'http://127.0.0.1:3000/api/v1/user/repos' --header='Authorization: token <TOKEN>'`
3. **If repos still missing:** Check if repos exist at the old path: `ls /data/gitea/data/git/repositories/manjufkanavi/`

**Prevention:** Always back up `gitea.db` and `gitea.db.backup` before any Gitea image change. The backup DB contains the full repo/user mapping and survives image migrations.

## Post-Restore API Mismatch

After restoring an old backup database (migration 312-era), some API endpoints return 404 even though the repo metadata works:

- ✅ `GET /api/v1/user/repos` — works (repo metadata in DB is intact)
- ❌ `GET /api/v1/repos/admin/<repo>/commits/main` — 404
- ❌ `GET /api/v1/repos/admin/<repo>/git/ref/heads/main` — 404

**Root cause:** The Gitea binary (latest-rootless) expects newer git object references or migration 343-era schema. The old DB's object references are compatible but the API paths have shifted.

**Workaround:** Use the **Gitea CLI inside the container** or **direct git operations on bare repos** instead of the REST API for post-restoration operations:
```bash
# Get commit info (replaces GET /commits/main)
docker exec iacgenie-gitea git -C /data/gitea/data/git/repositories/manjufkanavi/<repo>.git log --oneline -5

# Get file listing (replaces GET /contents)
docker exec iacgenie-gitea git -C /data/gitea/data/git/repositories/manjufkanavi/<repo>.git ls-tree -r HEAD --name-only

# Update a branch ref directly (bypasses API entirely)
docker exec iacgenie-gitea git -C /path/to/bare/repo.git update-ref refs/heads/main <NEW_SHA>
```

## Git Bare Repo Direct Manipulation — Pre-Receive Hook Pitfall

When pushing directly to a Gitea bare repo via filesystem path (not through SSH or the HTTP API), the `pre-receive` hook fails:

```
remote: error: Rejecting changes as Gitea environment not set.
remote: error: If you are pushing over SSH you must push with a key managed by Gitea
error: failed to push some refs
```

**Bypass method (temporarily remove hooks):**
```bash
BARE=/data/gitea/data/git/repositories/manjufkanavi/<repo>.git

# 1. Clone as worktree (not bare) for committing
git clone "$BARE" /tmp/work
cd /tmp/work
git checkout main
# ... add/modify files ...
git add -A
git commit -m "ci: add workflows"

# 2. Temporarily rename the hook, push, restore
mv $BARE/hooks/pre-receive $BARE/hooks/pre-receive.bak
git push origin main  # succeeds without hook
mv $BARE/hooks/pre-receive.bak $BARE/hooks/pre-receive

# 3. Verify
git -C "$BARE" log --oneline -3
```

**Critical: `git update-ref` does NOT transfer objects.** If you create a commit in a worktree clone and run `git -C $BARE update-ref refs/heads/main $NEW_SHA`, the ref pointer moves but the commit object (`$NEW_SHA`) exists only in the worktree — the bare repo returns `cannot update ref ... with nonexistent object`.

**Correct approach:** Either push via the hook-bypass method above, or pack the objects first:
```bash
# In the worktree clone:
git repack -a -d  # packs all objects into the bare repo
git gc
# Then update the ref
git -C "$BARE" update-ref refs/heads/main $(git rev-parse HEAD)
```

### Deploying Workflow Files: Non-Bare Clone + Push Method

When you need to **create new files** (not modify existing ones) in a Gitea bare repo, the most reliable approach:

```bash
BARE=/home/mkanavi/docker/iacgenie/gitea_data/data/git/repositories/manjufkanavi/<repo>.git
TMP=/tmp/gitea-clone

# 1. Clone with --no-checkout to get a working tree pointing at the bare repo
rm -rf "$TMP/<repo>"
git clone --no-checkout "$BARE" "$TMP/<repo>"

# 2. Enter the clone and make changes
cd "$TMP/<repo>"
git checkout main
mkdir -p .github/workflows
cp /path/to/workflow.yml ".github/workflows/workflow.yml"
git add ".github/workflows/workflow.yml"
git commit -m "ci: add workflow.yml" --author="Gitea CI <ci@gitea.iacgenie.com>"

# 3. Force push back to the bare repo (or bypass hooks if needed)
# Option A — hooks work (push via HTTP/SSH URL to running Gitea):
git push origin main --force

# Option B — hooks fail (temporarily disable hooks on bare repo):
rm -rf "$BARE/hooks"
git push origin main --force
# Restore hooks (they'll be regenerated by Gitea on next access)
# Or: git -C "$BARE" update-ref refs/heads/main $(git rev-parse HEAD)
#     && git -C "$BARE" repack -a -d

cd /tmp && rm -rf "$TMP/<repo>"
```

### `git mktree` Pitfall with Nested Paths

**`git mktree` does NOT handle subdirectories with slashes.** Creating a tree entry for `.github/workflows/smoke-test.yml` fails with:

```
fatal: path .github/workflows/smoke-test.yml contains slash
```

**Workaround:** Use `git mktree --missing` flag to allow creation of missing intermediate tree entries:
```bash
# WRONG (no slashes):
echo "100644 blob <sha>	text.txt" | git mktree

# WRONG (has slashes, no --missing):
echo "100644 blob <sha>	.github/workflows/test.yml" | git mktree
# → fatal: path .github/workflows/test.yml contains slash

# CORRECT (--missing flag):
echo "100644 blob <sha>	.github/workflows/test.yml" | git mktree --missing
# → Creates tree with .github/ subtree and workflows/ subtree automatically
```

**Note:** `--missing` only works when there's an existing tree to merge into. For an empty repo, use the non-bare clone method above instead.

### Gitea API `EOF` Error on Repo Endpoints

Some Gitea versions (especially rootless Docker images) return `{"message":"EOF"}` instead of JSON on repo-level API endpoints (`/api/v1/repos/<owner>/<repo>/...`), `/api/v1/repos/<owner>/<repo>/contents/...`, and `/api/v1/repos/<owner>/<repo>/branches/<branch>`:

```json
{"message":"EOF","url":"https://gitea.iacgenie.com/api/swagger"}
```

**Root cause:** The Gitea binary cannot resolve paths inside the container (hooks reference `/usr/local/bin/gitea` which isn't in the git hook PATH). The `contents` API endpoint is particularly affected.

**Workaround:** Use direct `git` commands on the bare repo filesystem, or push through the HTTP API which routes through the running container.

### Gitea Repo Owner Path Mismatch

The Gitea API may report repo owners as `admin` (the logged-in user) while the filesystem stores repos under a different username. Always verify:

```bash
# API says:
curl -s -H "Authorization: token $TOKEN" \
  "https://gitea.iacgenie.com/api/v1/user/repos" | grep name
# → ["admin iacgenie", "admin LightSerp"]

# Filesystem shows:
find /home/mkanavi/docker/iacgenie/gitea_data -name "*.git" -type d
# → .../manjufkanavi/iacgenie.git  ← different owner!
```

**Fix:** Use the filesystem owner name when addressing repos via API or git operations. The correct path is `/api/v1/repos/manjufkanavi/<repo>` (not `/api/v1/repos/admin/<repo>`).

## GitHub ↔ Gitea Bidirectional Sync — Infinite Loop Pattern

Pushing to **both** GitHub and Gitea with push mirrors in **both directions** creates an **infinite commit loop**: GitHub → Gitea mirror triggers a push → Gitea → GitHub mirror pushes back → GitHub triggers again → repeat forever.

### Avoiding the Loop

Three strategies, listed from most recommended to least:

#### Strategy A: Pull mirrors only (GitHub → Gitea) — RECOMMENDED

Set up Gitea as a **pull mirror** of GitHub. Gitea reads from GitHub; nothing pushes back.

- In Gitea repo settings: Source → "Pull mirror" → URL to GitHub
- Set sync interval (e.g., every 5 minutes)
- Gitea runs CI/CD workflows directly (no need for push mirrors)
- **No loop possible** because Gitea is read-only

#### Strategy B: Push mirrors with webhook filtering

Use Gitea's push mirror to GitHub, but configure Gitea to **skip webhook notifications** for commits that came from the mirror itself. This requires:

1. Use a **different SSH deploy key** for Gitea's push mirror to GitHub
2. Configure GitHub to **exclude commits** authored by the deploy key
3. Not fully reliable — depends on author metadata

#### Strategy C: Cron-based sync script

Instead of mirrors, run a sync script on a cron:

1. Fetch from GitHub → push to Gitea (one direction only)
2. OR: sync both directions but **skip the "mirror source" commit**
3. Best with a dedicated sync user account (e.g., `sync-bot`) whose commits are excluded from CI/CD

### Decision Guide

| Scenario | Recommended Strategy |
|---|---|
| Code lives on GitHub, Gitea is a backup | **A** (pull only) |
| Code lives on Gitea, GitHub is a mirror | B or C |
| Both are equally important | **A** + run Gitea Actions directly |
| Gitea workflows need to trigger on GitHub commits | **A** (push to GitHub → pull mirror to Gitea → Gitea Actions) |

## DB Migration Version Mismatch

Upgrading the Gitea Docker image can fail if the DB migration version exceeds what the binary supports:

```
[F] Migration Error: Your database (migration version: 343) is for a newer Gitea,
you can not use the newer database for this old Gitea release (312).
```

### Fix
1. Check current version: `docker exec gitea gitea --version`
2. Pull newer image: `docker compose down gitea && sed -i 's|:1.23.4|:latest|' docker-compose.yml && docker compose pull gitea`
3. Recreate: `docker compose up -d --force-recreate gitea`
4. Verify: `docker logs gitea --tail 10` — should show "PING DATABASE" then listen, NOT "Prepare to run install page"
sudo systemctl stop gitea-runner
rm -f /home/mkanavi/.runner
docker exec iacgenie-gitea gitea actions generate-runner-token
cd /home/mkanavi
~/bin/gitea-runner register --instance https://gitea.iacgenie.com --token <NEW> --no-interactive
sudo systemctl start gitea-runner
journalctl -u gitea-runner --no-pager -n 5
```

## Disable GitHub Actions on Repos

```bash
for repo in iacgenie LightSerp iacgenie-unified-infra; do
  gh api repos/manjufkanavi/"$repo"/actions/permissions \
    --method PUT --input - <<EOF
{"enabled":false}
EOF
done
```

**Critical:** Use `--input -` with JSON body. Using `-f enabled=false` fails with "not a boolean".

## SMTP2GO Email Delivery

### Approach 1: SMTP Auth (requires separate SMTP credentials)

The `SMTP2GO_API_KEY` is for REST API only. SMTP servers need separate credentials from the dashboard.

### Approach 2 (PREFERRED): SMTP2GO REST API — no SMTP credentials needed

SMTP2GO REST API (`https://api.smtp2go.com/v3/email/send`) requires **only the API key**.

```python
import json
from urllib.request import Request, urlopen

payload = {
    "to": ["recipient@example.com"],
    "sender": "verified_sender@domain.com",
    "subject": "Email subject",
    "html_body": "<html>...</html>"
}

data = json.dumps(payload).encode("utf-8")
req = Request(
    "https://api.smtp2go.com/v3/email/send",
    data=data,
    headers={
        "Content-Type": "application/json",
        "X-Smtp2go-Api-Key": os.environ["SMTP2GO_API_KEY"]
    }
)
resp = urlopen(req, timeout=30)
result = json.loads(resp.read().decode("utf-8"))
```

See `references/sync-gitea-standalone.md` for the complete sync script template with REST API email reporting.

## Gitea CI/CD Workflow Structure

Workflows live in `.github/workflows/` (same as GitHub Actions — Gitea Actions uses the identical format).

### Standard workflow pattern

1. `on:` triggers (`push` to main, `pull_request` to main)
2. `runs-on: ubuntu-latest` (uses self-hosted Gitea runner labels)
3. GitHub-compatible actions (`actions/checkout@v4`, etc.)
4. Service-specific lint, test, build, Docker validation steps
5. `continue-on-error: true` for non-critical steps

### Workflow examples per project type

**Infrastructure-only repos:** Validate Docker Compose with `docker compose config --quiet`

**Python projects:** Setup Python 3.11, lint, run pytest, validate Docker Compose

**Node.js/TypeScript:** Setup Node.js 20, `npm ci`, build, run tests, validate Docker Compose

### Committing workflows

```bash
cd <repo>
git add .github/workflows/
git commit -m "ci: add Gitea CI workflow"
git push
```

## Mirrors API Unavailable — Detect Before Setting Up

```bash
curl -s -u "admin:password" \
  "http://127.0.0.1:3000/api/v1/repos/mkanavi/iacgenie/mirrors" | python3 -m json.tool
# If 404 → use cron-based sync (see references/gitea-mirror-workaround.md)
```

## Gitea Rootless `environment-to-ini.go` Pitfall

The rootless Gitea Docker image runs `environment-to-ini.go` on startup which:
1. Reads all `GITEA__section__key` env vars
2. **Overwrites** `/etc/gitea/app.ini` with merged values
3. Writes result → `/etc/gitea/app.ini`

**Critical implication:** Any env var NOT set in the compose file will be reset to defaults on restart — including `INSTALL_LOCK`.

### Symptoms
- `INSTALL_LOCK` set in app.ini to `true` but Gitea still shows installation page after restart
- `GITEA__security__INSTALL_LOCK` not in env vars (`docker exec container env | grep INSTALL` returns nothing)
- Config changes in the bind-mounted app.ini file get silently overwritten

### Diagnosis
```bash
# Check actual env vars in the running container
docker exec <container> env | grep GITEA

# Check what app.ini the container is reading
docker exec <container> cat /etc/gitea/app.ini | grep INSTALL_LOCK
```

### Fix
Add the missing env var to the **Docker Compose file** and force-recreate:
```bash
# In docker-compose.yml, add under environment:
GITEA__security__INSTALL_LOCK: "true"

# Then force-recreate (not just restart):
docker compose -f docker-compose-unified.yml up -d --force-recreate gitea
```

**CRITICAL:** `docker restart` does NOT re-read compose files. You MUST use `up -d --force-recreate` for env var changes to take effect.

### `INSTALL_LOCK = false` pitfall

When `INSTALL_LOCK = false`, Gitea treats itself as uninitialized — admin user does not exist, all requests redirect to `/install`.

**Fix:** Set `INSTALL_LOCK = true` in `[security]` and run `gitea admin user change-password`.

## Config File Locations

| Path | Description |
|------|-------------|
| `/etc/gitea/app.ini` (container) | **The ONLY config file Gitea reads** |
| `/data/gitea/conf/app.ini` (mounted) | NOT read by Gitea |
| `/home/mkanavi/docker/iacgenie/gitea_data/data/` | Gitea data (repos, LFS, indexers) |

## API Base URL

- Via tunnel: `https://gitea.iacgenie.com`
- Direct (VM localhost): `http://127.0.0.1:3000`

## Gitea Bare-Repo Administration

Beyond basic administration, you may need to recover corrupted repos, deploy workflow files, or manipulate bare Git repos inside the Gitea container.

### SSH + Docker Exec Quoting Pitfalls

When combining SSH + heredocs + `docker exec`, you face a triple-quoting minefield. The `<<'EOF'` heredoc inside an SSH single-quoted command **does not work** — the outer quotes eat the inner quotes.

**Fix patterns (see `references/ssh-quoting-pitfalls.md` for details):**
1. **Base64**: `base64 <<'EOF'` locally → `echo '...' | base64 -d > /tmp/script.sh` on VM → `bash /tmp/script.sh`
2. **Individual commands**: Run each step as a separate `ssh` call with simple `docker exec`
3. **Python on VM**: `ssh 'python3 -c "..."'` to write files (avoids shell entirely)
4. **Single-level SSH**: Put script on VM first via `tee` or `scp`, then `ssh host 'bash /tmp/script.sh'`

**Docker exec variable expansion**: `docker exec container sh -c "echo $VAR"` — `$VAR` expands on the **host** shell, not inside the container. Use single quotes: `docker exec container sh -c 'echo $VAR'`.

### Shell Quoting for Special Characters

When passing passwords with `$`, `!`, `@` via shell commands, the `$` gets expanded. Always use single-quoted heredocs (`<<'EOF'`), temp files, or pass via env vars.

### Bare Repo Restoration

When a commit deleted original code and only CI workflows remain:

```bash
# 1. Extract original code tree
docker exec <container> sh -c "git -C <bare-repo> archive <commit-hash> | tar xf - -C /tmp/restore"

# 2. Reset index to original tree
docker exec <container> git -C <bare-repo> read-tree <commit-hash>

# 3. Add missing files and write new commit
# (see references/ssh-quoting-pitfalls.md for full quoting examples)
```

### Repo Paths

Gitea repos are at `/data/gitea/data/git/repositories/<owner>/<repo>.git` (NOT `/data/gitea/git/`). Verify with:
```bash
docker exec <container> find /data/gitea -name "*.git" -type d 2>/dev/null
```

### Pre-Receive Hook Issues

Error: `Rejecting changes as Gitea environment not set`.
**Fix:** Hook runs in `git` user context and can't find `gitea` binary. Bypass with `git push --no-verify` for one-shot pushes, or patch the hook.

## Gitea Hardening Configuration

Security hardening environment variables and configuration patterns for production Gitea deployments.

### Essential Security Variables

All variables go in the Gitea service `environment:` block in docker-compose:

```yaml
# Account security
GITEA__security__INSTALL_LOCK: "true"            # Lock admin UI
GITEA__security__DISABLE_REGISTRATION: "true"     # No public signups
GITEA__service__DISABLE_REGISTRATION: "true"      # Same, service-level
GITEA__service__REGISTER_EMAIL_CONFIRM: "false"   # No email verification needed
GITEA__security__DISABLE_GRAVATAR: "true"         # No external avatar fetch
GITEA__security__ENABLE_CAPTCHA: "true"           # CAPTCHA on login
GITEA__security__MIN_PASSWORD_LENGTH: 12          # Minimum password length
GITEA__security__DEFAULT_ENABLE_2FA: "true"       # Enforce 2FA for all users
GITEA__session__SESSION_LIFETIME: 86400           # 24h session timeout
GITEA__session__COOKIE_SECURE: "true"             # Secure cookies only
```

### Authentication Hardening

- Admin credentials must come from env vars, NOT hardcoded:
  - `GITEA__admin__INIT_ROOT_USER_NAME: "${GITEA_ADMIN_USERNAME:-admin}"`
  - `GITEA__admin__INIT_ROOT_USER_PASSWORD: "${GITEA_ADMIN_PASSWORD}"`
- The `${GITEA_ADMIN_PASSWORD}` value must be present in the `.env` file

### SMTP Configuration

```yaml
GITEA__mailer__ENABLED: "true"
GITEA__mailer__SMTP_ADDR: "mail.smtp2go.com"
GITEA__mailer__SMTP_PORT: "2525"
GITEA__mailer__USER: "${SMTP_USER}"
GITEA__mailer__PASSWD: "${SMTP_PASS}"
GITEA__mailer__FROM: "noreply@iacgenie.com"
```

### Ansible Role Defaults

Map hardening settings to Ansible role defaults:
```yaml
gitea_2fa_enforce: true
gitea_disable_registration: true
gitea_enable_notify_mail: true
gitea_min_password_length: 12
gitea_rate_limit_window: 15m
gitea_rate_limit_high: 200
gitea_rate_limit_low: 50
```

### Security Headers (Nginx Proxy)

Add these HTTP headers in the nginx proxy for Gitea:
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; font-src 'self' https://cdn.jsdelivr.net; frame-ancestors 'none';`
- `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`
- `X-Permitted-Cross-Domain-Policies: none`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`

## Dependencies

### References
- `references/gitea-state-assessment.md` — Complete diagnostic workflow, state matrix, and session context for diagnosing "installed but empty" Gitea state
- `references/cloudflared-cert-pem-issue.md` — Cloudflare tunnel cert.pem missing error: cause, fix, and legacy migration
- `references/gitea-1-23-apis.md` — Gitea 1.23 API quirks
- `references/gitea-actions-setup.md` — Actions feature setup
- `references/push-mirror-database.md` — Push mirror DB schema
- `references/gitea-mirror-workaround.md` — Gitea 1.23.x mirrors API 404 — verified DB schema (mirror table), is_mirror flag requirement, SQL steps, pitfall list
- `references/gitea-mirror-sync-template.md` — GitHub→Gitea pull mirror sync script, cron setup, and macOS `env -i` workaround
- `references/sync-gitea-standalone.md` — SMTP2GO REST API email reporting patterns
- `references/gitea-ci-cd-workflows.md` — Gitea Actions workflow structure
- `references/gitea-actions-workflows.md` — CI/CD workflow templates for Python, TypeScript, Docker builds
- `references/gitea-1-27-runner-auth-debug.md` — Gitea 1.27 runner gRPC auth schema, debugging path when `unregistered runner` error persists
- `references/gitea-runner-registration.md` — Full runner registration workflow (token generation, register, verify)
- `references/gitea-openbao-credential-pattern.md` — Python+SCP pattern for storing Gitea credentials in OpenBao; handles `$`-containing passwords through multi-level SSH quoting
- `references/gitea-workflow-templates-2026-08-01.md` — Workflow files created for Phase 3 CI/CD (iacgenie, lightserp, unified-infra repos)
- `references/gitea-non-bare-clone-deploy.md` — Complete non-bare clone + push pattern with pitfall inventory for deploying files to Gitea bare repos (replaces API approach when contents API returns EOF/403)

### Scripts
- `scripts/gitea-state-assessment.sh` — One-command Gitea health check (container status, user count, DB stats, Actions enabled, runner status, recent errors)
- `scripts/verify-gitea-mirrors.sh` — Verify Gitea pull mirrors: DB entries, sync trigger, bare repo content
- `scripts/sync-gitea-with-email.py` — cron-compatible GitHub→Gitea sync with HTML email reports (legacy SMTP)
- `scripts/extract-env-var.py` — safely extract Docker Compose `***` protected variables
- `scripts/gitea-reset-admin-password.py` — batch admin password reset
