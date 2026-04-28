"""JWT authentication dependency — validates Keycloak RS256 tokens."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt

import httpx
from app.config import settings

_bearer = HTTPBearer()
_jwks_cache: Optional[dict] = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.keycloak_issuer}/protocol/openid-connect/certs")
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        headers = jwt.get_unverified_header(token)
        key = next(
            (k for k in jwks["keys"] if k.get("kid") == headers.get("kid")), None
        )
        if key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown signing key")
        public_key = jwk.construct(key)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer,
        )
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
