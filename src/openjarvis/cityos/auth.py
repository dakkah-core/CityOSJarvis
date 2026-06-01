"""Keycloak OIDC/JWT authentication middleware for CityOS.

Replaces OpenJarvis's simple API-key auth with Keycloak JWT validation,
including tenant claim extraction and RBAC role passthrough.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
import jwt as pyjwt
from jwt import PyJWKSet
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class CityOSAuthMiddleware(BaseHTTPMiddleware):
    """Validates Keycloak JWT tokens on all /v1/* and /api/* routes.

    Expects the BFF gateway to forward the user's JWT via:
        Authorization: Bearer <keycloak_jwt>
        X-CityOS-Tenant-Id: <tenant_uuid>

    Falls back to the original OpenJarvis API key if Keycloak is not
    configured (for local development).
    """

    def __init__(self, app: Any, api_key: str = "") -> None:  # noqa: ANN401
        super().__init__(app)
        self._api_key = api_key or os.environ.get("OPENJARVIS_API_KEY", "")
        self._keycloak_url = os.environ.get("KEYCLOAK_URL", "")
        self._keycloak_realm = os.environ.get("KEYCLOAK_REALM", "cityos")
        self._jwks: dict[str, Any] | None = None
        self._jwks_client: httpx.AsyncClient | None = None

    async def dispatch(self, request: Request, call_next: Any) -> Any:  # noqa: ANN401
        path = request.url.path

        # Exempt health checks and webhook routes
        if not self._requires_auth(path):
            return await call_next(request)

        # Try Keycloak JWT first (CityOS mode)
        if self._keycloak_url:
            result = await self._validate_keycloak(request)
            if result is not None:
                return result

        # Fallback to legacy API key (OpenJarvis standalone mode)
        if self._api_key:
            result = self._validate_api_key(request)
            if result is not None:
                return result

        return await call_next(request)

    def _requires_auth(self, path: str) -> bool:
        exempt = {"/health", "/v1/health", "/api/health"}
        if path in exempt:
            return False
        if path.startswith("/v1/") or path.startswith("/api/"):
            return True
        return False

    async def _validate_keycloak(self, request: Request) -> Any | None:  # noqa: ANN401
        auth = request.headers.get("Authorization", "")
        if not auth:
            return JSONResponse(
                {"detail": "Missing Authorization header"},
                status_code=401,
            )

        scheme, _, token = auth.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return JSONResponse(
                {"detail": "Invalid Authorization format"},
                status_code=401,
            )

        try:
            jwks = await self._get_jwks()
            jwks_set = PyJWKSet.from_dict(jwks)
            signing_key = jwks_set.get_signing_key_from_jwt(token)
            payload = pyjwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="account",
                issuer=f"{self._keycloak_url}/realms/{self._keycloak_realm}",
            )
        except pyjwt.ExpiredSignatureError:
            return JSONResponse(
                {"detail": "Token expired"},
                status_code=401,
            )
        except pyjwt.InvalidAudienceError as e:
            return JSONResponse(
                {"detail": f"Invalid token audience: {e}"},
                status_code=401,
            )
        except pyjwt.InvalidIssuerError as e:
            return JSONResponse(
                {"detail": f"Invalid token issuer: {e}"},
                status_code=401,
            )
        except pyjwt.InvalidTokenError as e:
            return JSONResponse(
                {"detail": f"Invalid token: {e}"},
                status_code=401,
            )

        # Attach user context to request state for downstream handlers
        request.state.cityos_user = {
            "sub": payload.get("sub"),
            "preferred_username": payload.get("preferred_username"),
            "email": payload.get("email"),
            "realm_roles": payload.get("realm_access", {}).get("roles", []),
            "tenant_id": request.headers.get("X-CityOS-Tenant-Id"),
            "node_path": request.headers.get("X-CityOS-Node-Path"),
        }

        return None

    def _validate_api_key(self, request: Request) -> Any | None:  # noqa: ANN401
        auth = request.headers.get("Authorization", "")
        if not auth:
            return JSONResponse(
                {"detail": "Missing Authorization header"},
                status_code=401,
            )
        scheme, _, token = auth.partition(" ")
        if scheme.lower() != "bearer" or token != self._api_key:
            return JSONResponse(
                {"detail": "Invalid API key"},
                status_code=401,
            )
        return None

    async def _get_jwks(self) -> dict[str, Any]:
        """Fetch and cache Keycloak JWKS."""
        if self._jwks is not None:
            return self._jwks

        if self._jwks_client is None:
            self._jwks_client = httpx.AsyncClient(timeout=10.0)

        jwks_url = (
            f"{self._keycloak_url}"
            f"/realms/{self._keycloak_realm}"
            f"/protocol/openid-connect/certs"
        )
        response = await self._jwks_client.get(jwks_url)
        response.raise_for_status()
        self._jwks = response.json()
        return self._jwks
