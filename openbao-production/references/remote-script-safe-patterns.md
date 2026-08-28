# Remote Python Script Safety Patterns

## The `***` Python Pitfall (CRITICAL 2026-08)

When writing Python scripts that embed tokens or secrets, **NEVER use `***` as a placeholder** — it is valid Python syntax (the star/expand/unpack operator) and will cause a syntax error:

```python
# WRONG — crashes with: SyntaxError: invalid syntax (line 4, column 11)
TOKEN=*** = "http://127.0.0.1:8200/v1"

# WRONG — linter catches this immediately on the local machine
# SyntaxError: invalid syntax (line 4, column 17)
```

**Correct approach:** Always read tokens/secrets from a file using Python's `json.load()`:

```python
with open("/path/to/init_keys.json") as f:
    TOKEN=json.l...s = "http://127.0.0.1:8200/v1"
HEADERS = {"X-Vault-Token": TOKEN, "Content-Type": "application/json"}
```

## Shell Variable Corruption Pattern

When passing tokens through shell variables (especially over SSH), the token can be truncated or mangled:

```bash
# WRONG — token gets truncated/corrupted
TOKEN=*** mkanavi:mkanavi /home/...'
curl -H "X-Vault-Token: $TOKEN" ...

# CORRECT — read token from file inside Python
python3 -c 'import json; TOKEN=*** If API calls return "permission denied" even with what looks like the correct token, the token was likely corrupted during shell variable assignment. Always verify by reading the token from the source file inside the Python script.

## Script Delivery Patterns (Ordered by Safety)

| Method | Safety | Notes |
|--------|--------|-------|
| **Python json.load() + heredoc** | High | Use `<< 'EOF'` (single-quoted delimiter) to prevent ALL shell expansion |
| **Base64 encode + decode** | High | Avoids all shell interpolation; write locally, SCP, decode on VM |
| **SCP Python file** | High | Write script locally, SCP to VM, execute there |
| **Inline `python3 -c '...'`** | Medium | Single-quote the Python code, but `@` in passwords still causes issues |
| **Shell variable interpolation** | LOW | Token gets mangled; secrets in heredocs get glob-expanded |

## Heredoc Pattern for Python Scripts

Use **single-quoted heredoc delimiter** to prevent ALL shell expansion (`$`, `` ` ``, `@`, `*`, `&`):

```bash
ssh user@vm 'bash -s' << 'EOF'
import urllib.request, json

with open("/path/to/init_keys.json") as f:
    TOKEN=*** Script continues — no shell expansion happens
EOF
```

The `<< 'EOF'` (with quotes around the delimiter) is CRITICAL — without quotes, `$VAR` and `*` patterns get expanded by the shell.

## When to Use Each Pattern

- **Quick one-liner test**: `python3 -c '...'` — fine for simple checks where no secrets are involved
- **Script with secrets**: Always use heredoc (`<< 'EOF'`) or SCP — NEVER inline secrets
- **Complex multi-line scripts**: SCP or heredoc — inline `-c` gets unwieldy
- **Token reading**: Always use `json.load()` from file, never shell variables
- **Password in Python code**: Write to temp file first, then have Python read from file
