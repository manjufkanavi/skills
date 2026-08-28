# Cargo Workspace Test Discovery Failures

## The Problem

`cargo test` fails to compile test modules with errors like:

```
error[E0433]: cannot find module or crate `my_crate` in this scope
 --> crates/my-crate/tests/foo_tests.rs:1:5
  |
1 | use my_crate::something;
  |     ^^^^^^^^ use of unresolved module or unlinked crate
  = help: if you wanted to use a crate named `my_crate`, use `cargo add my_crate` to add it to your `Cargo.toml`
```

## Root Cause

The test file imports the crate using a **name that doesn't match** the actual
crate name as registered in `Cargo.toml`.

Common mismatches:
| Test file uses | Cargo.toml has | Correct import |
|---------------|---------------|-----------------|
| `astral_mcp_server` | `name = "astral-mcp-server"` | `use astral_mcp_server::...` (crate name uses underscore, not hyphen) |
| `my-project` | `name = "my_project"` | `use my_project::...` (hyphen becomes underscore) |
| `MyCrate` | `name = "my-crate"` | `use my_crate::...` (case+hyphen mapping) |

**Rust cargo auto-translates package names:** hyphens and dashes become
underscores, and names are lowercased for the import path.

## The Fix

1. Check the `[package]` name in the crate's `Cargo.toml`.
2. Run `cargo test --package <crate-name>` to see the actual crate name used.
3. Fix the import path in the test file to match the actual crate name.

### Example

```toml
# Cargo.toml
[package]
name = "astral-mcp-server"  # hyphen
```

In `Cargo.toml` the hyphen is used, but Rust's crate naming convention maps
hyphens to underscores for the import path. The test file should use:

```rust
use astral_mcp_server::tools::...;
```

If the test is itself in the same crate directory (as a binary test), the
crate name must be a dev-dependency.

## Special Cases

### Binary-Only Crate (Tests Import Non-Existent Library)

**Symptom:** `error[E0433]: cannot find module or crate 'astral_mcp_server' in this scope`
**Cause:** The crate's `Cargo.toml` defines only a `[[bin]]` target (binary-only),
with no `[[lib]]` section. Test files import library modules (`use astral_mcp_server::tools::...`)
that don't exist as an exportable library.

**Reproduction pattern:**
```toml
# Cargo.toml — binary-only, no library target
[[bin]]
name = "astral-mcp-server"
path = "src/main.rs"

# No [[lib]] section
```
```rust
// tests/server_tests.rs — tries to import library code
use astral_mcp_server::tools::...;      // fails
use astral_mcp_server::transport::...;  // fails
```

**Fix options:**

1. **Add `[[lib]]` section** if the source tree has library modules that should be tested:
   ```toml
   [lib]
   name = "astral_mcp_server"
   path = "src/lib.rs"

   [[bin]]
   name = "astral-mcp-server"
   path = "src/main.rs"
   ```

2. **Move tests to integration test style** if the crate is meant to be binary-only:
   - Tests should exercise the binary via command-line invocation, not module imports.
   - Use `std::process::Command` to run the binary and check stdout/stderr/exit code.

3. **Fix test imports to match crate name** if the import path is wrong:
   - Run `cargo test --package <crate-name> --no-run 2>&1 | grep -i 'compiling'`
   - The output shows the actual crate name (hyphens become underscores).
   - Update the `use` statement in test files accordingly.

### Workspace root tests vs member crate tests

- Tests in `tests/` at the workspace root belong to the **workspace member crate**,
  not the workspace itself.
- If you put integration tests in `crates/my-crate/tests/`, they are part of the
  `my-crate` member, not a separate crate.
- To create a truly separate integration test crate, add it as a `[dev-dependencies]`
  entry in the crate's `Cargo.toml`.

### `cargo fix --lib -p <crate>`

Use `cargo fix --lib -p <crate>` to auto-fix simple import issues. Not all
issues are fixable automatically.

### Viewing resolved crate names

```bash
cargo test --package <crate-name> --no-run 2>&1 | grep -i 'compiling\|error'
```

The compilation output shows the actual crate names being used.
