# Demo-Only to Production Auth Migration

## Identifying a "Demo-Only" Authentication Setup

Symptoms that indicate demo-only auth:
1. Frontend `login()` or equivalent calls a hardcoded mock function (e.g., `loginDemo()`)
2. Auth callback page ignores the auth code parameter from URL  
3. Backend only has a `/verify` endpoint but no login/signup/refresh endpoints
4. User data stored in localStorage with fake tokens (`"demo-token"` strings)
5. No database tables for refresh_tokens or OTP codes

## Step-by-Step Migration Process

### Phase 1: Backend Auth Endpoints (Foundation)
**Goal**: Add real auth API before touching frontend.

1. Create `api/routes/auth.py` with these endpoints:
   - `POST /login` — email/password login → returns `{access_token, refresh_token}`
   - `POST /signup` — user registration (via auth-wrapper Keycloak ROPC)
   - `POST /refresh` — token refresh with rotation  
   - `POST /logout` — revoke refresh token from DB
   - `GET /config` — return auth capabilities for UI discovery

2. Extend backend service (`services/auth.py`) to call shared `AUTH_WRAPPER_URL` for credential ops:
   ```python  
   async def login_with_credentials(email, password):
       resp = await httpx.post(f"{AUTH_WRAPPER_URL}/api/auth/login", json={email, password})
       return resp.json()  # {token, refresh_token, user}  
   ```

3. Add database tables for `refresh_tokens` and `otp_tokens`.
4. Set `JWT_SECRET`, `JWT_EXPIRATION=900` (15 min), `JWT_REFRESH_EXPIRATION=604800` (7 days).

### Phase 2: Fix Auth Callback
**Goal**: Exchange the Keycloak auth code for real tokens.

Replace this dead-end pattern:
```typescript  
// BEFORE (demo): ignores the code, just creates a fake session
useEffect(() => { loginDemo(); router.push('/dashboard'); }, [code]);

// AFTER (production): exchanges code with backend  
useEffect(() => {
  const code = search.get('code');
  if (code) {
    fetch('/api/v1/auth/keycloak/callback', {  
      method: 'POST', body: JSON.stringify({ code })
    }).then(res => res.json()).then(({ token, refresh_token, user }) => {  
      setCredentials(token, refresh_token, user);
      router.push('/dashboard');
    });  
  } else {
    router.push('/login'); // no code — show error or demo fallback  
  }
}, [code]);
```

### Phase 3: Replace Demo Auth Calls in Context  
**Goal**: All auth paths go through real backend endpoints.

Replace these patterns:
```typescript  
// BEFORE (demo): fake session creation  
const loginDemo = () => { persist("fake-token", { keycloak_id: "demo-user" }); };

// AFTER (production): real login via backend  
const login = async (email, password) => {
  const res = await fetch('/api/v1/auth/login', {  
    method: 'POST', body: JSON.stringify({ email, password })
  });
  if (!res.ok) throw new Error(await res.json().then(r => r.detail));  
  const { token, refresh_token, user } = await res.json();
  persist(token, refresh_token, user);  
};

const loginWithKeycloak = () => {
  // Redirect to Keycloak PKCE flow (already partially working)  
  const keycloakUrl = process.env.NEXT_PUBLIC_KEYCLOAK_URL || 'https://keycloak.iacgenie.com';
  const realm = process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'iacgenie';
  const clientId = process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || 'resume-platform';
  const redirectUri = process.env.NEXT_PUBLIC_REDIRECT_URI || `${window.location.origin}/auth/callback`;
  const state = Math.random().toString(36).substring(2) + Date.now().toString(36);
  const url = `${keycloakUrl}/realms/${realm}/protocol/openid-connect/auth?client_id=${clientId}&response_type=code&redirect_uri=${encodeURIComponent(redirectUri)}&state=${state}`;
  window.location.href = url;  
};
```

### Phase 4: Add Token Auto-Refresh on Stale Tokens  
**Goal**: Transparent refresh when access token expires (15 min) but refresh_token is still valid.

Add to the auth context's `useEffect` on mount:
```typescript  
useEffect(() => {
  const savedToken = localStorage.getItem('resume_token');
  if (savedToken) {  
    // Verify token is still valid
    fetch('/api/v1/auth/verify', { 
      headers: { Authorization: `Bearer ${savedToken}` }
    }).then(res => {  
      if (res.status === 401) { // token expired — try refresh
        const refreshToken = localStorage.getItem('resume_refresh_token');  
        if (refreshToken) {
          fetch('/api/v1/auth/refresh', {
            method: 'POST', body: JSON.stringify({ refresh_token: refreshToken })
          }).then(res => res.json()).then(({ access_token, refresh_token }) => {  
            persist(access_token, refresh_token, user); // rotation
          });
        } else {  
          // No valid refresh — redirect to login  
          router.push('/login?redirect=' + encodeURIComponent(window.location.pathname));
        }
      }
    });  
  }, []);
```

### Phase 5: Add Protected Routes  
**Goal**: Unauthenticated users cannot access dashboard/resume pages.

Option A — Next.js middleware (recommended for App Router):
```typescript  
// middleware.ts in webui root  
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const publicRoutes = ['/login', '/signup', '/', '/templates'];
const protectedPaths = ['/dashboard', '/resume/'];

export function middleware(request: NextRequest) {
  const token = request.cookies.get('resume_token')?.value;  
  if (!token && protectedPaths.some(p => request.nextUrl.pathname.startsWith(p))) {
    return NextResponse.redirect(new URL('/login', request.url));  
  }
  if (!token && publicRoutes.some(r => request.nextUrl.pathname === r)) {  
    return NextResponse.next();
  }  
  return NextResponse.next();
}

export const config = { matcher: ['/dashboard/:path*', '/resume/:path*'] };
```

Option B — ProtectedRoute HOC (for client components):  
See `references/demo-to-production-auth-migration.md` for the full HOC pattern.

### Phase 6: Remove Demo Mode (Cleanup)
**Goal**: No more demo mode in production.

After verifying all auth flows work:  
1. Remove `loginDemo()` from the context provider
2. Replace demo buttons with real auth paths (e.g., "Continue with Keycloak" → `loginWithKeycloak()`)
3. Update any tests that relied on demo mode to use real auth endpoints  
4. Document the new flow in README

## Verification Checklist for Each Phase
- [ ] Backend endpoint returns correct response shape (`{access_token, refresh_token}`)  
- [ ] Frontend stores tokens in localStorage (or cookies for SSR)
- [ ] Token verify endpoint confirms stored token is valid  
- [ ] Stale access token triggers auto-refresh (401 → POST /refresh → new tokens)  
- [ ] Unauthenticated user redirected to login with return URL preserved
- [ ] Logout clears tokens AND calls backend POST /logout (revokes refresh token on server)
