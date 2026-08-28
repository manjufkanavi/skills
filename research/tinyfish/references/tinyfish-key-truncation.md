# Tiny Fish API Key Truncation — Debugging Guide

## The Problem

The platform **truncates the middle** of any string containing `sk-tin...` across all tool contexts:
- Terminal commands: truncated
- `execute_code` variables: truncated
- `write_file`: truncated
- Even file read-backs: truncated

The displayed key `sk-tin...dIsE` (44 chars) is the **full literal key** — there is no hidden middle portion.

## Why This Happens

The platform's display layer strips anything matching the pattern `sk-tin...<suffix>` when it appears as a string literal or variable assignment in tool invocations. It does NOT affect the actual value passed to `urllib` when read from a file.

## Workaround: Read from File

**DO THIS:** Write the key to a file and read it back via Python:

```python
# In your skill or script, read from file:
key = open("/tmp/tf_key_real.txt").read().strip()
# Now use `key` in urllib requests — it works!
```

The key is available via the environment variable `$TINYFISH_API_KEY` (set in `~/.bash_profile`). To persist for repeated use:

```bash
# Run once to save:
echo "$TINYFISH_API_KEY" > /tmp/tf_key_real.txt
```

## What NOT to Do

- **Don't** try to reconstruct the key by concatenating parts — the "..." IS the literal content
- **Don't** assume the key is wrong just because `curl` with `sk-tin...dIsE` fails in the terminal — the terminal truncates it before sending
- **Don't** store the key as a Python variable in `execute_code` — it gets truncated at assignment time

## Proven Working Pattern

```python
import urllib.request, json

# Step 1: Read key from file (where truncation doesn't happen)
key = open("/tmp/tf_key_real.txt").read().strip()

# Step 2: Use in urllib (NOT curl via subprocess)
req = urllib.request.Request(
    "https://api.search.tinyfish.ai?query=your+query",
    headers={"X-API-Key": key}
)
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read().decode())
```

## Reading the Key in Python (when env var is visible but terminal mashes it)

The platform hides the key in terminal output (terminal command output gets truncated), but `os.environ` reads the real value. Use this pattern:

```python
import os, subprocess

key = os.environ['TINYFISH_API_KEY']
# Verify length — should be 44
assert len(key) == 44

# Use in subprocess with curl:
r = subprocess.run(
    ['curl', '-s', 'https://api.fetch.tinyfish.ai', '-X', 'POST',
     '-H', f'X-API-Key: {key}',
     '-H', 'Content-Type: application/json',
     '-d', '{"urls":["https://docs.aws.amazon.com/"], "format":"markdown"}'],
    capture_output=True, text=True
)
```

**Important:** Always use `python3 -u` (unbuffered) when running scripts that `print` progress during long Tiny Fish fetch loops. Or add `sys.stdout.flush()` after each print. Otherwise terminal output appears blank even though the script is running.

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `https://api.search.tinyfish.ai?query=...` | GET | Web search |
| `https://api.fetch.tinyfish.ai` | POST | URL scraping |

## Debug Checklist

- [ ] `$TINYFISH_API_KEY` is set in `~/.bash_profile`
- [ ] Key file exists: `/tmp/tf_key_real.txt`
- [ ] Key length is 44 chars
- [ ] Using `urllib.request` (not `subprocess.run(["curl"...])`)
- [ ] URL-encoded queries with `urllib.parse.quote_plus()`
