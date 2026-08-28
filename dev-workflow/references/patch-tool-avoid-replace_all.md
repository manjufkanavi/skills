# Patch Tool Pitfall: replace_all=True Cross-Matching

## The Problem

When using `patch` (mode=replace) with `replace_all=True`, the old_string pattern can match across **unrelated template blocks** that share common boilerplate text. This causes unintended replacements in blocks that should NOT be changed.

**Symptom:** After applying a `replace_all=True` patch, other server blocks or template sections that weren't targeted are silently modified with the new content, often corrupting the file structure.

## Root Cause

Many nginx/cloudflare config templates contain duplicate or near-duplicate sections (e.g., HTTP and HTTPS versions of the same vHost). If the replacement pattern matches common boilerplate (security headers, proxy_set_header blocks, etc.), the patch tool will replace ALL occurrences — not just the intended ones.

### Example (from IacGenie v4.0)

The nginx template had `platform.iacgenie.com` sections in BOTH HTTP (port 80) and HTTPS (port 443). Both blocks shared identical boilerplate. Using `replace_all=True` with a pattern like `"connect-src 'self' api.iacgenie.com"` → `"connect-src 'self' http://127.0.0.1:3003"` replaced BOTH blocks, including ones that were for different services (app.iacgenie.com) that got merged due to the shared boilerplate.

## Prevention — Use Unique Context

**ALWAYS use enough surrounding context to make the old_string uniquely match ONE block.** Include at minimum:

1. **The preceding section's closing brace** (`}`) to anchor the boundary
2. **A unique preceding line** (e.g., `# PageZen (page) — root handler: redirect to main app`)
3. **Service-specific identifiers** (server_name, listen directives, unique comments)

**Wrong (will match all):**
```
old_string: "    add_header Content-Security-Policy \"default-src 'self'...connect-src 'self' api.iacgenie.com...\""
```

**Correct (uniquely matches one block):**
```
old_string: |
    # All other paths: proxy to PageZn
    location / {
        proxy_pass http://127.0.0.1:8081;
        ...
    }
}

# IacGenie Platform (platform)
server {
    listen 443 ssl http2;
    server_name platform.iacgenie.com;
    ...
    add_header Content-Security-Policy "...connect-src 'self' api.iacgenie.com...";
    ...
}

# Vault/OpenBao (vault)
```

## Recovery from Accidental replace_all

1. **Re-read the full file** to understand the damage
2. **Use targeted single-match patches** (no replace_all) to fix each section individually
3. **Verify the file structure** by listing all `server_name` directives to ensure no blocks were merged or deleted
4. **Git reset if needed:** `git checkout -- <file>` to start over

## General Rule

> **Never use `replace_all=True` on template files with duplicate block structures.** Always provide unique context that distinguishes the target block from its near-duplicates. If you need to fix multiple blocks, make separate patches with unique context for each.

## Real-World Consequences (2026-08-16)

`replace_all=True` has been observed corrupting both nginx config templates AND docker-compose.yml.j2 templates:

| File | What broke | Cause |
|------|-----------|-------|
| `nginx-unified.conf.j2` | CSP headers merged across server blocks | Shared `add_header` boilerplate |
| `docker-compose.yml.j2` | Duplicate `# Cloudflare Tunnel` section, removed `/etc/nginx/conf.d` volume mount | Shared `# =====================` section markers |
| `docker-compose.yml.j2` | `auth_wrapper` deploy block replaced with logging block | Shared `deploy/resources` boilerplate |

**Lesson:** The `patch` tool's `replace_all=True` operates on raw text matching, not semantic blocks. Any two blocks sharing the same text pattern will be affected.