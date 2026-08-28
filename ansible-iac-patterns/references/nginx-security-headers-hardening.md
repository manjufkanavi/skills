# Nginx Security Headers Hardening

## When to Use

After setting up Nginx reverse proxy for Docker services, harden all HTTPS vHosts with security headers. This is a Phase 10.2 Security Hardening task.

## Required Headers (Per vHost)

### Essential Headers (All vHosts)
```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### API vHosts Only
```nginx
add_header Content-Security-Policy "default-src 'none';" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
add_header Access-Control-Allow-Origin '$http_origin' always;
add_header Access-Control-Allow-Methods 'GET, POST, PUT, DELETE, PATCH' always;
add_header Access-Control-Allow-Headers 'Authorization, Content-Type, X-Api-Key' always;
add_header Access-Control-Allow-Credentials 'true' always;
```

### Web Application vHosts
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' <api-domain>; frame-ancestors 'none';" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
```

### Cross-Origin Policy Headers (All vHosts)
```nginx
add_header X-Permitted-Cross-Domain-Policies "none" always;
add_header Cross-Origin-Embedder-Policy "require-corp" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header Cross-Origin-Resource-Policy "same-origin" always;
```

## CORS Preflight Pattern (API vHosts Only)
```nginx
if ($request_method = 'OPTIONS') {
    add_header 'Access-Control-Allow-Origin' '$http_origin' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, X-Api-Key' always;
    add_header 'Access-Control-Max-Age' 86400 always;
    add_header 'Content-Length' 0 always;
    add_header 'Content-Type' 'text/plain' always;
    return 204;
}
if ($request_method ~* '(GET|POST|PUT|DELETE|PATCH)') {
    add_header 'Access-Control-Allow-Origin' '$http_origin' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH' always;
    add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, X-Api-Key' always;
    add_header 'Access-Control-Allow-Credentials' 'true' always;
}
```

## Pitfalls

- **Always use `always` keyword** — without it, headers are not added to error responses (4xx/5xx). This defeats CSP protection on error pages.
- **CSP `script-src 'unsafe-inline'` is a compromise** — it allows inline `<script>` tags which defeats XSS protection. Prefer `nonce-` or `hash-` directives for known scripts. Acceptable for self-hosted apps where you control the source.
- **CORS `Access-Control-Allow-Credentials: true` requires specific origins** — never use `*` as the origin when credentials are enabled. Browsers will reject the response.
- **If using `$http_origin`, validate it** — in production, restrict to known origins: `map $http_origin $allowed_origin { ... }`. Using `$http_origin` directly echoes back any Origin header.
- **HSTS preload requires `includeSubDomains; preload`** — once submitted to the HSTS preload list (chromium.org/hsts), it cannot be easily removed. Verify at https://hstspreload.org/

## Source

Phase 10.2 Security Hardening P1 — ansible-iac-patterns project. Template: `roles/nginx/templates/reverse-proxy.conf.j2`.
