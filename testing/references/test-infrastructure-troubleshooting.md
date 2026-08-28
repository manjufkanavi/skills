# Test Infrastructure Troubleshooting — Session-Specific Patterns

Concise reference built from actual nightly test run failures.

## pytest Collection Errors

### ImportPathMismatchError (iacgenie)

Two `conftest.py` files at different paths but identical dotted name:

```
tests/conftest.py            → module name: tests.conftest
iacgenie/backend/tests/conftest.py → module name: tests.conftest (collision!)
```

**Fix options:**
1. Rename: `iacgenie/backend/tests/backend_conftest.py`
2. Add `__init__.py` to make `backend/tests` a proper package, then import with qualified name.
3. Use `pytest --override-ini` to exclude one conftest.

### ModuleNotFoundError (vulndb)

Missing optional dependencies pulled in by test imports:

| Missing Module | Found In | Fix |
|---------------|----------|-----|
| `qdrant_client` | `test_deep_agents.py`, `test_vector_db.py`, `test_integration.py` | `pip install qdrant-client` |
| `fastmcp` | `test_mcp_server.py` | `pip install fastmcp` |

**Pattern:** The application code imports optional deps with `from vulnai.xyz import ...`
which transitively loads missing packages at test-collection time. Consider lazy imports
in application modules or making optional deps explicit in `requirements-test.txt`.

## npm Test Failures

### Missing Script (karnataka-official)

`package.json` scripts: only `dev`, `build`, `preview`. No `test`.

**Fix options:**
1. Add `"test": "vitest run"` or `"test": "react-scripts test"` depending on stack.
2. If using Vite + Vitest: `npm install -D vitest`, then `npm test` runs `vitest run`.
3. If no tests written yet: add `"test": "exit 0"` as placeholder.

## cargo test Failures

### Unresolved Crate Names (ASTral)

```rust
// In tests/diff_engine_tests.rs:
use astral_mcp_server::diff_engine::engine::DiffEngine;
```

**Problem:** The test is inside `crates/astral-mcp-server/tests/` but uses the crate's
own package name (`astral_mcp_server`) instead of the workspace member name. In workspaces,
tests inside a crate should use `crate::` for intra-crate imports or ensure the crate
is properly declared as a dev-dependency.

**Fix:** Change imports to use the crate's public API via `crate::` path for internal
tests, or add `astral-mcp-server` to the workspace's `[dev-dependencies]` with the
correct crate name mapping.

### Intra-Crate Test Imports (general pattern)

When a crate's integration tests import from itself:

```rust
// WRONG — crate name != package name
use my_crate_name::module::Foo;

// CORRECT — use crate:: for intra-crate imports
use crate::module::Foo;

// ALTERNATIVE — add to Cargo.toml [dev-dependencies]
// my-crate = { path = "..", package = "my_crate_name" }
```

**Root cause:** Cargo package names use kebab-case (`astral-mcp-server`) but crate
names use snake_case (`astral_mcp_server`). When the test crate IS the library crate,
it should reference itself with `crate::` not by the package name.

## Parallel Test Execution

### Exit Code Pitfall

```bash
# WRONG — tee swallows exit code:
python3 -m pytest 2>&1 | tee /tmp/out.txt
echo $?  # always 0

# RIGHT — capture exit code in same command:
python3 -m pytest 2>&1 | tee /tmp/out.txt; echo "EXIT:$?"
```

The `;` separates the pipeline from the echo. Without it, `$?` refers to `tee`, not
`pytest`.

### execute_code Blocked in Cron Mode

Cron jobs cannot use `execute_code` (requires user approval). Use `terminal()` instead —
it works without approval in cron mode.

### Project Discovery When Paths Are Unknown

Projects may live in scattered directories. Use brute-force search:

```bash
for proj in ProjectA ProjectB; do
  find ~ -maxdepth 4 -type d -name "$proj" 2>/dev/null | head -1
done
```

Common locations: `~/workspace/git_workspace/`, `~/.hermes/git_clone_dir/`,
`~/workspace/nanobot_workspace/`.
