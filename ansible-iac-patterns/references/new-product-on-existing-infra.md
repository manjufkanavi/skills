# New Product on Existing Infra - Case Study: resume-platform

**Session:** 2026-08-26. Integrated the resume-platform (FastAPI api/ + Next.js webui/) onto the already-running shared iacgenie stack (Keycloak, Postgres, Redis, MinIO, n8n, Cloudflare tunnel, host-level nginx). The API was deployed and healthy but never actually integrated with backend services - auth silently failed. This file is the post-mortem and reuse recipe.

## Live-state discovery checklist (run before touching anything)
1. SSH in and run `docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"` - see what is genuinely running.
2. Confirm which shared services are healthy (Keycloak, Postgres, MinIO, n8n) and reuse them instead of standing up new ones.
3. Check nginx vHosts: `grep -rl "<new-domain>" /etc/nginx/`. A missing match means the product is not reachable yet (no vHost).
4. Check the tunnel: `docker ps | grep cloudflared`, then confirm the new domain is registered on the tunnel.
5. Read the product own docker-compose.*.yml and its nginx/*.conf template - they often already describe the intended routing; the gap is usually only provisioning.

## What was actually found (resume-platform)
- iacgenie_resume_api was already up and healthy on 127.0.0.1:3006. Its code already imported Keycloak config (KEYCLOAK_URL, KEYCLOAK_REALM=iacgenie, KEYCLOAK_CLIENT_ID=resume-platform) and token validation lives in api/services/auth.py.
- Keycloak 26 (--import-realm) ran the iacgenie realm, but the realm only OIDC client was iacgenie-app (redirects to localhost:5173). No resume-platform client existed, so any OIDC flow fails. Fix: create the client.
- There was no resume.iacgenie.com nginx vHost and it was not on the Cloudflare tunnel.

## Debugging insight: auth-wrapper internal-vs-host port mismatch
- The API validated tokens by calling AUTH_WRAPPER_URL (default http://auth-wrapper:9096/validate). The Go auth-wrapper (shared-auth-wrapper) listens internally on 9090, but the compose mapped 127.0.0.1:9096:9096. Nothing bound container :9096, so the container was marked unhealthy and every API call to :9096 failed.
- General lesson: when a service is unhealthy and its callers fail, compare the internal listener port (what the app binds and what the healthcheck tests) against the compose host:container mapping. A mapping that points at a port the app never binds is a silent failure. Align them (for example 9096:9090) or point the caller at the real internal port.
- Escape hatch that avoids the wrapper entirely: the resume API has a Keycloak introspection fallback (_validate_via_keycloak in services/auth.py). Enable it by setting KEYCLOAK_URL, KEYCLOAK_CLIENT_SECRET, and KEYCLOAK_CLIENT_ID=resume-platform. The introspection code already exists - just configure it.

## Recommended integration order (lowest risk)
1. List existing Keycloak clients first (GET /realms/<realm>/admin/clients) before provisioning - never assume the client exists.
2. Create the resume-platform OIDC client (public + PKCE, or confidential), set redirect URIs/web origins to https://<domain>/*, enable email verification.
3. Point the API at Keycloak introspection directly (drop the broken auth-wrapper dependency).
4. Configure email verification: Keycloak built-in SMTP, or reuse iacgenie SMTP2GO service if email-based signup is required.
5. Add the nginx vHost for the new domain and register it on the Cloudflare tunnel.

## Reusable building blocks from iacgenie-platform
If a new product needs real email-based signup (not just Keycloak redirect), copy from platform/backend/:
- routers/auth.py - signup/login/reset/verify-otp unified router (Keycloak + PostgreSQL, bcrypt).
- services/email_service.py and services/smtp2go_email_service.py - email delivery.
- middleware/rate_limiting.py - per-endpoint rate limits for auth endpoints.

## Container-based infra pattern (nginx + cloudflared as containers, disable systemd)
Instead of running nginx and cloudflared as systemd services, run them as Docker containers and disable the systemd units:
- Add `use_container_based_infra: true` to the `nginx` and `cloudflare_tunnel` role **defaults**.
- The roles then run `systemd: {state: stopped, enabled: false}` for nginx/cloudflared and skip their systemd enable tasks (guarded by `when: not use_container_based_infra`).
- Container runtime: `iacgenie-nginx` (nginx:1.27-alpine, `network_mode: host`) mounts `/home/mkanavi/docker/iacgenie/nginx/conf.d` -> `/etc/nginx/conf.d`; `iacgenie-cloudflared` runs the tunnel.
- A dedicated `resume-platform` ansible role generates the `resume.iacgenie.com` vHost into `nginx/conf.d/resume-platform.conf` (template `templates/resume-platform.conf.j2`), wired into `playbooks/services.yml` after `docker-compose-generator`.
- Validate locally with `ansible-playbook --syntax-check`, then render the vHost template with the role defaults to confirm valid nginx config before touching the VM.

## Vault-key blocker (deployment workaround)
`inventory/group_vars/all.yml` may be AES256-encrypted; if the real `.vault_key` is unavailable, the full ansible playbook cannot decrypt secrets and a `--check`/run fails with "Decryption failed (no vault secrets)". Workaround: the real secrets usually already exist on the target as per-service `.env` files (`.env`, `.env.keycloak`, etc.). Recover the vault key if possible; otherwise apply the product-specific changes directly to the VM (compose + nginx conf + Keycloak client) while treating the ansible repo as the "desired state" to be reproduced once the key is recovered. Do NOT record the missing-key failure as a durable rule — record the workaround technique instead.
