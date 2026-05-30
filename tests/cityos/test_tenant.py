"""Tests for CityOS multi-tenancy and Node hierarchy tenant isolation."""

from __future__ import annotations

import pytest

from openjarvis.cityos.tenant import (
    TenantContext,
    get_tenant_context,
    validate_cross_tenant_access,
)


class TestTenantContext:
    """Test TenantContext dataclass and methods."""

    def test_valid_tenant(self):
        ctx = TenantContext(
            tenant_id="tenant-42",
            node_path="global/sa/riyadh/dakkah",
            realm_roles=["ai-user"],
            user_sub="user-123",
        )
        assert ctx.is_valid() is True

    def test_empty_tenant_invalid(self):
        ctx = TenantContext(
            tenant_id="",
            node_path=None,
            realm_roles=[],
            user_sub=None,
        )
        assert ctx.is_valid() is False

    def test_invalid_node_path(self):
        ctx = TenantContext(
            tenant_id="tenant-42",
            node_path="invalid/path/with/way/too/many/segments/here",
            realm_roles=[],
            user_sub=None,
        )
        assert ctx.is_valid() is False

    def test_memory_index_prefix(self):
        ctx = TenantContext(
            tenant_id="Tenant-ABC!",
            node_path="global/sa/riyadh",
            realm_roles=[],
            user_sub=None,
        )
        # SAFE_PREFIX_PATTERN keeps a-z, 0-9, _, - and replaces everything else
        # "Tenant-ABC!".lower() -> "tenant-abc!" -> "tenant-abc_"
        assert ctx.memory_index_prefix() == "cityos_memory_tenant-abc_"

    def test_trace_table_prefix(self):
        ctx = TenantContext(
            tenant_id="t1",
            node_path="global/sa",
            realm_roles=[],
            user_sub=None,
        )
        assert ctx.trace_table_prefix() == "cityos_traces_t1"

    def test_conversation_prefix(self):
        ctx = TenantContext(
            tenant_id="my-tenant",
            node_path=None,
            realm_roles=[],
            user_sub=None,
        )
        assert ctx.conversation_prefix() == "cityos_conv_my-tenant"

    def test_has_role(self):
        ctx = TenantContext(
            tenant_id="t1",
            node_path=None,
            realm_roles=["admin", "ai-user"],
            user_sub=None,
        )
        assert ctx.has_role("admin") is True
        assert ctx.has_role("ai-user") is True
        assert ctx.has_role("nonexistent") is False

    def test_to_log_dict_no_pii(self):
        """Verify audit log serialization doesn't leak sensitive data."""
        ctx = TenantContext(
            tenant_id="tenant-42",
            node_path="global/sa/riyadh",
            realm_roles=["admin"],
            user_sub="user-123",
        )
        log_dict = ctx.to_log_dict()
        assert log_dict["tenant_id"] == "tenant-42"
        assert log_dict["node_path"] == "global/sa/riyadh"
        assert log_dict["user_sub"] == "user-123"
        assert log_dict["roles"] == ["admin"]
        # Should NOT contain email, name, or other PII
        assert "email" not in log_dict
        assert "name" not in log_dict


class TestGetTenantContext:
    """Test extracting tenant context from request state."""

    def test_extract_from_cityos_user(self):
        from unittest.mock import MagicMock

        request = MagicMock()
        request.state.cityos_user = {
            "sub": "user-456",
            "tenant_id": "tenant-99",
            "node_path": "global/sa/riyadh",
            "realm_roles": ["admin"],
        }

        ctx = get_tenant_context(request)
        assert ctx is not None
        assert ctx.tenant_id == "tenant-99"
        assert ctx.node_path == "global/sa/riyadh"
        assert ctx.user_sub == "user-456"
        assert ctx.realm_roles == ["admin"]

    def test_missing_auth_returns_none(self):
        from unittest.mock import MagicMock

        request = MagicMock()
        # No cityos_user attribute
        del request.state.cityos_user

        ctx = get_tenant_context(request)
        assert ctx is None

    def test_defaults_when_partial(self):
        from unittest.mock import MagicMock

        request = MagicMock()
        request.state.cityos_user = {
            "sub": "user-789",
            # Missing tenant_id, node_path, realm_roles
        }

        ctx = get_tenant_context(request)
        assert ctx.tenant_id == "default"
        assert ctx.node_path is None
        assert ctx.realm_roles == []
        assert ctx.user_sub == "user-789"


class TestCrossTenantAccess:
    """Test tenant isolation rules."""

    def test_same_tenant_allowed(self):
        requester = TenantContext(
            tenant_id="tenant-42",
            node_path="global/sa/riyadh/dakkah",
            realm_roles=["ai-user"],
            user_sub="user-1",
        )
        assert validate_cross_tenant_access(requester, "tenant-42") is True

    def test_different_tenant_denied(self):
        requester = TenantContext(
            tenant_id="tenant-42",
            node_path="global/sa/riyadh/dakkah",
            realm_roles=["ai-user"],
            user_sub="user-1",
        )
        assert validate_cross_tenant_access(requester, "tenant-99") is False

    def test_parent_can_access_child(self):
        """Hierarchical: parent node can access child node data."""
        requester = TenantContext(
            tenant_id="parent",
            node_path="global/sa/riyadh/dakkah",
            realm_roles=["ai-user"],
            user_sub="user-1",
        )
        # target_tenant_id starts with requester's node_path
        assert validate_cross_tenant_access(requester, "global/sa/riyadh/dakkah/zone-7") is True

    def test_child_cannot_access_parent(self):
        """Child node cannot access parent node data."""
        requester = TenantContext(
            tenant_id="child",
            node_path="global/sa/riyadh/dakkah/zone-7",
            realm_roles=["ai-user"],
            user_sub="user-1",
        )
        assert validate_cross_tenant_access(requester, "global/sa/riyadh/dakkah") is False

    def test_sibling_denied(self):
        """Sibling tenants cannot access each other."""
        requester = TenantContext(
            tenant_id="tenant-a",
            node_path="global/sa/riyadh/dakkah/zone-1",
            realm_roles=["ai-user"],
            user_sub="user-1",
        )
        assert validate_cross_tenant_access(requester, "global/sa/riyadh/dakkah/zone-2") is False

    def test_system_admin_can_access_any(self):
        """System admin role bypasses all tenant isolation."""
        requester = TenantContext(
            tenant_id="tenant-42",
            node_path="global/sa/riyadh",
            realm_roles=["system-admin"],
            user_sub="admin-1",
        )
        assert validate_cross_tenant_access(requester, "any-tenant-id") is True
        assert validate_cross_tenant_access(requester, "another-tenant") is True

    def test_no_node_path_denied(self):
        """If requester has no node_path, they can't claim parent access."""
        requester = TenantContext(
            tenant_id="tenant-42",
            node_path=None,
            realm_roles=["ai-user"],
            user_sub="user-1",
        )
        assert validate_cross_tenant_access(requester, "other-tenant") is False
