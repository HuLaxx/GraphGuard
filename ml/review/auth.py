"""Short-lived HMAC-signed local demo reviewer identity (not production IAM).

The verifier NEVER trusts an unsignatured actor/role supplied in a request.
Tokens are minted only by an offline operator holding the signing secret.
Use external OIDC, rotation and revocation for any production service.
"""
import base64
import hashlib
import hmac
import json
import re
import secrets
import time

ISSUER = "graphguard-local-demo-v1"
AUDIENCE = "graphguard-synthetic-case-review"
ROLES = frozenset({"analyst", "admin"})
MAX_TTL = 3600
USER_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,63}$")


class ReviewAuthError(PermissionError):
    pass


def checked_key(raw: str, label: str) -> bytes:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) < 32:
        raise ReviewAuthError(f"{label} must be at least 32 bytes, injected privately")
    if raw.encode("utf-8") in (b"x" * 32, b"0" * 32):
        raise ReviewAuthError(f"{label} uses a deliberately weak placeholder")
    return raw.encode("utf-8")


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", value):
        raise ReviewAuthError("Invalid token encoding")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error) as error:
        raise ReviewAuthError("Invalid token encoding") from error
    if _encode(decoded) != value:
        raise ReviewAuthError("Noncanonical token encoding")
    return decoded


def issue_demo_token(key: bytes, *, subject: str, role: str, ttl: int = 600,
                     now: int | None = None) -> str:
    """Operator-side only: never expose token-minting via review HTTP API."""
    if len(key) < 32:
        raise ReviewAuthError("Signing key too short")
    if not isinstance(subject, str) or not USER_RE.fullmatch(subject):
        raise ReviewAuthError("Invalid demo reviewer ID")
    if role not in ROLES or type(ttl) is not int or not 1 <= ttl <= MAX_TTL:
        raise ReviewAuthError("Invalid reviewer role or token lifetime")
    clock = int(time.time()) if now is None else now
    header = {"alg": "HS256", "typ": "GG-DEMO"}
    claims = {
        "iss": ISSUER, "aud": AUDIENCE,
        "sub": subject, "role": role, "iat": clock,
        "exp": clock + ttl, "jti": secrets.token_hex(12),
    }
    unsigned = ".".join(
        _encode(json.dumps(item, sort_keys=True, separators=(",", ":")).encode())
        for item in (header, claims)
    )
    signature = _encode(hmac.new(key, unsigned.encode("ascii"), hashlib.sha256).digest())
    return unsigned + "." + signature


def verify_demo_token(key: bytes, token: str, *, now: int | None = None) -> dict:
    if len(key) < 32:
        raise ReviewAuthError("Signing key too short")
    if not isinstance(token, str) or len(token) > 2048 or token.count(".") != 2:
        raise ReviewAuthError("Missing or malformed reviewer token")
    first, second, signature = token.split(".")
    unsigned = f"{first}.{second}"
    expected = hmac.new(key, unsigned.encode("ascii"), hashlib.sha256).digest()
    if not hmac.compare_digest(_decode(signature), expected):
        raise ReviewAuthError("Invalid reviewer signature")
    try:
        header = json.loads(_decode(first))
        claims = json.loads(_decode(second))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise ReviewAuthError("Malformed reviewer claims") from error
    if header != {"alg": "HS256", "typ": "GG-DEMO"} or not isinstance(claims, dict):
        raise ReviewAuthError("Unsupported reviewer token")
    if set(claims) != {"iss", "aud", "sub", "role", "iat", "exp", "jti"}:
        raise ReviewAuthError("Unexpected reviewer claims")
    clock = int(time.time()) if now is None else now
    if (
        claims["iss"] != ISSUER or claims["aud"] != AUDIENCE
        or not isinstance(claims["sub"], str)
        or not USER_RE.fullmatch(claims["sub"])
        or claims["role"] not in ROLES
        or type(claims["iat"]) is not int or type(claims["exp"]) is not int
        or not isinstance(claims["jti"], str)
        or not re.fullmatch(r"[a-f0-9]{24}", claims["jti"])
        or claims["iat"] > clock + 30 or claims["exp"] <= clock
        or not 0 < claims["exp"] - claims["iat"] <= MAX_TTL
    ):
        raise ReviewAuthError("Expired, future-dated or unauthorized reviewer")
    return {"subject": claims["sub"], "role": claims["role"], "jti": claims["jti"]}
