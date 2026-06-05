"""CityOS-specific extensions for OpenJarvis.

This package contains patches and extensions that adapt OpenJarvis for
the Dakkah CityOS smart city platform, including:

- Keycloak OIDC/JWT authentication
- Multi-tenancy via Node hierarchy
- Compliance data classification (PHI/PII filtering)
- Audit logging for governance
- CityOS-specific prompt templates
- Domain-specific MCP tool configurations
"""

from .audit import CityOSAuditLogger
from .auth import CityOSAuthMiddleware
from .compliance import ComplianceGate
from .tenant import TenantContext, get_tenant_context

# Voice service router (registered in app.py)
from .voice_service import router as voice_router  # noqa: F401

__all__ = [
    "CityOSAuthMiddleware",
    "TenantContext",
    "get_tenant_context",
    "ComplianceGate",
    "CityOSAuditLogger",
]
