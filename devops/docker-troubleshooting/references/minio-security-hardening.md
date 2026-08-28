# MinIO Security Hardening

## Container Security Profile

### Complete Hardening Template

```yaml
minio:
  image: minio/minio:RELEASE.2025-09-07T16-13-09Z  # Pin to available tag
  container_name: iacgenie_minio
  restart: always
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: "${MINIO_ROOT_USER}"
    MINIO_ROOT_PASSWORD: "${MINIO_ROOT_PASSWORD}"
    MINIO_PROMETHEUS_AUTH_TYPE: "public"
  volumes:
    - /path/to/minio/data:/data
  ports:
    - "127.0.0.1:9000:9000"   # API
    - "127.0.0.1:9001:9001"   # Console
  networks:
    - iacgenie-backend
  healthcheck:
    test: ["CMD-SHELL", "mc ready local && curl -f http://127.0.0.1:9000/minio/health/live || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
  deploy:
    resources:
      limits:
        memory: "4g"
        cpus: "2.0"
  cap_drop:
    - ALL
  cap_add:
    - CHOWN        # File ownership in mounted volumes
    - DAC_OVERRIDE # Bypass file permission checks
    - FOWNER       # Own files in mounted volumes
    - SETGID       # Set group ID
    - SETUID       # Set user ID
    - NET_BIND_SERVICE
  security_opt:
    - no-new-privileges:true
  read_only: true
  tmpfs:
    - /tmp
  logging:
    driver: json-file
    options:
      max-size: "100m"
      max-file: "3"
```

### Capability Breakdown

| Capability | Why MinIO Needs It |
|------------|-------------------|
| CHOWN | Set ownership on files in mounted /data volume |
| DAC_OVERRIDE | Bypass file permission checks for data directory |
| FOWNER | Own files created in the mounted volume |
| SETGID | Set group ID for file operations |
| SETUID | Set user ID for service operation |
| NET_BIND_SERVICE | Bind to network interfaces |

### Why `read_only: true` + `tmpfs: /tmp`?

MinIO writes temporary files to `/tmp` during operations (encryption, erasure code). Without a tmpfs mount, `read_only: true` would cause crashes. The `/data` volume mount overrides read-only for the actual data directory.

## Image Tag Management

**CRITICAL:** MinIO RELEASE tags expire and are removed from Docker Hub. Always check available tags before pinning:

```bash
curl -s https://hub.docker.com/v2/repositories/minio/minio/tags?page_size=20 | \
  python3 -m json.tool | grep '"name": "RELEASE' | head -5
```

Current available tags (as of 2025-09): `RELEASE.2025-09-07T16-13-09Z`, `RELEASE.2025-07-23T15-54-02Z`
Older tags like `RELEASE.2025-06-13T05-20-52Z` are removed and will cause `manifest unknown` errors.

## Nginx Reverse Proxy Pattern

### HTTP Redirect Blocks

```nginx
server {
    listen 80;
    server_name minio.iacgenie.com;
    return 301 https://$host$request_uri;
}

server {
    listen 80;
    server_name console.minio.iacgenie.com;
    return 301 https://$host$request_uri;
}
```

### HTTPS API Block

```nginx
server {
    listen 443 ssl http2;
    server_name minio.iacgenie.com;

    ssl_certificate /etc/letsencrypt/live/iacgenie.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/iacgenie.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'none';" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;

    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_redirect off;
        proxy_hide_header X-Powered-By;
    }
}
```

### HTTPS Console Block (with Basic Auth)

```nginx
server {
    listen 443 ssl http2;
    server_name console.minio.iacgenie.com;

    # Same SSL config as API block...

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'none';" always;

    auth_basic "MinIO Console Admin";
    auth_basic_user_file /etc/nginx/.htpasswd_minio;

    location / {
        proxy_pass http://127.0.0.1:9001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_redirect off;
        proxy_hide_header X-Powered-By;
    }
}
```

## Common Pitfalls

### Orphan `minio-console` Service

**Anti-pattern:** Running a separate nginx container (`minio-console`) to proxy the MinIO console.

**Fix:** Use the main Nginx reverse proxy. The separate container adds unnecessary complexity and breaks the centralized TLS termination pattern used by all other services.

### `LIGHTSERP_ALLOW_INSECURE: "true"`

When MinIO runs over HTTP, dependent services must set `ALLOW_INSECURE=true`. After TLS is configured, this must be set to `false` and the endpoint changed to `https://`.

### Credential Conflicts

Multiple `.env` files with different MinIO credentials (`.env`, `infra.env`, `.env.minio`) cause authentication failures. Always use a single Ansible-managed `.env` file with templated credentials.

### Healthcheck Only Checks `mc ready`

The basic healthcheck `mc ready local` only checks if MinIO is ready to accept connections, not if the S3 API is functional. Add `curl -f http://127.0.0.1:9000/minio/health/live` for a more thorough check.

## Security Audit Checklist

1. [ ] Image pinned to specific RELEASE tag (not `latest`)
2. [ ] `cap_drop: ALL` with minimal `cap_add`
3. [ ] `no-new-privileges:true` security option
4. [ ] `read_only: true` filesystem with tmpfs for writable dirs
5. [ ] CPU limits set (`cpus: "2.0"`)
6. [ ] Prometheus metrics enabled (`MINIO_PROMETHEUS_AUTH_TYPE: public`)
7. [ ] Nginx reverse proxy with TLS termination
8. [ ] Security headers (HSTS, CSP, X-Frame-Options, etc.)
9. [ ] Rate limiting configured
10. [ ] Console protected with basic auth
11. [ ] Single source of truth for credentials
12. [ ] `LIGHTSERP_ALLOW_INSECURE` set to `false` after TLS
