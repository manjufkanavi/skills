
# Platform Auth Analysis — Systematic Method

Analyze an existing platform's authentication implementation and create a migration plan for another platform. Covers understanding Keycloak OIDC, JWT tokens, auth-wrapper integration, and multi-platform shared infrastructure patterns.

---

## Phase 1: Locate the Codebase

Determine where both platforms live — source of truth, deployed code, and infrastructure config.

```bash
# Find the platform on VM (deployed state) — use short timeouts, read small files first
ssh -o ConnectTimeout=10 <user>@<vm-ip> "find /home/<user>/docker -name 'auth*' 2>/dev/null | head"

# Find the platform in Ansible roles (source of truth — authoritative)
find ~/iacgenie-platform/infra -path "*<platform>*" -name "*.py" 2>/dev/null | grep auth

# Find frontend source (varies by framework)
find ~/iacgenie-platform -path "*frontend*" -name "*.tsx" 2>/dev/null | grep -i "login\|auth\|signin\|signup"
```

**Pitfalls:**
- VM is extremely slow (~65KB/s) — use `ConnectTimeout=10`, batch SSH commands with echo separators, read small files first
- Ansible role files are the **source of truth** — deployed VM state may diverge from manual patches
- Frontend location varies: `platform/frontend/` (Vite), `webui/src/app/` (Next.js App Router)
- Auth logic scattered across files — search broadly: `routes/auth.py`, `routers/` modules, `services/`, middleware

## Phase 2: Backend Auth Audit (4-step)

Read the backend in this order to understand the full auth flow:

### 2.1 Routes (`routes/auth.py` or `routers/`)
Read the full file. Extract every endpoint into a table:

| Endpoint | Method | Description | Auth Required? |
|----------|--------|-------------|----------------|

**Look for these patterns:**
- **Unified endpoint with `action` param**: `/api/auth/token` accepts login/signup/reset/verify (IacGenie pattern)
- **Separate endpoints per operation**: individual `/login`, `/signup` routes (resume platform pattern)
- **Keycloak OAuth2/OIDC with PKCE**: `GET /keycloak/login` → redirect, then `/keycloak/callback?code=XXX` (exchange code for tokens)
- **Google/GitHub SSO via Keycloak IDPs**: `/google`, `/github` routes that redirect to Keycloak with `idp_hint=`
- **Email OTP flow**: endpoints for forgot-password, verify-otp, reset-with-otp

### 2.2 Auth Service (`services/auth.py` or similar)
Read the service layer. Extract every function and its external dependencies:

| Function | What it does | External dependency? |
|----------|-------------|---------------------|

**Key questions to answer:**
- Does the platform use **auth-wrapper** for credential management? → YES means no local password/bcrypt logic needed (shared service handles Keycloak ROPC)
- Does the platform issue its **own JWT tokens** after external auth? → YES means HS256 local JWTs with short expiry (15 min access, 7 day refresh)
- Does the platform use **Keycloak introspection** as fallback when auth-wrapper is down? → Dual validation path = more resilient
- Are tokens stored in a **database** (refresh_tokens table)? → Determines if refresh rotation is supported
- Is there a **JTI revocation store**? → Indicates production-grade token management

### 2.3 Database Schema (`database.py` or `models/`)
Check which auth-related tables exist and their capabilities:

| Table | Purpose | Auth Level Implied |
|-------|---------|-------------------|
| `users` (with keycloak_id) | Local user records synced from Keycloak, no local passwords | Basic — external auth only |
| `refresh_tokens` (with token_hash, expires_at) | Refresh token rotation tracking with chain of rotations | Production-grade — supports refresh flow |
| `otp_tokens` (with purpose, otp_code_hash) | Email verification + password reset OTPs with expiry | Full auth — supports email flows |
| `auth_audit_logs` (with event_type, user_id) | Security audit trail for login/logout/token events | Enterprise-grade — compliance ready |
| `users` (with hashed_password) | Local password storage with bcrypt/argon2 | Legacy/simple — no Keycloak integration |

**Pitfalls:**
- Database URL in `database.py` may point to Docker internal hostname (`postgres:5432`) — works on VM via Docker networking but breaks in local development
- If only a single `users` table exists with no refresh_tokens or otp_tokens, the platform lacks token rotation and email verification — these are **gaps to address in migration**
- `NullPool` connection pool (from SQLAlchemy) means no persistent connections — fine for stateless APIs but check timeout settings

### 2.4 Middleware (`middleware/auth.py` or `middleware/`)
Check how requests are protected and tokens validated:

| Pattern | Description | Auth Level |
|---------|-------------|-----------|
| `verify_token(request)` → Decoded JWT claims | Extracts Bearer token, verifies HS256 signature, checks JTI revocation against store | Production-grade |
| `require_admin(token)` → Role check from JWT claims | Checks role against admin list, returns 403 if insufficient | RBAC support |
| `get_user_id(token)` → User ID extraction via DI | Simple dependency injection for route handlers that need the user ID | Basic auth pattern |
| No middleware — manual `Bearer` header check in each endpoint | Every protected route manually extracts and validates token | Basic — error-prone, inconsistent across endpoints |

**Check for:**
- **JTI (JWT ID) revocation checking in middleware** — production-grade token management; tokens can be invalidated server-side
- **Grace secrets support (`_decode_token_with_grace()`)** — allows key rotation without invalidating existing tokens
- **Token expiration check in middleware vs. client-side only** — server-side expiry prevents expired tokens from being used

## Phase 3: Frontend Auth Audit (4-step)

### 3.1 Pages (`src/app/*/page.tsx` or `pages/`)
List all auth-related pages and assess their real functionality:

| Page | Path | Functionality | Auth Level |
|------|------|---------------|-----------|

**Critical check:** Does the login page call a **real auth function** or just `loginDemo()`?
- If it calls demo mode (`loginDemo()`, no API call, just sets localStorage with fake data) — the entire frontend auth flow is a **no-op**. Users never get tokens.
- If it calls `loginWithKeycloak()` — check if the callback page actually exchanges the code, or also just calls demo mode. This is a **dead-end SSO** pattern (found in resume platform).

### 3.2 Auth Context/Store (`contexts/auth-context.tsx` or `store/useAuthStore.ts`)
Read the auth state management. Extract:

| Pattern | Description | Auth Level |
|---------|-------------|-----------|

**Key questions:**
- On mount, does the auth context **verify/refresh stale tokens**? → If not present: users get 401 errors after page reload when their access token expired (JWT default expiry is usually short)
- Is there a `refreshIfExpired()` function that attempts token refresh before redirecting to login? → Indicates graceful handling of stale sessions
- Does `loginWithKeycloak()` actually work (builds correct PKCE URL) or is it a dead end? → If the function builds a Keycloak redirect URL but no backend endpoint exists to exchange the returned code for tokens, SSO is broken

### 3.3 API Client (`lib/api.ts` or `services/`)
Check how authenticated requests are made and error handling:

| Pattern | Description | Auth Level |
|---------|-------------|-----------|

### 3.4 Route Protection (`components/ProtectedRoute.tsx` or middleware)
Check how protected routes are guarded:

| Pattern | Description | Auth Level |
|---------|-------------|-----------|

**Key patterns:**
- **HOC with auto-refresh**: `<ProtectedRoute>` wraps pages, checks auth on mount, attempts token refresh if expired before redirecting to login (IacGenie pattern)
- **Next.js middleware**: Route-level auth guard in `middleware.ts` — runs on server before page render, redirects unauthenticated users to `/login`. Better for SSR/ISR apps.
- **No route protection**: All pages accessible, backend returns 401 on API calls when unauthenticated → UX is broken (user can navigate to dashboard but gets errors)
- **Manual check in each page**: `if (!isAuthenticated) return <Navigate to="/login" />` — fragmented, easy to miss on new pages

## Phase 4: Infrastructure Integration Audit

### 4.1 Keycloak Configuration
Check how the platform connects to Keycloak:

| Config | Where Found | Auth Level |
|--------|------------|-----------|

**Check for:** PKCE enabled (`S256` code challenge method), redirect URIs matching frontend paths, Keycloak client ID per platform (but same realm).

### 4.2 Auth-Wrapper Integration
Check if the platform uses the shared auth-wrapper service:

| Pattern | Description | Auth Level |
|---------|-------------|-----------|

**Key insight:** When multiple platforms share auth-wrapper, credential management (password hashing via bcrypt, Keycloak ROPC) is a **single source of truth**. Each platform just calls the auth-wrapper endpoints and adds its own JWT layer on top. This eliminates duplicate password logic across platforms.

### 4.3 Nginx Configuration
Check how the platform is exposed and which endpoints go through auth-wrapper vs. direct backend:

| Route Pattern | Proxy Target | Auth Level |
|--------------|-------------|-----------|

**Critical routing rule:** `/api/v1/auth/*` (login, signup) must go to **backend directly** — auth-wrapper does NOT handle credential operations. `/api/v1/resume/*` (resource APIs) goes through auth-wrapper for token validation. Mixing these up causes 403 errors.

## Phase 5: Create Migration Plan

With findings from Phases 1-4, create a structured plan. Use this template:

```markdown
# <Target Platform> Auth Integration Plan (modeled after <Source Platform>)

## Current State Analysis
| Component | Status | Issues Found |

## Target Backend Endpoints (what to add)
- POST /api/v1/auth/login — ...

## Target Frontend Pages (what to create/modify)
- /login → Full login form (replace demo-only)

## Infrastructure Changes Needed
- Keycloak client: register/verify ...
- Auth-wrapper: ensure configured for <target-platform>

## Environment Variables to Add/Update
```env
KEYCLOAK_URL=...
AUTH_WRAPPER_URL=http:/...

## Timeline Summary
| Phase | Duration | Dependencies |
```

**Decision points to address:**
1. **Auth wrapper vs direct Keycloak** — Always prefer auth-wrapper for consistency across platforms
2. **Token storage** — HTTP-only cookies (recommended, XSS resistant) vs localStorage (easier but less secure). Cookies recommended for Next.js.
3. **JWT issuer/audience** — Each platform should have unique `JWT_ISSUER` and `JWT_AUDIENCE` to prevent token confusion
4. **Demo mode** — Keep for testing/preview if useful, but make it clearly separated from production auth

## Key Patterns to Replicate (from IacGenie)

### Pattern 1: Unified Auth Backend
```python
class AuthService:
    def __init__(self): self.provider = create_auth_provider(os.getenv("AUTH_PROVIDER"))

# The provider (KeycloakAuthProvider) handles Keycloak REST API.
# AuthService is a thin wrapper — easy to swap providers (local, keycloak).
```

### Pattern 2: Local JWT After External Auth + Refresh Rotation
```python
# Access token (15 min, short-lived) — used for API authorization  
access_token = generate_token(user_id, email, role)

# Refresh token (7 days, long-lived) — stored hashed in DB for rotation
plain_refresh, refresh_meta = generate_refresh_token(user_id)
await db_adapter.create_refresh_token(refresh_meta)

# On refresh: revoke old, issue new (rotation prevents replay attacks)
await db_adapter.revoke_refresh_token_by_hash(old_hash)  # rotation step
new_access, (new_plain, new_meta) = generate_token(...), generate_refresh_token(...)
await db_adapter.create_refresh_token(new_meta)
```

### Pattern 3: Frontend Auth Context with Auto-Refresh on Stale Tokens
```typescript
// Zustand auth store persisted to localStorage, auto-restored on mount:
const useAuthStore = create<AuthState>()(persist(..., { name: 'resume-auth' }));

// On mount: verify token is valid; if expired, attempt refresh before redirecting
useEffect(() => { const token = getStorage(TOKEN_KEY); if (token && isTokenExpired(token)) refreshToken(); }, []);
```

### Pattern 4: Protected Route HOC with Loading State + Auto-Refresh
```typescript
// Checks auth before rendering, shows spinner while verifying. Refreshes stale tokens automatically.
export const ProtectedRoute = ({ children }) => { useEffect(() => checkAuth(), []); return isChecking ? <Loading /> : children; };
```

## Pitfalls to Avoid (from this session)

1. **Demo-only auth pages** — If the login page calls `loginDemo()` instead of real backend endpoints, the entire auth flow is a no-op. Always verify: does this page actually call an API?
2. **Dead-end SSO redirects** — If `loginWithKeycloak()` builds a Keycloak URL but the callback page ignores it (just calls demo), SSO is broken. The callback MUST exchange the auth code for tokens via a backend endpoint.
3. **Missing token refresh** — If the frontend stores JWTs but has no `refreshIfExpired()` logic, users get 401 errors after page reload. Always implement auto-refresh or use HTTP-only cookies with server-side sessions.
4. **Auth-wrapper URL mismatch** — The auth-wrapper service runs on a specific port (9096 in the unified stack). Backend services must use the correct URL (`http://127.0.0.9:9096` for nginx proxy access, `http://auth-wrapper:9096` for Docker internal). Verify with `curl http://127.0.0.9:9096/health` before writing code that depends on it.
5. **Nginx proxy routing for auth endpoints** — Auth endpoints (login, signup) must go to the backend directly (port 3006), not through auth-wrapper. Auth-wrapper only validates tokens on resource API calls (`/api/v1/resume/*`). Mixing these up causes 403 errors because auth-wrapper doesn't handle login/signup.
