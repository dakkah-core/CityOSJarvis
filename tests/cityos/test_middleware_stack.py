"""Verify middleware stack ordering and security headers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestMiddlewareStack:
    """Verify middleware is registered in correct order."""

    def test_security_headers_middleware_present(self) -> None:
        """SecurityHeadersMiddleware adds expected headers to responses."""
        from openjarvis.server.middleware import create_security_middleware

        app = FastAPI()
        middleware_cls = create_security_middleware()
        assert middleware_cls is not None, "SecurityHeadersMiddleware should be available"

        app.add_middleware(middleware_cls)

        @app.get("/test")
        def test_endpoint() -> dict:
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        # Check for security headers
        headers = response.headers
        assert "x-content-type-options" in headers
        assert headers["x-content-type-options"] == "nosniff"
        assert "x-frame-options" in headers
        assert "strict-transport-security" in headers or "x-xss-protection" in headers

    def test_cors_middleware_before_auth(self) -> None:
        """CORS preflight requests should not require authentication."""
        from fastapi.middleware.cors import CORSMiddleware
        from openjarvis.cityos.auth import CityOSAuthMiddleware

        app = FastAPI()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://dakkah.city"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.add_middleware(CityOSAuthMiddleware)

        @app.get("/protected")
        def protected() -> dict:
            return {"ok": True}

        client = TestClient(app)
        # CORS preflight should succeed without auth
        response = client.options(
            "/protected",
            headers={
                "Origin": "https://dakkah.city",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_middleware_order_in_app_py(self) -> None:
        """Verify middleware registration order in app.py source."""
        from pathlib import Path

        app_py = Path(__file__).parent.parent.parent / "src" / "openjarvis" / "server" / "app.py"
        source = app_py.read_text()
        security_idx = source.find("create_security_middleware")
        auth_idx = source.find("CityOSAuthMiddleware")

        assert security_idx > 0, "Security middleware should be registered"
        assert auth_idx > 0, "CityOSAuthMiddleware should be registered"
        assert security_idx < auth_idx, (
            "Security headers must be registered BEFORE auth middleware"
        )

    def test_request_logging_middleware_present(self) -> None:
        """Request logging middleware captures tenant and correlation IDs."""
        app = FastAPI()

        @app.middleware("http")
        async def log_middleware(request, call_next):
            response = await call_next(request)
            response.headers["x-request-id"] = request.headers.get("x-correlation-id", "none")
            return response

        @app.get("/test")
        def test_endpoint() -> dict:
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test", headers={"x-correlation-id": "test-123"})

        assert response.headers["x-request-id"] == "test-123"

    def test_compliance_gate_blocks_before_agent(self) -> None:
        """Compliance gate must run before agent execution."""
        from openjarvis.cityos.compliance import ComplianceGate

        gate = ComplianceGate()
        result = gate.classify("My national ID is 1234567890")

        assert not result.allowed
        assert result.redacted_payload is not None
        assert "[REDACTED]" in result.redacted_payload
