"""Tests for RBAC permission checks integrated with tenant context."""

from __future__ import annotations

from openjarvis.cityos.tenant import TenantContext, validate_cross_tenant_access


class TestRBACPermissions:
    def test_ai_user_role_exists(self) -> None:
        ctx = TenantContext("t1", "global/sa", ["ai_user"], "u1")
        assert ctx.has_role("ai_user") is True

    def test_cityos_admin_role(self) -> None:
        ctx = TenantContext("t1", "global/sa", ["cityos_admin"], "u1")
        assert ctx.has_role("cityos_admin") is True
        assert ctx.has_role("ai_user") is False

    def test_system_admin_can_access_any_tenant(self) -> None:
        ctx = TenantContext("t1", "global/sa", ["system-admin"], "u1")
        assert validate_cross_tenant_access(ctx, "any-tenant") is True

    def test_regular_user_cannot_cross_tenant(self) -> None:
        ctx = TenantContext("t1", "global/sa", ["ai_user"], "u1")
        assert validate_cross_tenant_access(ctx, "t2") is False

    def test_same_tenant_always_allowed(self) -> None:
        ctx = TenantContext("t1", "global/sa", ["ai_user"], "u1")
        assert validate_cross_tenant_access(ctx, "t1") is True

    def test_parent_node_can_access_child(self) -> None:
        ctx = TenantContext("global/sa", "global/sa", ["ai_user"], "u1")
        assert validate_cross_tenant_access(ctx, "global/sa/dakkah") is True

    def test_child_node_cannot_access_parent(self) -> None:
        ctx = TenantContext("global/sa/dakkah", "global/sa/dakkah", ["ai_user"], "u1")
        assert validate_cross_tenant_access(ctx, "global/sa") is False

    def test_empty_roles_denied(self) -> None:
        ctx = TenantContext("t1", "global/sa", [], "u1")
        assert validate_cross_tenant_access(ctx, "t2") is False

    def test_multiple_roles_evaluated(self) -> None:
        ctx = TenantContext("t1", "global/sa", ["ai_user", "system-admin"], "u1")
        assert validate_cross_tenant_access(ctx, "t2") is True
