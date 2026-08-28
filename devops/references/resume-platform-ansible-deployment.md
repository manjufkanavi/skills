# Resume Platform — Ansible Deployment Guide

**Date:** 2026-08-26
**Product:** resume.iacgenie.com
**Pattern:** Ansible role → VM deployment → docker compose up

## Ansible Role Structure

The resume-platform is managed by the `resume-platform` Ansible role at:
```
ansible/playbooks/roles/resume-platform/
├── tasks/main.yml          # MinIO bucket, PostgreSQL tables, Keycloak client, Ollama model
├── templates/              # Nginx vHost template (if needed)
└── files/                  # Static files to copy to VM
```

### Role Tasks

The role handles **initialization** only (not container lifecycle — that's docker-compose-generator):

1. **MinIO bucket** — `mc mb iacgenie/resume-files --ignore-existing`
2. **PostgreSQL tables** — `users` and `resumes` tables in the `lightsrp` database
3. **Keycloak client** — Creates `resume-platform` OIDC client via admin API
4. **Ollama model** — `ollama pull qwen2.5:0.5b`

### Container Lifecycle

Containers are managed by `docker-compose-generator` role which renders:
- `ansible/playbooks/roles/docker-compose-generator/templates/docker-compose.yml.j2`
- Already includes `resume-api` and `n8n` services

### Nginx vHost

The vHost is rendered by `nginx-container` role:
- Template: `ansible/playbooks/roles/nginx-container/templates/nginx-unified.conf.j2`
- Added `resume.iacgenie.com` server block (HTTPS only, HTTP handled by catch-all)
- Proxies: `/api/v1/auth/` → `:3006`, `/api/v1/internal/` → `:3006`, `/api/v1/` → `:9096` (auth-wrapper), `/` → `:3006`

### Cloudflare Tunnel

Ingress rule added to `docker-compose/docker/cloudflared/config.yml`:
```yaml
- hostname: "resume.iacgenie.com"
  service: http://127.0.0.1:80
```

### Secrets

Added to `ansible/templates/env.j2`:
- `RESUME_PLATFORM_CLIENT_SECRET` — Keycloak client secret
- `RESUME_API_SECRET` — Internal API key for n8n callbacks

## Deployment Order

```
1. docker-compose-generator (renders docker-compose.yml with resume-api + n8n)
2. nginx-container (renders nginx config with resume.iacgenie.com vHost)
3. resume-platform (initializes MinIO bucket, PostgreSQL tables, Keycloak client, Ollama model)
```

## deploy.sh Path Fix (2026-08-26)

**Bug:** `deploy.sh` referenced `playbook.yml` and `inventory/hosts.yml` — both wrong.
**Fix:** Changed to `playbooks/site.yml` and `inventory/hosts.ini`.

```bash
# WRONG (old)
PLAYBOOK="$ANSIBLE_DIR/playbook.yml"
INVENTORY="$ANSIBLE_DIR/inventory/hosts.yml"

# CORRECT (current)
PLAYBOOK="$ANSIBLE_DIR/playbooks/site.yml"
INVENTORY="$ANSIBLE_DIR/inventory/hosts.ini"
```

## Manual Deployment (if Ansible fails)

When `ansible-playbook` times out or fails, deploy manually:

```bash
# 1. Copy API code
scp -r /path/to/resume-platform/api/* mkanavi@192.168.0.118:/home/mkanavi/docker/iacgenie/resume-platform/

# 2. Create MinIO bucket
ssh mkanavi@192.168.0.118 "docker exec iacgenie_minio mc mb iacgenie/resume-files --ignore-existing"

# 3. Create PostgreSQL tables
ssh mkanavi@192.168.0.118 "docker exec iacgenie_postgres psql -U lightsrp -d lightsrp -c '
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY, keycloak_id VARCHAR(255) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL, name VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS resumes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  filename VARCHAR(500) NOT NULL, file_type VARCHAR(50) NOT NULL,
  file_size INTEGER NOT NULL DEFAULT 0, minio_key VARCHAR(500) NOT NULL,
  ocr_json JSONB DEFAULT \\'{}\\', ats_score_json JSONB DEFAULT \\'{}\\',
  improvements_json JSONB DEFAULT \\'{}\\', status VARCHAR(20) DEFAULT \\'pending\\',
  job_title VARCHAR(255), experience_years INTEGER, error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_status ON resumes(status);
'"

# 4. Pull Ollama model
ssh mkanavi@192.168.0.118 "docker exec ollama ollama pull qwen2.5:0.5b"

# 5. Restart services
ssh mkanavi@192.168.0.118 "cd /home/mkanavi/docker/iacgenie && docker compose up -d --build resume-api n8n"

# 6. Reload nginx
ssh mkanavi@192.168.0.118 "docker exec iacgenie-nginx nginx -t && docker exec iacgenie-nginx nginx -s reload"
```

## Key Integration Points

| Component | Config Location | Port |
|-----------|----------------|------|
| Resume API | docker-compose.yml.j2 | 127.0.0.1:3006 |
| n8n | docker-compose.yml.j2 | 127.0.0.1:3005 |
| Nginx vHost | nginx-unified.conf.j2 | 443 ssl |
| Cloudflare | cloudflared/config.yml | ingress rule |
| Keycloak | keycloak.conf (comments) | admin API |
| Auth Wrapper | docker-compose.yml.j2 | SERVICE_BACKENDS |
| Secrets | env.j2 | RESUME_PLATFORM_CLIENT_SECRET, RESUME_API_SECRET |
