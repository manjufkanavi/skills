# Base64 SSH Script Transport — Session Pattern (2026-08-06)

## The Problem

When passing Python scripts with complex quoting (HCL policies with `"sys/*"`,
token variables, nested strings) through SSH, three failure modes exist:

1. **Heredoc stripping quotes**: `path "sys/*"` becomes `path sys/*` (bash strips
   inner quotes even in single-quoted heredocs when mixed with Python strings)
2. **Shell globbing of `***`**: The token placeholder `TOKEN=*** gets expanded by
   the local shell even inside heredocs, corrupting the remote script
3. **Base64 encoding works**: but the resulting Python file still contains `***`
   which is a valid Python syntax operator causing `SyntaxError` on the remote

## The Solution — Two-Layer Transport

### Step 1: Write correct script locally (verify with py_compile)
```bash
python3 -m py_compile /path/to/script.py
```

### Step 2: Base64 encode locally
```bash
base64 /path/to/script.py > /tmp/script.b64
```

### Step 3: SCP + decode + execute on remote
```bash
scp /tmp/script.b64 user@host:/tmp/script.b64
ssh user@host "base64 -d /tmp/script.b64 | python3"
```

### Alternative — echo encode via Python
```bash
python3 -c "import base64; print(base64.b64encode(open('/path/to/script.py','rb').read()).decode())" | \
  ssh user@host "base64 -d | python3"
```

## When to Use

Use this pattern when:
- The script contains HCL config with nested quotes
- The script references token variables that contain `$`, `*`, `!`
- Heredocs have failed with quote-stripping or globbing errors
- You've seen `SyntaxError` after base64 decode (check for `***` placeholder issues)

## Pitfall: `***` in Python Source Code

The string `***` is Python's unpacking operator. It is ONLY valid on the right side
of `=`:
```python
# CORRECT (unpacking into multiple variables)
a, b = [1, 2]  # OK

# WRONG (unpacking operator on left side of assignment)
TOKEN=*** = "http://127.0.0.1:8200/v1"  # SyntaxError!
```

When writing Python to read a token from a JSON file, the correct line is:
```python
with open("init_keys.json") as f:
    TOKEN=json.load(f)["root_token"]
```

NEVER write `TOKEN=***` — it is NOT a placeholder that gets substituted.
It is literally the three asterisk characters, which cause `SyntaxError`.

## When NOT to Use

- Simple one-liners: use heredoc directly
- Scripts with no special characters: SCP the Python file directly
- Interactive scripts: use PTY mode, not piped stdin
