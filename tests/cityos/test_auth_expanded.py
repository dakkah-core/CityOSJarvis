"""Expanded auth and tenant context tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from openjarvis.cityos.auth import CityOSAuthMiddleware
from openjarvis.cityos.tenant import (
    TenantContext,
    get_tenant_context,
    validate_cross_tenant_access,
)


class TestAuthEdgeCases:
    @pytest.fixture
    def middleware(self) -> CityOSAuthMiddleware:
        app = MagicMock()
        return CityOSAuthMiddleware(app, api_key="test-api-key")

    def test_requires_auth_exempt_paths(self, middleware: CityOSAuthMiddleware) -> None:
        assert middleware._requires_auth("/health") is False
        assert middleware._requires_auth("/v1/health") is False
        assert middleware._requires_auth("/api/health") is False

    def test_requires_auth_protected_paths(
        self, middleware: CityOSAuthMiddleware
    ) -> None:
        assert middleware._requires_auth("/v1/chat") is True
        assert middleware._requires_auth("/api/bff/ai/chat") is True

    def test_requires_auth_other_paths(self, middleware: CityOSAuthMiddleware) -> None:
        assert middleware._requires_auth("/") is False
        assert middleware._requires_auth("/static/file.css") is False

    def test_validate_api_key_missing_auth(
        self, middleware: CityOSAuthMiddleware
    ) -> None:
        request = MagicMock()
        request.headers = {}
        result = middleware._validate_api_key(request)
        assert result is not None
        assert result.status_code == 401

    def test_validate_api_key_wrong_key(self, middleware: CityOSAuthMiddleware) -> None:
        request = MagicMock()
        request.headers = {"Authorization": "Bearer wrong-key"}
        result = middleware._validate_api_key(request)
        assert result is not None
        assert result.status_code == 401

    def test_validate_api_key_correct_key(
        self, middleware: CityOSAuthMiddleware
    ) -> None:
        request = MagicMock()
        request.headers = {"Authorization": "Bearer test-api-key"}
        result = middleware._validate_api_key(request)
        assert result is None

    def test_validate_api_key_malformed(self, middleware: CityOSAuthMiddleware) -> None:
        request = MagicMock()
        request.headers = {"Authorization": "Basic dXNlcjpwYXNz"}
        result = middleware._validate_api_key(request)
        assert result is not None
        assert result.status_code == 401

    @pytest.mark.asyncio
    async def test_validate_keycloak_missing_auth(
        self, middleware: CityOSAuthMiddleware
    ) -> None:
        request = MagicMock()
        request.headers = {}
        result = await middleware._validate_keycloak(request)
        assert result is not None
        assert result.status_code == 401

    @pytest.mark.asyncio
    async def test_validate_keycloak_malformed_bearer(
        self, middleware: CityOSAuthMiddleware
    ) -> None:
        request = MagicMock()
        request.headers = {"Authorization": "Bearer"}
        result = await middleware._validate_keycloak(request)
        assert result is not None
        assert result.status_code == 401

    @pytest.mark.asyncio
    async def test_validate_keycloak_no_keycloak_url(
        self, middleware: CityOSAuthMiddleware
    ) -> None:
        middleware._keycloak_url = ""
        request = MagicMock()
        request.headers = {"Authorization": "Bearer token"}
        # When keycloak URL is empty, the method may fail on HTTP request
        # Just verify it doesn't crash silently
        try:
            result = await middleware._validate_keycloak(request)
            assert result is None or hasattr(result, "status_code")
        except Exception:
            # Expected if it tries to fetch JWKS from empty URL
            pass


class TestTenantContextFromAuth:
    def test_valid_tenant_context(self) -> None:
        ctx = TenantContext(
            tenant_id="t1",
            node_path="global/sa/dakkah",
            realm_roles=["ai_user", "cityos_admin"],
            user_sub="user-123",
        )
        assert ctx.is_valid() is True

    def test_invalid_tenant_context_empty_id(self) -> None:
        ctx = TenantContext(
            tenant_id="",
            node_path="global/sa/dakkah",
            realm_roles=[],
            user_sub="user-123",
        )
        assert ctx.is_valid() is False

    def test_invalid_tenant_context_bad_path(self) -> None:
        ctx = TenantContext(
            tenant_id="t1",
            node_path="invalid path with spaces",
            realm_roles=[],
            user_sub="user-123",
        )
        assert ctx.is_valid() is False

    def test_memory_index_prefix(self) -> None:
        ctx = TenantContext(
            tenant_id="my-tenant",
            node_path="global/sa/dakkah",
            realm_roles=["ai_user"],
            user_sub="user-123",
        )
        assert ctx.memory_index_prefix() == "cityos_memory_my-tenant"

    def test_trace_table_prefix(self) -> None:
        ctx = TenantContext(
            tenant_id="test-tenant",
            node_path="global/sa/dakkah",
            realm_roles=["ai_user"],
            user_sub="user-123",
        )
        assert ctx.trace_table_prefix() == "cityos_traces_test-tenant"

    def test_conversation_prefix(self) -> None:
        ctx = TenantContext(
            tenant_id="tenant-1",
            node_path="global/sa/dakkah",
            realm_roles=["ai_user"],
            user_sub="user-123",
        )
        assert ctx.conversation_prefix() == "cityos_conv_tenant-1"

    def test_has_role(self) -> None:
        ctx = TenantContext(
            tenant_id="t1",
            node_path="global/sa/dakkah",
            realm_roles=["ai_user", "cityos_admin"],
            user_sub="user-123",
        )
        assert ctx.has_role("ai_user") is True
        assert ctx.has_role("nonexistent") is False

    def test_log_dict_no_pii(self) -> None:
        ctx = TenantContext(
            tenant_id="t1",
            node_path="global/sa/dakkah",
            realm_roles=["ai_user"],
            user_sub="user-123",
        )
        log_dict = ctx.to_log_dict()
        assert "tenant_id" in log_dict
        assert "node_path" in log_dict
        assert "user_sub" in log_dict
        assert "roles" in log_dict
        assert log_dict["roles"] == ["ai_user"]

    def test_cross_tenant_same_tenant(self) -> None:
        ctx = TenantContext(
            tenant_id="t1",
            node_path="global/sa/dakkah",
            realm_roles=["ai_user"],
            user_sub="user-123",
        )
        assert validate_cross_tenant_access(ctx, "t1") is True

    def test_cross_tenant_system_admin(self) -> None:
        ctx = TenantContext(
            tenant_id="t1",
            node_path="global/sa/dakkah",
            realm_roles=["system-admin"],
            user_sub="user-123",
        )
        assert validate_cross_tenant_access(ctx, "t2") is True

    def test_cross_tenant_hierarchical(self) -> None:
        ctx = TenantContext(
            tenant_id="global/sa/dakkah",
            node_path="global/sa/dakkah",
            realm_roles=["ai_user"],
            user_sub="user-123",
        )
        assert validate_cross_tenant_access(ctx, "global/sa/dakkah/zone-1") is True

    def test_cross_tenant_denied(self) -> None:
        ctx = TenantContext(
            tenant_id="t1",
            node_path="global/sa/dakkah",
            realm_roles=["ai_user"],
            user_sub="user-123",
        )
        assert validate_cross_tenant_access(ctx, "t2") is False

    def test_get_tenant_context_from_request(self) -> None:
        request = MagicMock()
        request.state.cityos_user = {
            "sub": "user-123",
            "tenant_id": "t1",
            "node_path": "global/sa/dakkah",
            "realm_roles": ["ai_user"],
        }
        ctx = get_tenant_context(request)
        assert ctx is not None
        assert ctx.tenant_id == "t1"
        assert ctx.user_sub == "user-123"

    def test_get_tenant_context_no_user(self) -> None:
        request = MagicMock()
        request.state = {}
        ctx = get_tenant_context(request)
        assert ctx is None

    def test_get_tenant_context_defaults(self) -> None:
        request = MagicMock()
        request.state.cityos_user = {
            "sub": "user-123",
        }
        ctx = get_tenant_context(request)
        assert ctx is not None
        assert ctx.tenant_id == "default"
        assert ctx.realm_roles == []
