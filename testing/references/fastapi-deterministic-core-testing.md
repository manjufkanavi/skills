# Testing FastAPI Apps Without Live External Services

Pattern for writing tests for a FastAPI (or Flask) app whose external
dependencies (Postgres, MinIO, Keycloak, Ollama, etc.) are **not available** in
the test environment. Two layers:

1. **Deterministic core** — import the business-logic functions directly and call
   them with crafted inputs. No server, no DB, no network.
2. **Route-registration smoke test** — import the app and assert endpoints are
   wired up (see below).

## Why importing the app is safe

Importing `from main import app` (or constructing `FastAPI(...)`) only **registers**
routes and middleware. A `@app.on_event("startup")` handler is *registered*, not
*run* — so a startup event that does `create_all()` on a real Postgres engine does
**not** execute on import. You can inspect `app.routes` without a live DB.
(Only start the app via `TestClient`/uvicorn if you need the startup path to run.)

## Route-registration smoke test

```python
from main import app

EXPECTED = ["/health", "/api/v1/auth/verify", "/api/v1/resume/upload", ...]

def _paths():
    return {r.path for r in app.routes if hasattr(r, "path")}

def test_routes_registered():
    missing = [p for p in EXPECTED if p not in _paths()]
    assert not missing, f"missing routes: {missing}"
```

Inspect a handler's declared params with `inspect.signature` (NOT
`endpoint.__signature__`, which plain functions lack):

```python
import inspect
route = next(r for r in app.routes if getattr(r, "path", "") == "/api/v1/resume/upload")
params = inspect.signature(route.endpoint).parameters
assert "file" in params and "job_title" in params
```

## Testing deterministic business logic

Import the service functions and call them with crafted inputs so tests don't
depend on live MinIO/Ollama/Keycloak:

```python
from services.ats import calculate_ats_score

def test_scores_bounded():
    score = calculate_ats_score({"sections": {...}, "raw_text": "..."}, "software engineer")
    assert 0 <= score["overall"] <= 100
```

For serialization formats with version drift (e.g. python-docx), serialize via
`BytesIO` + `save()` rather than a version-specific method like `.pack()`:

```python
import io
from docx import Document
buf = io.BytesIO(); Document().save(buf); blob = buf.getvalue()
```

## Making intra-package imports resolve

Apps often use relative imports (`from routes import ...`,
`from services.ats import ...`). Two ways to make them importable from tests:

- **conftest.py** adds the package dir to `sys.path`:
  ```python
  import os, sys
  sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # api/ dir
  ```
- **pytest.ini** `pythonpath = api` (pytest ≥7) with `testpaths = api/tests`.

## Anti-patterns

- Don't test endpoints that require live Postgres/MinIO/Keycloak/Ollama in unit
  tests — those belong to Docker Compose integration tests (see the main
  testing skill). Unit-test the deterministic logic; integration-test the wiring.
- Don't hardcode session-specific quirks (e.g. one app's section-detection rules)
  into a class-level skill — capture the *technique*, not the app's data.

See Also: `references/docker-compose-integration-testing.md` (when services *are*
available) and the main testing skill, section 4.
