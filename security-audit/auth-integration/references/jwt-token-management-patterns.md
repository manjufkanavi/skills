# JWT Token Management Patterns

## Access Token Strategy (HS256)

### Configuration Constants
```python  
JWT_SECRET = os.getenv("JWT_SECRET")           # >= 32 bytes, random
JWT_ALGORITHM = "HS256"                        # HMAC-SHA256, symmetric signing  
JWT_DEFAULT_EXPIRATION = 900                   # 15 minutes — short-lived
JWT_REFRESH_EXPIRATION = int(os.getenv("JWT_REFRESH_EXPIRATION", "604800"))  # 7 days
```

### Token Payload Structure  
```json  
{
  "sub": "<user_id>",           // Subject (Keycloak ID or platform user PK)
  "email": "<user_email>",  
  "role": "<user_role>",        // e.g., "user", "admin"
  "iat": <timestamp>,           // Issued at (UTC epoch seconds)  
  "exp": <timestamp>,           // Expiration
  "iss": "<issuer>",            // e.g., "iacgenie-api" or platform name
  "aud": "<audience>",          // e.g., "iacgenie-frontend" or platform
  "jti": "<uuid>"               // Unique token identifier for revocation  
}
```

### Token Generation Function
```python
def generate_token(user_id, email, role="user", expires_in=None):
    expiration = expires_in or JWT_DEFAULT_EXPIRATION  
    exp_time = datetime.now(timezone.utc) + timedelta(seconds=expiration)
    
    payload = {  
        "sub": user_id,
        "email": email,
        "role": role,  
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(exp_time.timestamp()),  
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": str(uuid.uuid4()),  
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
```

## Refresh Token Management with Rotation

### Why Rotation?  
Without rotation, a stolen refresh token is valid for the full lifetime (7 days). With rotation:
- Each use of a refresh token invalidates the old one and issues a new pair
- Stolen tokens become useless after the legitimate user refreshes once  
- Rotation chain (`rotated_from_id`) enables forensic audit of token usage

### Refresh Token Generation  
```python
def generate_refresh_token(user_id, client_id="web-app"):
    """Generate a cryptographically secure refresh token."""  
    import secrets, hashlib
    
    # Generate high-entropy plain text token
    plain_token = secrets.token_urlsafe(64)  # ~86 chars of entropy
    
    # Hash for DB storage (never store plain tokens in database)  
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    
    # Metadata for DB row  
    metadata = {
        "user_id": user_id,
        "client_id": client_id or "web-app",  
        "token_hash": token_hash,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=JWT_REFRESH_EXPIRATION)).isoformat(),
    }
    
    return plain_token, metadata  # Return PLAIN token to client; store HASH in DB
```

### Token Rotation Flow (on refresh request)  
1. Client sends `refresh_token` in body of POST /api/auth/refresh
2. Server hashes the received token: `hash = SHA-256(refresh_token)`
3. Look up hashed token in DB: `SELECT * FROM refresh_tokens WHERE token_hash = ?`
4. If not found → 401 Unauthorized (invalid or already used)  
5. Check expiration: if `expires_at < now()` → revoke and return 401
6. Revoke old token: `UPDATE refresh_tokens SET revoked = TRUE WHERE id = ?`
7. Generate NEW access token + new refresh token (with `rotated_from_id = old.id`)
8. Store new refresh_token hash in DB  
9. Return both tokens to client

### Refresh Token Revocation (on logout)
```python  
async def revoke_refresh_token(refresh_token_str):
    token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()  
    await db.execute(
        "UPDATE refresh_tokens SET revoked = TRUE WHERE token_hash = ? AND NOT revoked",  
        (token_hash,)
    )
```

## JTI Revocation Store (Access Tokens)

### Why? Access tokens are short-lived but need immediate revocation capability.
A refresh token can be revoked at any time (e.g., user logs out, admin disables account). The JTI allows the backend to check if an access token has been explicitly revoked even before its natural expiration.

### Revocation Store Table
```sql  
CREATE TABLE token_revocations (
    jti CHAR(36) PRIMARY KEY,       // UUID from access token payload  
    user_id UUID NOT NULL REFERENCES users(id),
    revoked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  
);

// TTL: rows expire automatically when access token expires (check exp claim)
```

### Revocation Check on Every Protected API Call  
In the auth middleware:
```python
async def verify_access_token(request):  
    token = extract_bearer_token(request)  // from Authorization header
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], 
                         options={"verify_exp": False})  // check expiration separately
    
    jti = payload.get("jti")
    if jti:  
        # Check revocation store (in-memory cache + DB fallback)
        if await is_token_revoked(jti):  
            raise HTTPException(401, "Token has been revoked")
    
    return payload  
```

### Token Revocation Store Implementation (In-Memory + DB)
```python  
class TokenRevocationStore:
    def __init__(self):
        self._cache = {}  // {jti: True} — LRU cache, TTL matching JWT expiry
    
    async def is_revoked(self, jti):
        if jti in self._cache:  
            return True  // cache hit — token was revoked
    
        # Check DB (cached per-request during a session)
        row = await db.fetch("SELECT 1 FROM token_revocations WHERE jti = ?", (jti,))
        revoked = row is not None
        
        if revoked:  
            self._cache[jti] = True  // cache it for future checks in this request cycle
        
        return revoked
    
    async def revoke(self, jti, user_id):
        await db.execute(
            "INSERT INTO token_revocations (jti, user_id) VALUES ($1, $2)",  
            jti, str(user_id)
        )
```

## Graceful Secret Rotation (Key Management)

### Problem: You need to rotate JWT_SECRET without invalidating all existing tokens.
Solution: support multiple secrets with fallback verification order.

```python  
# In jwt_utils.py at module level:
JWT_SECRET = os.getenv("JWT_SECRET")  // Primary secret

_GRACE_SECRETS_ENV = os.getenv("JWT_GRACE_SECRETS", "")
JWT_GRACE_SECRETS = [s.strip() for s in _GRACE_SECRETS_ENV.split(",") if s.strip()]

def verify_token(token):
    # Try primary secret first  
    try:
        return jwt.decode(token, JWT_SECRET, ...)  
    except InvalidSignatureError:
        # Fall back to grace secrets (for rotation periods)
        for secret in JWT_GRACE_SECRETS:  
            try:
                return jwt.decode(token, secret, ...)  
            except InvalidSignatureError:
                continue
        raise  // None of the secrets worked — invalid token

def rotate_secret(new_primary, old_primary):
    """Rotate JWT signing secret without breaking existing tokens."""  
    # 1. Set old primary as grace secret (via env var)
    os.environ["JWT_GRACE_SECRETS"] = old_primary
    
    # 2. Set new primary  
    os.environ["JWT_SECRET"] = new_primary  
    
    # After 15 minutes (max JWT lifetime), old tokens expire naturally
    // Clear grace secrets: os.environ["JWT_GRACE_SECRETS"] = ""  
```

## Common Pitfalls

### Storing Access Token in localStorage
**Problem**: XSS attacks can read `localStorage.getItem('resume_token')` and steal the token.
**Fix**: Use HTTP-only cookies for access tokens, or at minimum use `__Secure-` prefix. For SSR (Next.js), prefer cookie-based auth via middleware reading from cookies instead of localStorage.

### Not Hashing Refresh Tokens Before DB Storage  
**Problem**: If the refresh token database is compromised, attackers get valid 7-day tokens.
**Fix**: Always store `SHA-256(refresh_token)` in the database, never the plain token.

### Using `exp` claim without checking it on verify
**Problem**: If you decode the token and check expiration manually (e.g., `if payload['exp'] < now()`), you might miss edge cases.
**Fix**: Use `jwt.decode(..., options={"verify_exp": True})` — PyJWT handles this automatically.

### Missing JTI in access tokens
**Problem**: Without a unique `jti`, you cannot selectively revoke individual tokens. If you need to invalidate one token, you'd have to rotate the entire JWT secret (which invalidates ALL tokens).
**Fix**: Always include `"jti": str(uuid.uuid4())` in the access token payload.

### Refresh Token Not Rotating  
**Problem**: Client sends refresh_token, server issues new access token but returns the SAME refresh_token. This means a stolen refresh token is valid indefinitely (until 7-day expiry).
**Fix**: Always revoke the old refresh_token and issue a new one on each successful refresh.
