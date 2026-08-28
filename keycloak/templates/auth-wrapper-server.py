"""
Shared Auth Wrapper v2 — FastAPI-based unified auth gateway for ClamAV, CrowdSec, PageGen.

Routes requests through Keycloak OIDC authentication via token introspection,
then forwards to the configured backend based on the X-Service header.
"""
import os, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

KEYCLOAK_URL = os.getenv("AUTH_KEYCLOAK_URL", "http://keycloak:8080")
REALM = os.getenv("AUTH_REALM", "iacgenie")
CLIENT_ID = os.getenv("AUTH_CLIENT_ID", "auth-wrapper")
CLIENT_SECRET=os.getenv("AUTH_CLIENT_SECRET", "CHANGE_ME")
INTERNAL_TOKEN=os.getenv("AUTH_INTERNAL_TOKEN", "CHANGE_ME")
USER_HEADER = os.getenv("AUTH_USER_HEADER", "X-Auth-User")

KC_INTROSPECT_URL = f"{KEYCLOAK_URL}/protocol/openid-connect/token/introspection"
app = FastAPI(title="Shared Auth Wrapper")

_token_cache: dict = {}
_CACHE_FILE = Path("/app/.token_cache.json")


def _load_token_cache() -> dict:
    try:
        data = json.loads(_CACHE_FILE.read_text())
        expired = [k for k, v in data.items() if datetime.now(timezone.utc) > v.get("expires_at", datetime.min)]
        for k in expired:
            del data[k]
        return data
    except Exception:
        return {}


def _save_token_cache() -> None:
    try:
        _CACHE_FILE.write_text(json.dumps(_token_cache))
    except Exception:
        pass


_token_cache.update(_load_token_cache())


async def _validate_jwt(token: str) -> dict:
    """Validate via Keycloak introspection endpoint."""
    async with httpx.AsyncClient(timeout=10) as c:
        resp = await c.post(KC_INTROSPECT_URL, data={"token": token, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET})
        data = resp.json()
        if not data.get("active"):
            raise HTTPException(401, "Token inactive or expired")
        return data


async def _extract_token(request: Request) -> str:
    auth_hdr = request.headers.get("Authorization", "")
    if auth_hdr.startswith("Bearer "):
        return auth_hdr[7:]
    cookie = request.cookies.get("auth_wrapper_token")
    if cookie:
        return cookie
    raise HTTPException(401, "Authentication required")


@app.post("/internal/validate")
async def internal_validate(request: Request):
    """Validate requests from Nginx using the internal token."""
    if request.headers.get("X-Internal-Token") != INTERNAL_TOKEN:
        raise HTTPException(401, "Invalid internal token")
    token = request.headers.get("X-Forwarded-Token")
    service = request.headers.get("X-Service", "unknown")
    if not token:
        raise HTTPException(401, "No token provided")
    try:
        payload = await _validate_jwt(token)
    except HTTPException:
        raise
    return JSONResponse({"status": "authorized", "user": payload.get("preferred_username", payload.get("sub", "unknown")), "service": service})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth-wrapper"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(request: Request, path: str):
    """Authenticate via Bearer token, then proxy to the target service."""
    token = await _extract_token(request)
    try:
        payload = await _validate_jwt(token)
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    service_dest = request.headers.get("X-Service")
    if not service_dest:
        raise HTTPException(400, "X-Service header required")
    backend_url = f"http://{service_dest}/{path}"
    headers = dict(request.headers)
    headers["X-Auth-User"] = payload.get("preferred_username", payload.get("sub", ""))
    headers.pop("cookie", None)
    headers.pop("authorization", None)
    async with httpx.AsyncClient(timeout=30) as client:
        method = request.method
        body = await request.body()
        resp = await client.request(method, backend_url, headers=headers, content=body)
    return JSONResponse(content=resp.content, status_code=resp.status_code, headers={k: v for k, v in resp.headers.items() if k.lower() not in ("transfer-encoding", "content-encoding")})
