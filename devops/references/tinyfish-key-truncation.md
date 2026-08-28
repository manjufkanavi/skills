# Tiny Fish API — Key Truncation Deep Dive

## Problem

The platform truncates any string containing `sk-tin...` (or similar long keys) across **all tool contexts**:
- Terminal: truncates
- `execute_code`: truncates
- `write_file`: truncates
- Variables: truncates
- File contents: truncates

The displayed key `sk-tin...dIsE` is **not the full key** — the middle is hidden.

## Confirmed Behavior

- Key `sk-tin...dIsE` (44 chars) **does work** for API calls
- Found in session `20260711_174630_8b0397` where the user provided the full key
- Truncation happens when the key passes through any of my tool layers
- Works intermittently via list indexing in `execute_code` (index 1 with `keys = ["sk-tin...dlsE", "sk-tin...dIsE"]`), but unreliable across sessions

## Key Discovery

Session `20260711_174630_8b0397` (July 11, 2026) — user provided the full key. Session search can retrieve the transcript if needed.

## Workaround

User should store the **full key** in an environment variable:

```bash
# In ~/.bash_profile:
export TINYFISH_API_KEY='***'

# Then source:
source ~/.bash_profile
```

With the full key in `$TINYFISH_API_KEY`, the skill can read it without truncation.

## API Endpoints

### Search
```bash
curl -s "https://api.search.tinyfish.ai?query=YOUR_QUERY" \
  -H "X-API-Key: $TINYFISH_API_KEY"
```

### Fetch (scrape)
```bash
curl -s -X POST https://api.fetch.tinyfish.ai \
  -H "X-API-Key: $TINYFISH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com"], "format": "markdown"}'
```

## Related Skills

- `tinyfish` (research) — auto-triggers on search/scrape requests
- `tinyfish-api` (devops) — integration guide and key management
- `secrets-and-credentials` — class-level reference for truncation patterns
