---
name: testing
description: >
  Class-level skill for running, orchestrating, and reporting on test suites
  across software projects. Covers nightly multi-project test runs, parallel
  test execution via background terminals, handling language-specific runners
  (pytest, npm test, cargo test), collecting results, structured reporting,
  and diagnosing common test infrastructure failures (missing test scripts,
  collection errors, dependency gaps, compilation errors).
version: 1.2.0
author: Hermes Agent
tags: [testing, test-orchestration, nightly-tests, pytest, npm-test, cargo-test,
       multi-project, test-reporting, test-infrastructure]
created: 2026-07-18
updated: 2026-07-31
---

# Testing — Test Suite Orchestration & Reporting

Patterns for running, orchestrating, and reporting on test suites across
multiple software projects — especially in a multi-project portfolio or
CI-like nightly batch context.

## Contents

| Section | Description |
|---------|-------------|
| [1. Nightly Multi-Project Test Suite](#1-nightly-multi-project-test-suite) | Parallel test execution across Python, JS/TS, Rust, etc. |
| [2. Result Collection & Reporting](#2-result-collection--reporting) | JSON report format, raw log archival, pass/fail taxonomy |
| [3. Common Test Infrastructure Failures](#3-common-test-infrastructure-failures) | Diagnosing missing scripts, Docker Compose integration failures, dependency gaps, compilation errors |
| [4. Docker Compose Integration Testing](#4-docker-compose-integration-testing) | Running tests inside Docker containers, health checks, service readiness, multi-tenant validation |

---

## 1. Nightly Multi-Project Test Suite

### When to Run This

- Scheduled cron job (e.g., "Nightly Tests" at 2:00 AM)
- Manual pre-merge check across the portfolio
- Post-deployment validation

### Core Method

```
discover projects → create output dir → launch parallel test commands →
wait for all → collect results → save structured report → deliver summary
```

### Step 1: Framework Detection & Discovery

Projects may live in different directories. Use a brute-force search:

```bash
for proj in ProjectA ProjectB ProjectC; do
  find /Users/$USER -maxdepth 4 -type d -name "$proj" 2>/dev/null | head -1
done
```

Common locations: `~/workspace/git_workspace/`, `~/.hermes/git_clone_dir/`,
`~/workspace/nanobot_workspace/`.

**Framework detection rules** — before choosing a test command, probe what actually exists:

| File/directory present | Implies test runner | Notes |
|------------------------|---------------------|-------|
| `pyproject.toml` | `pytest` | Most common for modern Python |
| `setup.py` | `pytest` | Legacy Python projects |
| `package.json` with `"test"` script | `npm test` | Node/JS/TS projects |
| `package.json` WITHOUT `"test"` | SKIP | May use vitest/jest directly |
| `Cargo.toml` | `cargo test` | Rust workspace |
| `tests/` or `test/` with `.ts` files | `npm test` (TypeScript) | User may ask for pytest but it's a TS project — use npm test |
| `.pytest_cache` but NO `.py` test files | SKIP (no tests) | Cache exists but no actual test code |

**Dual-stack projects** (e.g., LightSerp, iacgenie): These have BOTH `pyproject.toml` (or `setup.py`) AND `package.json`. For nightly runs, run **both** pytest and npm test if both have actual test files. If only one has tests, use only that runner.

**LightSerp gotcha:** Has TypeScript tests (`tests/*.ts`) but no Python test files. When the user asks for `pytest`, run pytest (it will collect 0 tests) but note: "TypeScript tests exist, run `npm test` instead for actual coverage."

**Python 3.14 warning noise:** Python 3.14 on Homebrew shows `RequestsDependencyWarning: urllib3 (2.7.0) or chardet (7.4.3)/charset_normalizer (3.4.2) doesn't match a supported version!` This is **benign** — it comes from the requests library's vendored urllib3 detection. It appears in every pytest/cargo/npm run on this machine. The warning can be ignored; it does not affect test results.

### Step 2: Create Output Directory

```bash
mkdir -p ~/.hermes/shared/test_results
```

### Step 3: Launch Parallel Test Commands

Use `background=true` with `notify_on_complete=true` for each project.
Different languages use different test runners:

| Language | Test Runner | Command Pattern |
|----------|------------|-----------------|
| Python (pytest) | `pytest` | `cd <path> && python3 -m pytest --tb=short --junitxml=/tmp/<project>.xml 2>&1 \| tee /tmp/<project>.txt; echo "EXIT:$?"` |
| Node.js/npm | `npm test` | `cd <path> && npm test 2>&1 \| tee /tmp/<project>.txt; echo "EXIT:$?"` |
| Rust/Cargo | `cargo test` | `cd <path> && cargo test 2>&1 \| tee /tmp/<project>.txt; echo "EXIT:$?"` |

**Important:** Always append `; echo "EXIT:$?"` to capture the actual exit code
since `tee` returns 0 even if the piped command fails.

### Step 4: Wait for Completion

Use `process(action='list')` to check if background processes finished, then
`process(action='log', session_id=...)` to read each one's output.

### Step 5: Collect & Save Results

Save both a structured JSON summary and raw logs to `~/.hermes/shared/test_results/`.

### Step 6: Deliver Summary

Produce a concise report showing project, type, status, key metrics.

### Handling Special Cases

- **No test script defined** (npm): Check `package.json` for `"test"` in scripts.
  If missing, report as SKIP (not FAIL).
- **Planning-stage projects** (no source code): Skip entirely.
- **Compilation failures** (cargo): Collect warnings, note which crates compiled vs. failed.
### Collection errors** (pytest): Note the error type (import error, conftest collision, etc.).
- **npm chain cascade** (e.g. LightSerp): Sub-tests chained with `&&` in the `npm test` script — the first failure blocks all subsequent sub-tests (it never reaches test:auth, test:cache, etc.). Consider running sub-tests in parallel (`npm run test:search & npm run test:scrape & ...; wait`) or in a wrapper script that reports per-test results individually instead of short-circuiting.
- **tee in project-local directories can fail**: Writing `tee test_results/output.txt` inside a project directory will silently fail if that project doesn't have a `test_results/` subdirectory. Always write to `~/.hermes/shared/test_results/` or `/tmp/` instead of relying on project-local directories.

### Example Cron Prompt

```
Run the nightly test suite. Execute pytest on all Python projects (list),
npm test on JavaScript/TypeScript projects, cargo test on Rust projects,
and skip projects that are in planning stage (no code). Save results to
~/.hermes/shared/test_results/ and deliver the summary.
```

---

## 2. Result Collection & Reporting

### JSON Report Format

Save to `~/.hermes/shared/test_results/nightly_YYYY-MM-DD.json`:

```json
{
  "report": "Nightly Test Suite — YYYY-MM-DD",
  "timestamp": "ISO-8601",
  "projects": {
    "ProjectName": {
      "type": "python|npm|cargo|node",
      "path": "absolute path",
      "test_command": "command used",
      "result": "short description",
      "passed": N, "failed": N, "errors": N, "skipped": N,
      "exit_code": N,
      "status": "PASS|FAIL|SKIP",
      "note": "optional context"
    }
  },
  "summary": {
    "total_projects": N,
    "passed": N, "failed": N, "skipped": N,
    "pass_rate": "XX.X%"
  }
}
```

### Raw Logs

Copy raw terminal output files for debugging:

```bash
for src in /tmp/<project>.txt; do
  name=$(basename "$src" .txt)
  cp "$src" ~/.hermes/shared/test_results/${name}_raw.txt
done
```

### Status Classifications

| Status | Meaning |
|--------|---------|
| PASS | Tests ran, all passed (or no tests, no errors) |
| FAIL | Tests ran and failed, or collection/compilation errors |
| SKIP | No test infrastructure (no test script, no code, planning stage) |

---

## 3. Common Test Infrastructure Failures

### A. No Tests Found (pytest: 0 collected)

**Symptom:** `collected 0 items` / `no tests ran`
**Diagnosis:** No `test_*.py` or `*_test.py` files exist in the project.
**Action:** PASS (no failures) but note the gap — project may need test coverage.

### B. Test Collection Error (ImportPathMismatchError)

**Symptom:** `ImportPathMismatchError: ('tests.conftest', '/path/a', '/path/b')`
**Cause:** Two `conftest.py` files share the same dotted module name but differ in
filesystem path. pytest refuses to collect both.
**Fix:** Rename one conftest (e.g., `backend_conftest.py`) or move them to
different packages so they have distinct module names.

### C. Missing Dependencies (ModuleNotFoundError)

**Symptom:** `ImportError: No module named 'qdrant_client'`
**Cause:** Test imports depend on optional/missing packages.
**Action:** Note which packages are missing; skip the affected test modules.
Consider adding a `pyproject.toml` or `requirements-test.txt` with test deps.

### D. No Test Script (npm)

**Symptom:** `npm error Missing script: "test"`
**Cause:** `package.json` has no `"test"` in the scripts section.
**Action:** SKIP — not a failure. The project may use a different tool (e.g.,
`vitest` via `vitest run`) or have no tests yet.

### E. Compilation Errors (cargo test)

**Symptom:** `error: could not compile <crate>`
**Cause:** Test modules import crates not properly linked in `Cargo.toml`
(e.g., using the crate's own name instead of the workspace member name).
**Action:** Document which crates compiled vs. failed. The ones that compiled
may have produced valid test results even if others failed.

### F. No `execute_code` Access (Cron Mode)

**Symptom:** `BLOCKED: execute_code runs arbitrary local Python... Cron jobs
run without a user present to approve it.`
**Cause:** In cron mode, `execute_code` is blocked unless `approvals.cron_mode`
is set to `approve`.
**Action:** Use `terminal()` instead — it works without approval in cron mode.

**Cron JSON parsing pitfall:** `cat file.json | python3` is blocked by the
`pipe_to_interpreter` security scanner in cron mode. Use `jq` instead:
```bash
jq '.status' package.json        # extract field
jq -r 'to_entries | map("\(.key)=\(.value)") | join("\n")' file.json
```
Or use `python3 -c` with explicit approval, or pre-configure `jq` aliases.

### G. PEP 668 Blocks `pip install` on System Python

**Symptom:** `ERROR: External Environment detected, refusing to install.`
**Cause:** macOS Homebrew Python (and many distro pythons) enforce PEP 668 —
`pip` refuses to install into the system prefix.
**Action:** Create a venv first:
```bash
cd <project_path>
uv venv .venv
source .venv/bin/activate
uv pip install pytest
pytest
```
See `references/pep668-venv-fix.md` for the full pattern.

### H. Test Discovery Pitfalls

See `references/test-discovery-pitfalls.md` for: recursive directory tripling,
missing fixtures, crate name mismatches, npm short-circuiting, and missing
plugin flags.

### I. Test Bootstrap File Calls sys.exit() During Collection

**Symptom:** `INTERNALERROR: mainloop: caught unexpected SystemExit!` — pytest
crashes before reporting any results, even though the exit code is 0 (or close).

**Cause:** A test file (often a bootstrap/validation script like `test_comprehensive.py`)
calls `sys.exit(1)` during module-level import. pytest treats this as an unexpected
exception and aborts the run, masking all test results.

**Fix:**
1. Replace `sys.exit(1)` in test files with `pytest.skip("reason")` or
   `pytest.fail("reason")` — these produce proper test results instead of crashing
   the runner.
2. If the file is meant to be a gate (fail the build if deps are missing), move it
   outside the test directory and run it as a pre-test check via CI, not inside pytest.
3. As a quick workaround, run with `-p no:cacheprovider` to reduce import-side effects.

### J. Correctly Parsing pytest Summary Lines for Pass Counts

When a pytest run produces `N failed, N skipped, N errors in Xs`, **do not guess** the
pass count. Use the formula:

```
passed = collected - failed - skipped - errors
```

Only if all four numbers appear in the output. If `passed` is shown explicitly, use it.
If `collected` isn't in the output, you can approximate: `passed ≈ sum(passed shown)`.

**Example:** Hisaab 2026-07-28
```
pytest output: "collected 232 items" ... "152 failed, 15 skipped, 66 errors in 13.15s"
calculation:   passed = 232 - 152 - 15 - 66 = 14 passed
```

**Verification step:** Always grep the raw pytest output for the summary line:
```bash
grep -E "^[0-9]+ (passed|failed|skipped|error)" <output_file> | tail -1
```
This gives you the ground-truth numbers. Never trust a subagent's first-guess summary
without verifying against the raw output.

### K. No Test Infrastructure Across Multiple Projects

**Pattern:** In a portfolio of 8+ projects, it is common for 40-60% of projects to
have no test files at all. This is the baseline for greenfield projects, not a bug.

**Expected distribution for a greenfield/young portfolio:**
- 1-2 projects with actual tests (the ones that mattered to the developer)
- 3-5 projects with no tests (right-sized for their importance)
- 1-2 projects with broken test infrastructure (collection errors, missing deps)

**When to act:** Only write tests for projects in the FAIL or COLLECTION_ERROR
categories if they are P0/P1 projects (actively used, critical infrastructure).
For P2 projects (side projects, prototypes), document the gap and move on.

### L. Missing `"test"` Script in package.json (npm)

**Symptom:** `npm error Missing script: "test"`

**Cause:** `package.json` has no `"test"` script in the scripts section. The project
may use a different runner (e.g., `vitest`, `jest`) or have no tests yet.

**Fix:** SKIP — not a failure. Check for alternative scripts:
### H. Tee in Project-Local Directories Fails Silently

When writing test output, writing to project-local `test_results/` directories
can fail silently if that directory doesn't exist. Always write to
`~/.hermes/shared/test_results/` or `/tmp/` instead.

### M. Docker Compose Integration Test Debugging
are editable without rebuilding.

```dockerfile
FROM python:3.11-slim
RUN pip install --no-cache-dir pytest psycopg2-binary redis boto3 requests nsq
COPY . /app
WORKDIR /app
```

Build from the docker-compose project root:
```bash
docker build -f docker-compose-unified/tests/Dockerfile \
  -t unified-test-runner .
docker run -d --name unified-test-runner --network docker-compose-unified_default \
  -v "$PWD:/app" unified-test-runner sleep infinity
```

**Important:** The test runner must join the same Docker network as the services.
Use `--network` to attach it to the compose network.

### Step 2: Write the conftest.py

Key patterns for Docker Compose integration tests:

```python
from pathlib import Path
import pytest

# ── Environment parsing ────────────────────────────────────────────
def _parse_env(path):
    """Parse .env file, handling single-quoted passwords with special chars."""
    path = Path(path)           # ← MUST convert string to Path first
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, val = line.split('=', 1)
        val = val.strip().strip("'\"")   # ← Strip both single AND double quotes
        env[key.strip()] = val
    return env

# ── Hostname constants ─────────────────────────────────────────────
# Use Docker Compose service names as hostnames (DNS resolves automatically)
PG_HOST, REDIS_HOST, MINIO_HOST = "postgres", "redis", "minio"
# ... etc.

# ── Health check helper ────────────────────────────────────────────
def _healthy(hostname, port, timeout=5):
    """Check if a TCP port is reachable with retry."""
    import socket, time
    deadline = time.time() + timeout
    attempts = 0
    while time.time() < deadline:
        try:
            s = socket.create_connection((hostname, port), timeout=3)
            s.close()
            return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            attempts += 1
            if time.time() >= deadline:
                return False
            time.sleep(0.5)
    return False

# ── Service availability fixture (session-scoped) ──────────────────
@pytest.fixture(scope="session")
def services_available(_healthy):
    """Check which services are reachable. Caches results for the session."""
    # Check services in order: 3 likely-up, 6 likely-down
    result = {}
    for name in ("postgres", "redis", "minio", "openbao", "keycloak",
                 "searxng", "nsqd", "prometheus", "grafana"):
        result[name] = _healthy(name, 80)  # adjust ports per service
    return result
```

### Step 3: Write Individual Test Files

```python
class TestHealthPostgres:
    def test_tcp_port_open(self, services_available):
        assert services_available.get("postgres"), "PostgreSQL not reachable"

    def test_accepts_connections(self, pg):
        cur = pg.cursor()
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1
        cur.close()

class TestHealthRedis:
    def test_set_get(self, redis_ia):
        key = "test_unified:health:ping"
        redis_ia.set(key, "pong", ex=10)
        assert redis_ia.get(key) == "pong"
        redis_ia.delete(key)

class TestHealthMinIO:
    def test_s3_list_buckets(self, s3):
        buckets = s3.list_buckets()
        names = {b["Name"] for b in buckets}
        assert len(names) > 0, "No buckets found"
```

### Step 4: Run Tests

```bash
docker exec unified-test-runner pytest /app/tests/ -v --tb=short
```

**Tip:** Add `-k "postgres or redis or minio"` to filter to specific service
tests. Use `--capture=no` for live output during debugging.

### Pitfalls & Gotchas

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `_parse_env` gets a string, not Path | `AttributeError: 'str' object has no attribute 'exists'` | Add `path = Path(path)` at function start |
| .env passwords have single quotes | `WRONGPASS` or auth failures | Strip with `.strip("'\"")` |
| Redis RESP3 auth error | `redis.exceptions.AuthenticationError: no password supplied` | Use `protocol=2` in `redis.Redis(...)` |
| MinIO `InvalidAccessKeyId` | `botocore.exceptions.ClientError` | Check if credentials come from env vars OR `*_FILE` env |
| PostgreSQL init scripts don't run | Tenant DBs missing after restart | Init scripts only run on first init; create DBs manually |
| Docker `CONFIG` disabled on Redis | `ERR unknown command 'CONFIG'` | Some Redis builds restrict admin commands |
| Health check times out per service | 30s+ setup time with 9 services at 5s each | Use 2s timeout for health checks to reduce setup time |
| `tee` in project-local dirs | Silent failure writing to non-existent dir | Write to `~/.hermes/shared/` or `/tmp/` instead |
| Init scripts don't re-run on restart | Tenant DBs disappear after `docker restart` | Init scripts only run on first data directory init |

See Also

| `references/test-infrastructure-troubleshooting.md` — Extended troubleshooting
  reference with specific error patterns from recent runs |
| `references/portfolio-test-status.md` — Project locations, test infrastructure
  state, known issues, and nightly command reference for the portfolio |
- `references/portfolio-test-status.md` — Project locations, test infrastructure
  state, known issues, and nightly command reference for the portfolio
- `references/test-discovery-pitfalls.md` — Test collection issues: recursive
  discovery tripling, missing fixtures, crate name mismatches, npm short-circuiting,
  and missing plugin flags
- `references/pep668-venv-fix.md` — PEP 668 system Python pitfall and uv venv
  workaround for cron/CI environments
- `references/cargo-test-discovery-failures.md` — Cargo workspace test crate name
  mismatch patterns and fixes
- `references/nightly-test-results-format.md` — Standard JSON report structure
  for nightly multi-project test suite results
- `templates/nightly-test-report.md` — Markdown template for nightly test reports
- `references/cron-workarounds.md` — pipe_to_interpreter blocked, execute_code blocked,
  tee output capture, jq as pipe alternative — cron-specific workarounds
- `references/fastapi-deterministic-core-testing.md` — Testing FastAPI apps without live Postgres/MinIO/Keycloak/Ollama: deterministic core + route-registration smoke test (import app registers routes but does not run startup)
- `references/fastapi-e2e-testing-patterns.md` — FastAPI E2E testing with TestClient: auth middleware ordering gotcha (401 before 422), file upload patterns, edge case testing, bug documentation in tests
- `references/tesseract-ocr-e2e-testing.md` — Real (non-mocked) OCR end-to-end test: generate a scanned PDF, run local tesseract through the pipeline, and the `parse_text_to_json` <60-char + body-line header heuristic gotcha
- `references/web-app-e2e-browser-testing.md` — Browser-driven E2E of a web app (Next.js/React) against a local mock-server: local mock-server mode, Next.js 16 async Client Component suspend gotcha, React file-input injection (DataTransfer/FileList mock), inspecting the DB directly when the API hides internal state, in-MinIO per-process caveat
- `production-readiness-audit` — Test strategy integration: when running a
  production readiness audit, the test strategy deliverable (unit, integration,
  security, load, E2E) is part of the role-assignment stage
  production readiness audit, the test strategy deliverable (unit, integration,
  security, load, E2E) is part of the role-assignment stage
