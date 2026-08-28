# Test Discovery Pitfalls — pytest, cargo, npm

Patterns discovered across project test runs where test collection behaves unexpectedly.

## pytest Recursive Discovery Tripling (iacgenie)

### Symptom

Test files appear at nested paths:
- `tests/test_health.py`
- `tests/tests/test_health.py`
- `tests/tests/tests/test_health.py`

Each test class runs 3 times (once per nesting level).

### Cause

`pytest` recursively discovers test files in subdirectories. If the project's `tests/`
directory contains another `tests/` directory (from a previous copy or migration),
pytest will collect from all levels.

### Fix

1. **Scope the run to the top-level only:**
   ```bash
   pytest tests/test_health.py --ignore=tests/tests/
   ```

2. **Or use a conftest filter at the project root:**
   ```python
   # conftest.py
   def pytest_ignore_collect(path, config):
       # Skip nested test directories
       if "tests/tests/tests" in str(path):
           return True
   ```

3. **Or clean up the duplicate:**
   ```bash
   rm -rf tests/tests/tests/
   ```

### Prevention

Ensure the test root is clearly delimited. Use `pytest.ini` with explicit testpaths:
```ini
[pytest]
testpaths = tests
```
This only scans the top-level `tests/`, not subdirectories.

## pytest Missing Fixture (iacgenie `nsqd`)

### Symptom

```
ERROR tests/test_health.py::TestHealthNSQ::test_nsqd_stats
E       fixture 'nsqd' not found
>       available fixtures: ..., pg, redis_ia, s3, ...
```

### Cause

A test file references a fixture (`nsqd`) that is defined in conftest.py but the conftest
is in a different directory layer and not being loaded by pytest.

### Fix

1. Verify the conftest is in the same directory (or a parent) as the test file.
2. If the fixture is in `tests/conftest.py` but the test is at `tests/tests/test_health.py`,
   add a conftest at `tests/tests/conftest.py` that imports it, or move the test.
3. Check `pytest --fixtures` output to see what fixtures are actually available.

## cargo Workspace Crate Name Mismatch (ASTral)

### Symptom

```rust
use astral_mcp_server::tools::Foo;  // compile error
```

Error: `cannot find module or crate 'astral_mcp_server'`

### Cause

Cargo package names use kebab-case (`astral-mcp-server`) while Rust crate names
use snake_case (`astral_mcp_server`). When the test crate IS the library crate
itself, it should reference itself with `crate::` instead.

### Fix

Change all intra-crate test imports:
```rust
// Before:
use astral_mcp_server::tools::Foo;

// After:
use crate::tools::Foo;
```

Or add to `Cargo.toml`:
```toml
[dev-dependencies]
astral-mcp-server = { path = "..", package = "astral_mcp_server" }
```

## npm Chained Test Short-Circuiting (LightSerp)

### Symptom

First test in a chain fails, subsequent tests never run:
```json
"test": "npm run test:search && npm run test:scrape && npm run test:auth"
```

### Cause

`&&` short-circuits on first failure. One failing test blocks the entire chain.

### Fix

Run sub-tests independently:
```json
"test": "npm run test:search || true; npm run test:scrape || true; npm run test:auth || true"
```

Or use a wrapper script that reports per-test results:
```bash
#!/bin/bash
failed=0
for test in search scrape auth scrape2 analysis optimization; do
  if npm run "test:$test" 2>&1; then
    echo "PASS: test:$test"
  else
    echo "FAIL: test:$test"
    ((failed++))
  fi
done
echo "Total failed: $failed"
exit $failed
```

## pytest --timeout Flag Without pytest-timeout (Hisaab, iacgenie)

### Symptom

```
error: unrecognized arguments: --timeout=10
```

### Cause

`pytest-timeout` plugin not installed. The test suite passes `--timeout=10` which
only works if the plugin is available.

### Fix

1. **Install the package:** `pip install pytest-timeout`
2. **Or remove the flag:** Run without `--timeout` in environments where it's not installed.
3. **Or make it conditional:** Use a wrapper that checks for the plugin:
   ```bash
   python3 -m pytest $(python3 -c "import pytest_timeout; print('--timeout=10')") testcases/
   ```

## Unknown Module Import (vulndb — `vulnai`)

### Symptom

```
ImportError while importing test module:
ModuleNotFoundError: No module named 'vulnai'
```

### Cause

Test files import from a package (e.g., `vulnai`) that isn't installed as a Python
package and isn't on `sys.path`. The source code directory exists but hasn't been
installed or isn't findable by Python's import machinery.

### Fix

1. **Install the package in development mode:**
   ```bash
   cd <vulndb_path> && pip install -e .
   ```
   Or if using Poetry: `poetry install`

2. **Or add the source root to PYTHONPATH:**
   ```bash
   PYTHONPATH=/path/to/vulndb/src pytest tests/
   ```

3. **Or check the project structure:** The import may reference a package name that
   doesn't match the directory name. For example, `from vulnai.foo import bar` expects
   a directory named `vulnai/` — not `vulndb/`.

### Detection

Before running tests, do a quick import probe:
```bash
python3 -c "import vulnai" 2>&1
```
If it fails, the package isn't findable — either install it or fix PYTHONPATH.
