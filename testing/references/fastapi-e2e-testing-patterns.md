# FastAPI E2E Testing Patterns with TestClient

Patterns for writing end-to-end tests for FastAPI apps using `fastapi.testclient.TestClient`,
covering auth middleware ordering, file uploads, edge cases, and error handling.

## Core Pattern

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestHealthEndpoints:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
```

## Auth Middleware Ordering Gotcha

**Critical:** FastAPI auth middleware runs BEFORE route-level validation.
This means auth errors (401) appear before validation errors (422).

```python
# WRONG: Expecting 422 for missing file
resp = client.post("/api/v1/resume/upload")
assert resp.status_code == 422  # FAILS — returns 401

# CORRECT: Auth middleware blocks first
resp = client.post("/api/v1/resume/upload")
assert resp.status_code in (401, 422)  # 401 is current behavior
```

**Why:** The auth dependency (`Depends(validate_token)`) is evaluated before
the route handler's Pydantic validation. If no token is present, the request
is rejected at the auth layer with 401, never reaching file validation.

**Test implication:** When testing endpoints that require auth + file upload,
you must either:
1. Accept 401 as a valid response (document the behavior)
2. Provide a valid token in the request headers
3. Override the auth dependency in conftest.py for tests that need it

## Providing Auth Tokens in Tests

```python
# Login first to get a token
login_resp = client.post("/api/auth/login", json={
    "username": "testuser",
    "password": "testpass"
})
token = login_resp.json()["access_token"]

# Use token in subsequent requests
resp = client.get("/api/v1/resume/", headers={
    "Authorization": f"Bearer {token}"
})
assert resp.status_code == 200
```

## File Upload Tests

```python
# Upload with actual file content
resp = client.post("/api/v1/resume/upload", files={
    "file": ("resume.pdf", b"fake pdf content", "application/pdf")
})

# Upload with empty file
resp = client.post("/api/v1/resume/upload", files={
    "file": ("empty.pdf", b"", "application/pdf")
})

# Upload without file (auth may block first)
resp = client.post("/api/v1/resume/upload")
# Expect 401 (auth) or 422 (validation) depending on middleware order
```

## Edge Case Testing

### Large Payloads
```python
large_text = "x" * 100000
resp = client.post("/api/v1/internal/n8n/process-resume", json={
    "resume_id": "large-test",
    "text": large_text,
})
assert resp.status_code != 500  # Should not crash
```

### Malformed JSON
```python
resp = client.post(
    "/api/v1/internal/n8n/process-resume",
    content="not json {{{",
    headers={"Content-Type": "application/json"}
)
assert resp.status_code == 422  # Pydantic validation error
```

### Concurrent Requests
```python
for i in range(5):
    resp = client.get("/health")
    assert resp.status_code == 200
```

### Unknown Routes
```python
resp = client.get("/api/v1/nonexistent")
assert resp.status_code == 404
```

### Method Not Allowed
```python
resp = client.delete("/health")
assert resp.status_code == 405
```

## Documenting Bugs in Tests

When you find a bug (e.g., a function raises instead of returning gracefully),
document it in the test with a clear BUG comment:

```python
def test_extract_text_from_pdf_empty_bytes_raises(self):
    """BUG: extract_text_from_pdf raises on empty bytes.

    pypdf.errors.EmptyFileError: Cannot read an empty file

    Should return empty string or raise a handled exception.
    """
    with pytest.raises(Exception):
        extract_text_from_pdf(b"")
```

This turns test failures into bug documentation that can be tracked and fixed.

## Test Organization

For a FastAPI project with `pytest.ini` containing:
```ini
[pytest]
testpaths = api/tests
pythonpath = api
```

- All imports in tests are relative to the `api/` directory
- `from main import app` works (not `from src.api.main import app`)
- `from services.ocr import ...` works (not `from src.services.ocr import ...`)
- `from routes import auth` works (not `from src.routes import auth`)

## Anti-patterns

- Don't test endpoints that require live Postgres/MinIO/Keycloak in E2E tests
  — those belong to Docker Compose integration tests. E2E tests should verify
  the API layer handles missing dependencies gracefully (no 500 errors).
- Don't assume 422 for all validation errors — auth middleware may return 401 first.
- Don't hardcode specific error codes when the behavior may vary — use `in (401, 422)`
  to document current behavior while allowing for future fixes.
- Don't mock the entire app — TestClient exercises the real middleware stack,
  which is the point of E2E testing.
