# OpenWebUI Admin Authentication Triage

**Session:** 2026-08-11

## Problem

OpenWebUI admin login at `http://192.168.0.118:4000` was failing with `Internal Server Error` for `admin@iacgenie.com`.

## Root Cause

Three separate DB issues in `/home/mkanavi/open-webui/webui.db`:

### 1. NULL Timestamps (Pydantic Validation Failure)

The `user` table had `NULL` for `last_active_at`, `updated_at`, `created_at`. OpenWebUI's Pydantic models expect integers, not `None`.

**Symptom:** `ValidationError` on login — the admin endpoint tries to return a `UserModel` with `None` timestamp fields.

**Fix:**
```bash
sqlite3 /home/mkanavi/open-webui/webui.db "UPDATE user SET last_active_at=1754900000, updated_at=1754900000, created_at=1754900000 WHERE email='admin@iacgenie.com';"
```

### 2. Plaintext Password in Auth Table

The `auth` table stored `Admin123` as plaintext instead of a bcrypt hash.

**How to generate a hash (run INSIDE the container):**
```bash
docker exec open-webui python3 -c "import bcrypt; print(bcrypt.hashpw(b'Admin123', bcrypt.gensalt()).decode())"
```

Then update the auth table with the returned hash.

### 3. ID Mismatch Between user and auth Tables

The `user` table ID was `admin-id` but the `auth` table ID was `admin-auth-id`. These must match.

**Fix:**
```bash
sqlite3 /home/mkanavi/open-webui/webui.db "UPDATE auth SET id='admin-id' WHERE email='admin@iacgenie.com';"
```

### 4. Read-Only Database

The DB file was owned by root.

**Fix:**
```bash
sudo sqlite3 /home/mkanavi/open-webui/webui.db "..."
# Or: sudo chmod 666 /home/mkanavi/open-webui/webui.db
```

## DB Schema Reference

### user table (relevant columns):
```
id          VARCHAR (PK)
email       VARCHAR
name        VARCHAR
role        VARCHAR (admin/user/pending)
avatar      TEXT
is_active   BOOLEAN
last_active_at INTEGER (timestamp)
updated_at   INTEGER (timestamp)
created_at   INTEGER (timestamp)
```

### auth table (relevant columns):
```
id          VARCHAR (FK to user.id — MUST MATCH)
email       VARCHAR
password    TEXT (bcrypt hash, NOT plaintext)
active      BOOLEAN
```

### config table (for base_urls issues):
```
key         VARCHAR
value       TEXT (often stores JSON)
timestamp   INTEGER
```

## Ollama Base URL Fix

**Problem:** `ollama.base_urls` was `[http://ollama:11434]` (missing inner quotes). JSON parser failed with `Expecting value: line 1 column 2`.

**Correct value:** `["http://ollama:11434"]`

**Fix (Python script avoids shell escaping):**
```python
import sqlite3, os
os.chmod("/path/to/webui.db", 0o666)
conn = sqlite3.connect("/path/to/webui.db")
conn.execute("UPDATE config SET value='[\"http://ollama:11434\"]' WHERE key='ollama.base_urls'")
conn.commit()
conn.close()
```
Then `docker restart open-webui`.

## Verification

```bash
curl -s -X POST http://localhost:4000/api/v1/auths/signin \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@iacgenie.com","password":"Admin123"}' | head -c 200
```

Should return a `token` field.

## Lessons

1. Always check the DB first before troubleshooting auth in containerized apps
2. `sqlite3` on host requires same permissions as container user
3. Bcrypt hash generation must happen inside the container
4. Config JSON values must be valid JSON — missing inner quotes silently corrupt the config
