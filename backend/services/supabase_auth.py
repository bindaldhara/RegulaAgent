"""Verify Supabase-issued JWT access tokens (legacy HS256 or asymmetric JWKS)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from config import get_settings

LEGACY_ALGORITHM = "HS256"
AUDIENCE = "authenticated"
ASYMMETRIC_ALGORITHMS = ["RS256", "ES256", "EdDSA"]


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient | None:
    settings = get_settings()
    base = settings.supabase_url.strip().rstrip("/")
    if not base:
        return None
    return PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json", cache_keys=True)


def _issuer() -> str | None:
    settings = get_settings()
    base = settings.supabase_url.strip().rstrip("/")
    if not base:
        return None
    return f"{base}/auth/v1"


def _decode_hs256(token: str, secret: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        secret,
        algorithms=[LEGACY_ALGORITHM],
        audience=AUDIENCE,
        options={"verify_iss": False},
    )


def _decode_jwks(token: str) -> dict[str, Any]:
    client = _jwks_client()
    issuer = _issuer()
    if client is None or issuer is None:
        raise jwt.PyJWTError("JWKS not configured")
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=ASYMMETRIC_ALGORITHMS,
        audience=AUDIENCE,
        issuer=issuer,
    )


def decode_supabase_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    secret = settings.supabase_jwt_secret.strip()

    if secret:
        try:
            return _decode_hs256(token, secret)
        except jwt.PyJWTError:
            pass

    try:
        return _decode_jwks(token)
    except jwt.PyJWTError:
        return None
