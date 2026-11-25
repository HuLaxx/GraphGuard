# ADR 007: JWT Authentication Strategy

**Status:** Accepted  
**Date:** 2026-01-22

## Context

Sentinance needs authentication for:
- Protected API endpoints (alerts, user preferences)
- Rate limiting by user tier
- Audit logging

## Decision

Use **JWT (JSON Web Tokens)** with:
- Short-lived access tokens (30 minutes)
- Refresh token rotation
- bcrypt password hashing

## Token Structure

```python
{
    "sub": "user-uuid",
    "email": "user@example.com",
    "is_premium": false,
    "exp": 1706000000,
    "iat": 1706000000
}
```

## Implementation

```python
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=30)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

## Consequences

### Positive
- Stateless (no session storage needed)
- Works with load balancing
- Self-contained user info

### Negative
- Token revocation requires blocklist
- Larger than session cookies

## Security Considerations

- JWT_SECRET must be 256+ bits
- Never store in localStorage (use httpOnly cookies)
- Validate `exp` claim on every request
