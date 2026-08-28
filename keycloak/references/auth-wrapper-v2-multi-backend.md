# Auth Wrapper v2 — Multi-Backend OIDC Gateway

Session: 2026-08-11 — Unified auth gateway for clamav, crowdsec, pagegen, searxng.

## Files

### `infra/shared-auth-wrapper/auth_wrapper2/app.js`
Express.js OIDC gateway with multi-backend routing. Key features:
- `DOMAIN_BACKEND_MAP` — maps subdomain to backend name
- `SERVICE_BACKENDS` env var — comma-separated `name:port` pairs
- `getBackendPort(req)` — resolves backend port from Host header
- `/login` → OIDC auth flow with crypto.randomBytes state
- `/callback` → token exchange, sets `access_token` cookie
- `/dashboard` → user info card with roles, logout link
- `/health` → JSON `{status:"ok"}`
- `/proxied` → authenticated proxy to backend with X-User-Name, X-User-Email, X-User-Roles headers

### `infra/shared-auth-wrapper/auth_wrapper2/Dockerfile`
Node 18 Alpine, builds deps then copies app. Exposes port 9090. CMD `node app.js`.

### `infra/shared-auth-wrapper/auth_wrapper2/package.json`
Dependencies: express, express-session, jsonwebtoken, node-fetch.

## Deployment Pattern

### Docker Compose (backend services)
```yaml
clamav-backend:
  image: rguziy/clamav-web-client:latest
  ports: ["127.0.0.1:9092:8080"]

crowdsec-backend:
  image: crowdsecurity/crowdsec:latest
  volumes: [crowdsec_data:/var/lib/crowdsec/data]
  ports: ["127.0.0.1:3033:8080"]

pagegen-backend:
  image: lightserp-pagezen:latest
  ports: ["127.0.0.1:3032:8082"]

searxng-backend:
  image: searxng/searxng:latest
  ports: ["127.0.0.1:8084:8080"]

auth-wrapper:
  image: iacgenie/auth-wrapper:latest
  ports: ["127.0.0.1:9090:9090"]
  environment:
    SERVICE_BACKENDS: "clamav:9092,pagegen:3032,crowdsec:3033,searxng:8084,default:9090"
    KEYCLOAK_URL: "https://auth.iacgenie.com"
    KEYCLOAK_CLIENT_ID: "auth-wrapper"
```

### Nginx
All 4 subdomains proxy to `127.0.0.1:9090` (auth-wrapper). The wrapper uses `X-Forwarded-Host` to route to the correct backend.

## Keycloak Client
- Client ID: `auth-wrapper`
- Client Secret: set in `client_attributes` table
- Direct Access Grants: enabled
- Redirect URIs: exact URIs per subdomain (wildcards NOT supported in KC 26)
- Standard Flow: enabled

## Troubleshooting

### Port "already allocated" after `docker rm -f`
Use `sudo fuser -k 9090/tcp` then `sleep 5` before `docker run`.

### Client has no client_secret in DB
```sql
INSERT INTO client_attributes (client_id, name, value)
SELECT c.id, 'client.secret', 'YOUR_SECRET'
FROM client c WHERE c.client_id = 'auth-wrapper'
AND NOT EXISTS (SELECT 1 FROM client_attributes ca
  WHERE ca.client_id = c.id AND ca.name = 'client.secret');
```

### ClamAV not responding on HTTP
The raw `clamav/clamav:latest` image uses a native protocol (not HTTP). Use `rguziy/clamav-web-client:latest` for the web interface, and map port 8080 (not 80).

### CrowdSec needs volume
Requires `/var/lib/crowdsec/data` volume or `CROWDSEC_BYPASS_DB_VOLUME_CHECK=true`.