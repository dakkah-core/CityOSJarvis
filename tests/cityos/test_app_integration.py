"""Integration tests for FastAPI application assembly.

Note: Full app requires engine + model via create_app() factory.
These tests verify individual route modules are importable.
"""

from __future__ import annotations


class TestRouteModulesImportable:
    def test_voice_service_router_importable(self) -> None:
        from openjarvis.cityos.voice_service import router

        assert router is not None
        assert len(router.routes) > 0

    def test_auth_module_importable(self) -> None:
        from openjarvis.cityos.auth import CityOSAuthMiddleware

        assert CityOSAuthMiddleware is not None

    def test_compliance_module_importable(self) -> None:
        from openjarvis.cityos.compliance import ComplianceGate

        assert ComplianceGate is not None

    def test_audit_module_importable(self) -> None:
        from openjarvis.cityos.audit import CityOSAuditLogger

        assert CityOSAuditLogger is not None

    def test_tenant_module_importable(self) -> None:
        from openjarvis.cityos.tenant import TenantContext

        assert TenantContext is not None

    def test_tenant_runtime_importable(self) -> None:
        from openjarvis.cityos.tenant_runtime import TenantAwareAgentRunner

        assert TenantAwareAgentRunner is not None

    def test_loki_handler_importable(self) -> None:
        from openjarvis.cityos.loki_handler import LokiHandler

        assert LokiHandler is not None

    def test_metrics_module_importable(self) -> None:
        from openjarvis.cityos.metrics import MetricsMiddleware

        assert MetricsMiddleware is not None

    def test_voice_prompts_importable(self) -> None:
        from openjarvis.cityos.voice_prompts import load_voice_prompt

        assert callable(load_voice_prompt)

    def test_app_factory_importable(self) -> None:
        from openjarvis.server.app import create_app

        assert callable(create_app)
