"""Shared Keycloak JWT auth dependency for all MCP servers."""
from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
import httpx

KEYCLOAK_ISSUER   = os.environ.get("KEYCLOAK_ISSUER", "https://auth.ai.adports.ae/realms/ai-portal")
KEYCLOAK_AUDIENCE = os.environ.get("KEYCLOAK_AUDIENCE", "portal-api")

_bearer = HTTPBearer()
_jwks_cache: Optional[dict] = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs")
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
        key = next((k for k in jwks["keys"] if k.get("kid") == headers.get("kid")), None)
        if key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown key")
        public_key = jwk.construct(key)
        return jwt.decode(
            token, public_key, algorithms=["RS256"],
            audience=KEYCLOAK_AUDIENCE, issuer=KEYCLOAK_ISSUER,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
