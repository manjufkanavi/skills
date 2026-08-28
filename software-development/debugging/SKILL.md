---
name: debugging
description: "Debug Python, Node.js, and async code — pdb, debugpy, remote-pdb, Node.js --inspect, Chrome DevTools Protocol, post-mortem, and deadlock debugging."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, python, node, pdb, debugpy, inspect, dap, post-mortem, deadlock]
---

# Debugging — Complete Reference

Complete guide for debugging Python, Node.js, and async code in production and development environments.

## Contents

| Section | Description |
|---------|-------------|
| [1. Python Debugging](#1-python-debugging) | pdb, debugpy, remote-pdb, pytest |
| [2. Node.js Debugging](#2-nodejs-debugging) | Node.js --inspect, Chrome DevTools Protocol |

---

## 1. Python Debugging

### Tools Overview

| Tool | When |
|---|---|
| **`breakpoint()` + pdb** | Local, interactive, simplest |
| **`python -m pdb`** | Quick poking without source edits |
| **`debugpy`** | Remote / headless / attach to running process |
| **`remote-pdb`** | Terminal-friendly remote debugging (nc-based) |

### pdb Quick Reference

| Command | Action |
|---|---|
| `n` | next line (step over) |
| `s` | step into |
| `r` | return from current function |
| `c` | continue |
| `w` | where (stack trace) |
| `p expr` / `pp expr` | print / pretty-print expression |
| `display expr` | auto-print expr on every stop |
| `b file:line` | set breakpoint |
| `!stmt` | execute arbitrary Python |
| `interact` | full Python REPL in current scope |

### Local Breakpoint

```python
def compute(x, y):
    result = some_helper(x)
    breakpoint()  # drops into pdb here
    return result + y
```

**Remove `breakpoint()` before committing.** Safety net:
```bash
rg -n 'breakpoint\(\)' --type py
```

### Launch Under pdb (No Source Edits)

```bash
python -m pdb path/to/script.py arg1 arg2
(Pdb) b path/to/script.py:42
(Pdb) c
```

### Debug pytest

```bash
# Drop to pdb on failure:
scripts/run_tests.sh tests/foo_test.py::test_bar --pdb -p no:xdist
```

**⚠️ pdb does NOT work under xdist.** Always add `-p no:xdist` or `-n 0`.

### Remote Debug with debugpy

**Source-edit pattern:**
```python
import debugpy
debugpy.listen(("127.0.0.1", 5678))
debugpy.wait_for_client()
debugpy.breakpoint()
```

**No source edit:**
```bash
python -m debugpy --listen 127.0.0.1:5678 --wait-for-client your_script.py arg1
```

**Attach to running process:**
```bash
python -m debugpy --listen 127.0.0.1:5678 --pid <pid>
```

### remote-pdb (Cleaner for Terminal Agents)

```bash
pip install remote-pdb
```

```python
from remote_pdb import set_trace
set_trace(host="127.0.0.1", port=4444)
```

Connect: `nc 127.0.0.1 4444`

### Post-Mortem

```python
import pdb, sys
try:
    run_the_thing()
except Exception:
    pdb.post_mortem(sys.exc_info()[2])
```

Or with `PYTHONFAULTHANDLER`:
```bash
PYTHONFAULTHANDLER=1 python -m pdb -c continue script.py
# On crash, pdb lands at the exception frame
```

### Pitfalls

1. **pdb under pytest-xdist silently does nothing** — use `-p no:xdist`
2. **`breakpoint()` in CI hangs** — never commit it
3. **`PYTHONBREAKPOINT=0`** disables all breakpoints — check env
4. **debugpy.listen blocks only with wait_for_client()** — without it, execution continues
5. **Attach to PID fails on hardened kernels** — ptrace_scope may need `echo 0 > /proc/sys/kernel/yama/ptrace_scope`
7. Threads — pdb only debugs current thread; use debugpy for multithreaded code
8. async — await in pdb requires Python 3.13+ or asyncio.ensure_future tricks
9. Forking/multiprocessing — pdb does not follow forks; debug one process at a time
10. Background process stdout buffering — print() buffers when stdout is not a TTY (background processes, CI, subprocess pipes). Result: agent sees nothing for minutes while the process runs. **Fix**: always use `print(msg, flush=True)` or `sys.stdout.flush()` after important status prints in long-running scripts. Pattern: define `flush_print(msg)` that wraps `print(msg, flush=True)` and use it for ALL progress output.
11. Sibling subagent file conflicts — when multiple subagents run in parallel, concurrent writes to the same file silently overwrite each other. **Fix**: coordinate file ownership (each subagent writes to its own path), or use file locks, or run sequentially when file writes are involved.
12. Demo-only auth flow masquerading as production — **pitfall**: a platform's login/signup/callback pages call `loginDemo()` or ignore the auth code from Keycloak, making it look like "auth works" when in fact no real authentication happens. **Symptoms**: login succeeds instantly without network call, callback page has `loginDemo()` hardcoded, backend only exposes `/verify` but no login/signup/refresh endpoints. **Diagnosis**: check every auth path in the frontend for `loginDemo`, mock token creation, or ignored URL parameters. Verify that POST /api/auth/login actually calls the backend (not a local mock). Check if tokens are real JWTs or fake strings like `"demo-token"`. **Fix**: implement real backend auth endpoints (login, signup, refresh), fix the callback to exchange Keycloak code for tokens, replace demo calls with real backend auth in context provider. See `auth-integration` skill for the full migration pattern (references/demo-to-production-auth-migration.md).

---

## 2. Node.js Debugging

### Node.js --inspect

```bash
# Start with inspect port
node --inspect src/index.js

# Non-blocking (continue execution after attach)
node --inspect-brk src/index.js

# Custom port
node --inspect=9229 src/index.js
```

### Chrome DevTools Protocol (CDP)

```bash
# 1. Start Node with inspect
node --inspect src/index.js

# 2. Open Chrome, go to chrome://inspect

# 3. Or use CDP directly for scripted debugging
node --inspect -e '
const { Client } = require("http");
// Access CDP at http://127.0.0.1:9229/json
'
```

### Chrome Inspector Commands

1. Navigate to `chrome://inspect/#devices`
2. Find the "Remote Target" with your Node process
3. Click "Inspect" — opens DevTools
4. Set breakpoints, step through, inspect variables

### Common Patterns

**Breakpoint in code:**
```javascript
debugger;  // hits when Node is in inspect mode
```

**Programmatic CDP attach:**
```javascript
const CDP = require("chrome-remote-interface");
(async () => {
  const client = await CDP({ port: 9229 });
  const { Runtime, Debugger } = client;
  await Runtime.enable();
  await Debugger.enable();
  await Debugger.setPauseOnExceptions({ state: "all" });
  // Use Runtime.evaluate, etc.
  await client.close();
})();
```

### Debugging Async/Deadlocks

```javascript
// Use --inspect with Chrome DevTools
// Watch for:
// - Event loop blocking
// - Unhandled promise rejections
// - Memory leaks (use chrome://inspect → Memory tab)
```

### Common Pitfalls

1. **`debugger` statement hangs in non-inspect mode** — Node will wait forever for a debugger
2. **--inspect-brk pauses at first line** — use `--inspect` for non-blocking startup
3. **Breakpoints in transpiled code** — source maps may not work with bundled output; debug the original source
4. **Child processes don't inherit inspect** — Node must be started with `--inspect` in each process
5. **Only one debugger can attach** — Chrome DevTools exclusive; close browser DevTools before running another debugger

---

## Quick Reference: Debug Recipes

| Problem | Solution |
|---------|----------|
| Test fails, traceback unclear | `breakpoint()` or `python -m pdb script.py` |
| Long-running process misbehaves | `remote-pdb` or `debugpy` attach |
| Post-mortem on crash | `PYTHONFAULTHANDLER=1 python -m pdb -c continue script.py` |
| Async handler deadlocks | `remote_pdb.set_trace(host="127.0.0.1", port=4444)` then `nc 127.0.0.1 4444` |
| Node.js hangs or slow | `node --inspect`, inspect in Chrome DevTools |
| Node.js Promise rejection | `process.on('unhandledRejection', (r) => console.error(r))` + `debugger` |
| Python async await in pdb | Python 3.13+ `await` in pdb, or `!stmt` with `asyncio.ensure_future` |

---

## 3. Frontend SPA Debugging

### SPA Shows Wrong Page (No Routing)

**Symptom:** The frontend SPA loads but always shows the same page (e.g., a settings/dashboard view) regardless of the URL. No console errors.

**Root cause:** `App.tsx` has no routing — it unconditionally renders one component for every URL. Page components exist (LandingPage, SignInPage, etc.) but are never imported or rendered.

**Diagnosis checklist:**
1. Open `App.tsx` — does it have `<Route>`, `useLocation()`, or conditional rendering?
2. If no routing: check if page components exist elsewhere in the project
3. The fix is to add React Router (see references/spa-wrong-page-diagnosis.md)

**Reference:** `references/spa-wrong-page-diagnosis.md`

### MLX LM API Quirks

When working with MLX LM for model inference and benchmarking, see `references/mlx-lm-api-quirks.md` for critical API quirks: `mlx_lm.generate()` does NOT accept `temperature`, model loading takes 2–4 minutes for 3B models, and LoRA adapter loading requires `model.freeze()` before `add_lora_to_model()`.

---

## 4. Redirect Loop Debugging

### Auth Redirect Loop (e.g., to 127.0.0.1:8083)

**Symptom:** User navigates to a protected service, gets bounced to a login page, but the login URL points to `127.0.0.1` (localhost) instead of the public hostname.

**Root cause:** Usually one of:
- The authentication backend (e.g., Keycloak realm) is misconfigured or missing, returning 404/500
- A reverse proxy (nginx, Cloudflare) strips or overrides `X-Forwarded-Proto`/`X-Forwarded-Host` headers
- The client app was deployed with hardcoded localhost URLs

**Diagnosis checklist:**
1. Trace the redirect chain: `curl -svL https://<service>/` — look for all `302` hops
2. Check each redirect's `Location:` header — is it using the correct hostname?
3. Test the auth backend directly: `curl -sv https://auth.example.com/realms/<realm>/protocol/openid-connect/auth`
4. Verify the service env vars: `docker exec <container> env | grep AUTH\|KEYCLOAK\|REALM\|BASE_URL`
5. If auth endpoint returns 404/500 → the realm/client is missing or broken

**Keycloak-specific:** See `references/keycloak-missing-realm-redirect-loop.md` (in the keycloak skill) for the complete realm-missing diagnosis and fix.

**Proxy-specific:** If the redirect shows the backend's internal hostname instead of the public one, ensure `proxy_set_header Host $host;` and `proxy_set_header X-Forwarded-Proto $scheme;` are set in the nginx vHost.
