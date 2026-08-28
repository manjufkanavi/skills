# SearXNG Settings.yml Deployment Pattern

## The Problem

SearXNG reads configuration from `settings.yml` at `/etc/searxng/settings.yml` inside the container. If only a partial settings file is deployed (e.g., just `secret_key` + `image_proxy`), proxy configuration, pool settings, and engine configuration will be missing — leading to rate-limiting failures (e.g., Brave 403 errors).

## Correct Template Structure (`settings.yml.j2`)

The template should include ALL configuration sections:
1. **General**: `secret_key`, `instance_name`, `default_lang`
2. **Server**: `bind_address`, `bind_port`, `methods` (GET/POST)
3. **Engines**: Disable rate-limited engines (Brave), configure remaining ones
4. **Proxy/Oxylabs**: Proxy URLs, pool settings, authentication
5. **UI**: Theme, pagination, locale settings

## Deployment Task (Ansible)

In `roles/searxng/tasks/main.yml`:
```yaml
- name: Deploy SearXNG settings.yml
  template:
    src: settings.yml.j2
    dest: "{{ searxng_data_dir }}/settings.yml"
    mode: '0644'
  notify: restart searxng
```

The volume mount in compose template:
```yaml
volumes:
  - {{ searxng_data_dir }}/settings.yml:/etc/searxng/settings.yml:ro
```

## Common Pitfalls

### 1. Partial Settings File
If `settings.yml` only has `secret_key`, all other config falls back to SearXNG defaults. This means:
- No proxy routing (Brave, Bing, etc. hit directly → rate-limited)
- Default engines may not include your preferred search sources
- No pool settings for proxy rotation

### 2. Engine Rate Limiting
Brave search is particularly aggressive with rate limiting. Always disable it:
```yaml
engines:
  - name: brave
    disabled: true
```

### 3. Secret Key Not Rotated
The `secret_key` must be a long random string. Use Ansible vault or environment variables:
```yaml
secret_key: "{{ searxng_secret_key | default('CHANGE_ME_IN_VAULT') }}"
```

### 4. Settings File Permissions
The file must be readable by the SearXNG container user (usually `www-data` or root). Set mode `0644`.

## Verification

After deployment:
1. Check file is present in container: `docker exec iacgenie_searxng cat /etc/searxng/settings.yml | head -20`
2. Test search: `curl -s 'http://127.0.0.1:8082/search?q=test&format=json' | head -5`
3. Check logs for engine errors: `docker logs iacgenie_searxng | grep -i "rate\|too many"`
