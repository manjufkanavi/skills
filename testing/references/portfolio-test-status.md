# Portfolio Test Status — Updated 2026-07-29

Project locations, test infrastructure state, and known issues.
Only covering active/not-planning projects.

## Project Locations

| Project | Workspace Path | Type | Notes |
|---------|---------------|------|-------|
| FlutterScan | `~/workspace/git_workspace/FlutterScan` | Python (setup.py) | Zero test files. Has `flutter_metadata/` subpackage. |
| Hisaab | `~/.hermes/git_clone_dir/Hisaab` | Python (FastAPI) + Flutter | 232 pytest test files in `testcases/`. E2E tests need backend API running. |
| LightSerp | `~/workspace/git_workspace/LightSerp` | Node.js/TypeScript | 6 chained npm sub-tests. No Python tests. TypeScript only. |
| iacgenie | `~/workspace/git_workspace/iacgenie` | Python + Node.js | `tests/` directory with pytest config. Dual-stack project. |
| vulndb | `~/.hermes/git_clone_dir/vulndb` | Python (Poetry) | `pyproject.toml`. 10 collection errors — `ModuleNotFoundError: No module named 'vulnai'`. Tests import from a `vulnai` package that isn't installed or in PYTHONPATH. Up from 4 errors (was `qdrant_client`/`fastmcp`). |
| ASTral | `~/workspace/git_workspace/ASTral` | Rust workspace | 5 crates. `astral-mcp-server` tests fail (unresolved crate imports). `astral-core` passes 24/32 tests — 8 failures in `ir_adapter_tests`. Package name `astral-mcp-server` → crate `astral_mcp_server` mismatch in test files. |
| personal_bot | `/Users/manjunathkanavi/personal_bot` | Python | No test files. Has `.pytest_cache` but no actual test code. |
| karnataka-official | `~/.hermes/git_clone_dir/karnataka-official` | React/TypeScript | No `test` script in package.json. |

## Skipped / Inactive

| Project | Reason |
|---------|--------|
| llmgenie | Planning stage — README + docs only, no source code. |

## Known Infrastructure Dependencies

These projects need specific services/dependencies running in the cron environment to pass:

- **Hisaab**: Backend server (FastAPI) reachable on localhost. Also: `pytest-timeout` must be installed if `--timeout` flag is used.
- **LightSerp**: SearXNG on port 8070 (search tests), LightPanda binary (scrape tests). Note: npm sub-tests are chained with `&&` — first failure blocks all subsequent sub-tests.
- **vulndb**: `vulnai` package installable via `pip install -e .` or add source dir to PYTHONPATH
- **iacgenie**: API server running on localhost:8000; `pytest-timeout` must be installed if `--timeout` flag is used.

## Known Test Infra Issues

| Issue | Projects | Notes |
|-------|----------|-------|
| iacgenie nested test dirs | iacgenie | Tests found at `tests/`, `tests/tests/`, `tests/tests/tests/` — pytest discovers recursively, causing tripling. Add `-x` or scope to top-level. |
| iacgenie missing `nsqd` fixture | iacgenie | `test_health.py` references `nsqd` fixture not defined in conftest — 3 ERROR results. |
| Hisaab `--timeout` flag | Hisaab | `pytest-timeout` not installed; `--timeout=10` causes collection failure. Remove flag or install package. |
| Hisaab legacy port | Hisaab | Tests target `localhost:5173` (Vite dev server port) rather than `localhost:8000` (FastAPI). |
| ASTral package vs crate name | ASTral | Cargo package `astral-mcp-server` → crate name `astral_mcp_server`. Tests must use `crate::` or `astral_mcp_server::` (underscore, not hyphen). |

## Nightly Test Command Reference

```bash
# Python projects
cd <path> && python3 -m pytest -v --tb=short 2>&1 | tee ~/.hermes/shared/test_results/<project>.txt; echo "EXIT:$?"

# Node.js
cd <path> && npm test 2>&1 | tee ~/.hermes/shared/test_results/<project>.txt; echo "EXIT:$?"

# Rust
cd <path> && cargo test 2>&1 | tee ~/.hermes/shared/test_results/<project>.txt; echo "EXIT:$?"
```

## Most Recent Run (2026-07-30)

- **Hisaab:** 152 FAILED, 15 SKIPPED, 66 ERROR — backend not running (ECONNREFUSED on port 8000/5173). 232 total tests collected.
- **iacgenie:** TIMEOUT — pytest hangs during collection (120s limit). Need to debug slow import.
- **vulndb:** 10 COLLECTION ERRORS — `ModuleNotFoundError: No module named 'vulnai'`
- **ASTral (astral-core):** 24 passed, 8 failed — failures in `ir_adapter_tests`. MCP server won't compile.
- **karnataka-official:** MISSING SCRIPT — no "test" in package.json
- **FlutterScan/LightSerp/personal_bot:** No test files (0 collected)
- **llmgenie:** SKIPPED (planning stage)

## Run (2026-07-29) — Framework Detection Notes

- **LightSerp** and **iacgenie** are dual-stack (Python + Node.js). For nightly runs, both pytest AND npm test should be considered. Python runs collected 0 tests in both — TypeScript tests only.
- **Python 3.14** on this machine produces benign `RequestsDependencyWarning` about urllib3/chardet version mismatch in every pytest run. Ignore the warning.
- **cron mode** blocks `cat file.json | python3` (pipe_to_interpreter). Use `jq` as alternative for JSON parsing.
