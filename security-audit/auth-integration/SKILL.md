---
name: auth-integration
description: "Multi-platform authentication integration patterns — Keycloak OIDC, JWT token management, auth-wrapper orchestration, full-stack auth implementation."
---

# Auth Integration — Multi-Platform Patterns

## When to Use This Skill

Use when implementing, auditing, or migrating authentication on any platform:
- Setting up Keycloak OIDC + PKCE for browser-based SSO login  
- Integrating with a shared auth-wrapper service (credential management proxy)
- Implementing JWT access tokens + refresh token rotation with JTI revocation  
- Migrating a demo-only auth flow to production-grade authentication
- Adding email OTP flows (verification, password reset) across platforms

## Core Architecture Pattern

```
┌─────────────┐     PKCE code      ┌──────────┐    access_token    ┌─────────────┐
│  Frontend   │ ──────────────────→ │ Keycloak │ ←───────────────→ │  Auth-Wrapper│
│ (SPA/Next.js)│   redirect URI     │ OIDC      │   client_creds    │ (credential  │
│              │ ←───────────────── │ Server    │                   │  proxy)       │  
└──────┬───────┘   auth code        └──────────┘                   │              │
       │                                                            ↓              ↓
       │  POST /api/auth/login/signup ┌──────────────┐            Keycloak         SMTP
       │  → issues local JWT          │   Backend     │───────────────┐             API           OTP
       └← Bearer token + refresh      │ (FastAPI)    ├──introspect───→│             6-digit
         token pair                    └──────────────┘               │              codes
                      ↓                                              │           for verification  
          Stored in localStorage /                                Keycloak realm
              HTTP-only cookie                                     (iacgenie)
```

### Three-Layer Auth Model  
1. **Identity Provider** (Keycloak): User identity, SSO redirect, password storage via auth-wrapper
2. **Auth Wrapper** (shared service): Proxies credential ops to Keycloak, handles ROPC
3. **Platform Backend**: Issues own short-lived JWTs for API auth, manages refresh tokens + OTP

## Keycloak OIDC Setup Checklist
- [ ] Client ID registered in realm with PKCE enabled (S256)  
- [ ] Access Type: `confidential` for backend, or `public` for SPA-only
- [ ] Standard Flow Enabled: ✅ (Authorization Code + PKCE)  
- [ ] Direct Access Grants: ❌ disable if using auth-wrapper (no ROPC)
- [ ] Valid Redirect URIs configured: `https://<domain>/auth/callback` + dev variants  
- [ ] PKCE Code Challenge Method: S256

## Auth Wrapper Integration Patterns
The auth-wrapper is a shared service across all IacGenie platforms. It handles:
- `POST /api/auth/login` — email/password → Keycloak ROPC token exchange  
- `POST /api/auth/signup` — user registration with email verification
- Password hashing (bcrypt) before Keycloak storage

Platform backend should call auth-wrapper for ALL credential ops, NOT manage passwords directly. This is the single source of truth pattern — never store bcrypt hashes in your platform's own database when auth-wrapper exists.

## JWT Token Strategy
- **Access tokens**: HS256, short-lived (900s = 15 minutes), issued by platform backend
- **Refresh tokens**: stored in DB with hashed token, 7-day expiry, rotation on each use
- **JTI revocation**: Each access token gets a unique jti; store in revocation table
- **Token rotation flow**: validate refresh token → revoke old one → issue new pair

## Database Tables Needed
```sql
-- Refresh tokens for rotation tracking  
CREATE TABLE refresh_tokens (id UUID PK, user_id FK, client_id VARCHAR(255),
  token_hash CHAR(64) NOT NULL, expires_at TIMESTAMP WITH TIME ZONE, 
  rotated_from_id UUID REFERENCES refresh_tokens(id), created_at TIMESTAMP);

-- OTP tokens for email verification and password reset
CREATE TABLE otp_tokens (id UUID PK, user_id FK, purpose VARCHAR(50),  -- 'email_verify' or 'password_reset'
  email_hash CHAR(64) NOT NULL, otp_code_hash CHAR(64) NOT NULL,
  expires_at TIMESTAMP WITH TIME ZONE, created_at TIMESTAMP DEFAULT NOW(), used BOOLEAN DEFAULT FALSE);
```

## Frontend Auth Context Pattern (React/Next.js)  
- Store user + token in context provider with localStorage persistence
- On mount: check if token exists, verify via `POST /api/auth/verify`  
- If expired but refresh_token valid: auto-refresh (silent re-auth)
- On 401 from API call: clear tokens, redirect to login with return URL
- `loginWithKeycloak()`: redirects browser to Keycloak PKCE auth page, not a direct API call

## Email OTP Flow  
1. Signup → backend generates 6-digit OTP, stores SHA-256 hash in DB, sends via SMTP
2. User enters OTP → backend verifies against stored hash  
3. Password reset: same flow — user requests, receives OTP email, enters to verify
4. Token expiry for OTP: 10 minutes (configurable)

## Migration Pattern — Demo-Only to Production Auth
Common pattern: frontend has `loginDemo()` bypassing all auth, callback page ignores the auth code.

Steps to fix:
1. Add backend login/signup/refresh endpoints (call shared auth-wrapper)  
2. Fix frontend callback to actually exchange code for tokens
3. Replace `loginDemo()` calls with real backend auth calls in context  
4. Add protected routes (middleware or HOC) that redirect unauthenticated users

## References
- See `references/keycloak-client-setup.md` — Keycloak client configuration checklist  
- See `references/demo-to-production-auth-migration.md` — step-by-step migration guide
- See `references/jwt-token-management-patterns.md` — token rotation, revocation patterns
