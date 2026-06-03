"""Tests for CityOS Keycloak JWT authentication middleware."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openjarvis.cityos.auth import CityOSAuthMiddleware


class TestRequiresAuth:
    """Test the _requires_auth path matching."""

    @pytest.fixture
    def middleware(self):
        return CityOSAuthMiddleware(app=MagicMock())

    def test_health_check_exempt(self, middleware):
        assert middleware._requires_auth("/health") is False
        assert middleware._requires_auth("/v1/health") is False
        assert middleware._requires_auth("/api/health") is False

    def test_v1_routes_require_auth(self, middleware):
        assert middleware._requires_auth("/v1/chat/completions") is True
        assert middleware._requires_auth("/v1/agents") is True
        assert middleware._requires_auth("/v1/voice/process-intent") is True

    def test_public_readonly_api_routes_optional(self, middleware):
        assert middleware._requires_auth("/v1/savings") is False
        assert middleware._requires_auth("/v1/savings/") is False
        assert middleware._requires_auth("/v1/analytics/identity") is False

    def test_api_routes_require_auth(self, middleware):
        assert middleware._requires_auth("/api/voice/webhook") is True
        assert middleware._requires_auth("/api/status") is True

    def test_other_routes_optional(self, middleware):
        assert middleware._requires_auth("/") is False
        assert middleware._requires_auth("/docs") is False


class TestApiKeyFallback:
    """Test legacy API key fallback authentication."""

    @pytest.fixture
    def middleware(self):
        return CityOSAuthMiddleware(app=MagicMock(), api_key="test-api-key-123")

    def test_valid_api_key(self, middleware):
        request = MagicMock()
        request.headers = {"Authorization": "Bearer test-api-key-123"}
        result = middleware._validate_api_key(request)
        assert result is None  # None means success (no error response)

    def test_invalid_api_key(self, middleware):
        request = MagicMock()
        request.headers = {"Authorization": "Bearer wrong-key"}
        result = middleware._validate_api_key(request)
        assert result is not None
        assert result.status_code == 401
        assert "Invalid API key" in result.body.decode()

    def test_missing_auth_header(self, middleware):
        request = MagicMock()
        request.headers = {}
        result = middleware._validate_api_key(request)
        assert result is not None
        assert result.status_code == 401
        assert "Missing Authorization" in result.body.decode()

    def test_wrong_scheme(self, middleware):
        request = MagicMock()
        request.headers = {"Authorization": "Basic test-api-key-123"}
        result = middleware._validate_api_key(request)
        assert result is not None
        assert result.status_code == 401


class TestKeycloakValidation:
    """Test Keycloak JWT validation (with mocked JWKS)."""

    @pytest.fixture
    def middleware(self):
        os.environ["KEYCLOAK_URL"] = "http://keycloak:8080"
        os.environ["KEYCLOAK_REALM"] = "cityos"
        return CityOSAuthMiddleware(app=MagicMock())

    @pytest.mark.asyncio
    async def test_missing_auth_header(self, middleware):
        request = MagicMock()
        request.headers = {}
        result = await middleware._validate_keycloak(request)
        assert result is not None
        assert result.status_code == 401
        assert "Missing Authorization" in result.body.decode()

    @pytest.mark.asyncio
    async def test_invalid_auth_format(self, middleware):
        request = MagicMock()
        request.headers = {"Authorization": "Basic dGVzdA=="}
        result = await middleware._validate_keycloak(request)
        assert result is not None
        assert result.status_code == 401
        assert "Invalid Authorization format" in result.body.decode()

    @pytest.mark.asyncio
    async def test_expired_token(self, middleware):
        import jwt as pyjwt_lib
        from jwt import PyJWKSet

        request = MagicMock()
        request.headers = {"Authorization": "Bearer expired-token"}

        mock_jwk_set = MagicMock()
        mock_jwk_set.get_signing_key_from_jwt.return_value = MagicMock(key="dummy-key")
        with patch.object(middleware, "_get_jwks", return_value={"keys": []}):
            with patch.object(PyJWKSet, "from_dict", return_value=mock_jwk_set):
                with patch("openjarvis.cityos.auth.pyjwt.decode", side_effect=pyjwt_lib.ExpiredSignatureError):
                    result = await middleware._validate_keycloak(request)

        assert result is not None
        assert result.status_code == 401
        assert "Token expired" in result.body.decode()

    @pytest.mark.asyncio
    async def test_invalid_signature(self, middleware):
        import jwt as pyjwt_lib
        from jwt import PyJWKSet

        request = MagicMock()
        request.headers = {"Authorization": "Bearer bad-token"}

        mock_jwk_set = MagicMock()
        mock_jwk_set.get_signing_key_from_jwt.return_value = MagicMock(key="dummy-key")
        with patch.object(middleware, "_get_jwks", return_value={"keys": []}):
            with patch.object(PyJWKSet, "from_dict", return_value=mock_jwk_set):
                with patch("openjarvis.cityos.auth.pyjwt.decode", side_effect=pyjwt_lib.InvalidTokenError("signature failed")):
                    result = await middleware._validate_keycloak(request)

        assert result is not None
        assert result.status_code == 401
        assert "Invalid token" in result.body.decode()

    @pytest.mark.asyncio
    async def test_valid_token_sets_user(self, middleware):
        from jwt import PyJWKSet

        request = MagicMock()
        request.headers = {
            "Authorization": "Bearer valid-token",
            "X-CityOS-Tenant-Id": "tenant-99",
            "X-CityOS-Node-Path": "global/sa/riyadh",
        }
        request.state = MagicMock()

        mock_jwk_set = MagicMock()
        mock_jwk_set.get_signing_key_from_jwt.return_value = MagicMock(key="dummy-key")
        with patch("openjarvis.cityos.auth.pyjwt.decode", return_value={
            "sub": "user-456",
            "preferred_username": "alice",
            "email": "alice@example.com",
            "realm_access": {"roles": ["city-admin"]},
        }):
            with patch.object(middleware, "_get_jwks", return_value={"keys": []}):
                with patch.object(PyJWKSet, "from_dict", return_value=mock_jwk_set):
                    result = await middleware._validate_keycloak(request)

        assert result is None  # Success
        assert request.state.cityos_user["sub"] == "user-456"
        assert request.state.cityos_user["preferred_username"] == "alice"
        assert request.state.cityos_user["realm_roles"] == ["city-admin"]
        assert request.state.cityos_user["tenant_id"] == "tenant-99"
        assert request.state.cityos_user["node_path"] == "global/sa/riyadh"


class TestJWKS:
    """Test JWKS fetching and caching."""

    @pytest.fixture
    def middleware(self):
        os.environ["KEYCLOAK_URL"] = "http://keycloak:8080"
        os.environ["KEYCLOAK_REALM"] = "cityos"
        return CityOSAuthMiddleware(app=MagicMock())

    @pytest.mark.asyncio
    async def test_jwks_cache(self, middleware):
        """JWKS should be fetched once and then cached."""
        mock_jwks = {"keys": [{"kid": "key1", "kty": "RSA"}]}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                json=MagicMock(return_value=mock_jwks),
                raise_for_status=MagicMock(),
            )

            # First call should fetch
            result1 = await middleware._get_jwks()
            assert result1 == mock_jwks
            assert mock_get.call_count == 1

            # Second call should use cache
            result2 = await middleware._get_jwks()
            assert result2 == mock_jwks
            assert mock_get.call_count == 1  # Still 1, cached

    @pytest.mark.asyncio
    async def test_jwks_url_construction(self, middleware):
        mock_jwks = {"keys": []}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                json=MagicMock(return_value=mock_jwks),
                raise_for_status=MagicMock(),
            )
            await middleware._get_jwks()

        call_args = mock_get.call_args
        assert "http://keycloak:8080/realms/cityos/protocol/openid-connect/certs" in str(call_args)


class TestDispatch:
    """Test the full dispatch flow."""

    @pytest.mark.asyncio
    async def test_exempt_path_bypasses_auth(self):
        middleware = CityOSAuthMiddleware(app=MagicMock())
        call_next = AsyncMock(return_value="response")

        request = MagicMock()
        request.url.path = "/health"

        result = await middleware.dispatch(request, call_next)
        assert result == "response"
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_keycloak_no_api_key_allows_through(self):
        """If no auth configured, request passes through (for local dev)."""
        os.environ.pop("KEYCLOAK_URL", None)
        middleware = CityOSAuthMiddleware(app=MagicMock(), api_key="")
        call_next = AsyncMock(return_value="response")

        request = MagicMock()
        request.url.path = "/v1/chat"
        request.headers = {}

        result = await middleware.dispatch(request, call_next)
        assert result == "response"
        call_next.assert_awaited_once()
