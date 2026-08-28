# PEP 668 and Python Virtual Environment Pitfalls

## The Problem

On macOS with Homebrew Python (or any PEP 668 system Python), `pip install` fails:

```
ERROR: External Environment detected, refusing to install.
hint: See PEP 668 for the detailed specification.
```

This blocks test execution in cron jobs, CI runners, or any environment where
the system Python is managed.

## The Fix

Use **uv** (or `python3 -m venv`) to create an isolated virtual environment.

### Option A: uv (recommended — installed on this host)

```bash
cd <project_path>
uv venv .venv
source .venv/bin/activate
uv pip install pytest  # or any deps
pytest
```

### Option B: stdlib venv

```bash
cd <project_path>
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
pytest
```

## Key Points

- `uv venv` is ~3x faster than `python3 -m venv` and handles dependency
  resolution better.
- Use `uv pip install` (not `pip install`) inside the venv to avoid path
  confusion when multiple pythons are installed.
- Always `source .venv/bin/activate` before running pytest or importing.
- In cron mode, use `terminal()` not `execute_code` — terminal is not blocked.

## Related Errors

- `pip: command not found` — pip is not bundled with this Python. Use `uv pip`
  or `python -m pip`.
- `ModuleNotFoundError` during pytest collection — deps not installed in the
  active venv. Run `uv pip install` inside the correct venv.
