"""Multi-tenancy support for CityOS Node hierarchy.

Every request in CityOS is scoped to a tenant within the Node hierarchy:
Global → Country → Region → City → Zone → POI → Tenant

This module validates tenant isolation and provides tenant-scoped
resource prefixes for memory, traces, and conversation storage.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from starlette.requests import Request

logger = logging.getLogger(__name__)

# Valid Node path pattern: e.g., "global/sa/riyadh/dakkah/zone-7/poi-42/tenant-99"
NODE_PATH_PATTERN = re.compile(
    r"^global(/[a-z0-9-]+){0,6}$",
    re.IGNORECASE,
)

# Characters safe for use in index/table prefixes
SAFE_PREFIX_PATTERN = re.compile(r"[^a-z0-9_-]", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Immutable tenant context extracted from a request."""

    tenant_id: str
    node_path: str | None
    realm_roles: list[str]
    user_sub: str | None

    def is_valid(self) -> bool:
        """Return True if the tenant context passes basic validation."""
        if not self.tenant_id:
            return False
        if self.node_path and not NODE_PATH_PATTERN.match(self.node_path):
            return False
        return True

    def memory_index_prefix(self) -> str:
        """Return a safe prefix for vector memory indices."""
        safe = SAFE_PREFIX_PATTERN.sub("_", self.tenant_id.lower())
        return f"cityos_memory_{safe}"

    def trace_table_prefix(self) -> str:
        """Return a safe prefix for trace/audit table names."""
        safe = SAFE_PREFIX_PATTERN.sub("_", self.tenant_id.lower())
        return f"cityos_traces_{safe}"

    def conversation_prefix(self) -> str:
        """Return a safe prefix for conversation session keys."""
        safe = SAFE_PREFIX_PATTERN.sub("_", self.tenant_id.lower())
        return f"cityos_conv_{safe}"

    def has_role(self, role: str) -> bool:
        """Check if the tenant user has a specific Keycloak realm role."""
        return role in self.realm_roles

    def to_log_dict(self) -> dict[str, Any]:
        """Serialize for audit logging (no PII beyond sub)."""
        return {
            "tenant_id": self.tenant_id,
            "node_path": self.node_path,
            "user_sub": self.user_sub,
            "roles": self.realm_roles,
        }


def get_tenant_context(request: Request) -> TenantContext | None:
    """Extract tenant context from a CityOS-authenticated request.

    This should be called *after* CityOSAuthMiddleware has populated
    request.state.cityos_user.
    """
    user = getattr(request.state, "cityos_user", None)
    if not user:
        return None

    return TenantContext(
        tenant_id=user.get("tenant_id") or "default",
        node_path=user.get("node_path"),
        realm_roles=user.get("realm_roles", []),
        user_sub=user.get("sub"),
    )


def validate_cross_tenant_access(
    requester: TenantContext,
    target_tenant_id: str,
) -> bool:
    """Return True if requester is allowed to access target tenant data.

    Rules:
    - Same tenant: always allowed
    - Parent Node can access child Nodes (hierarchical)
    - System admin role can access any tenant
    - Everything else: denied
    """
    if requester.tenant_id == target_tenant_id:
        return True

    if "system-admin" in requester.realm_roles:
        return True

    if requester.node_path and target_tenant_id.startswith(requester.node_path):
        return True

    logger.warning(
        "Cross-tenant access denied: %s attempted to access %s",
        requester.tenant_id,
        target_tenant_id,
    )
    return False
