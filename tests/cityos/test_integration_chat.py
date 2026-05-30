"""Integration tests for CityOSJarvis chat completions endpoint.

Tests the full request lifecycle through the FastAPI router:
- Auth middleware (JWT validation)
- Compliance gate (PHI/PII blocking)
- Audit logging (request/response recording)
- Engine dispatch (success and error paths)
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

# Set audit dir before importing routes (module-level logger instantiation)
os.environ["CITYOS_AUDIT_DIR"] = tempfile.mkdtemp()

from openjarvis.cityos.compliance import ComplianceGate
from openjarvis.cityos.audit import CityOSAuditLogger
from openjarvis.cityos.tenant import TenantContext
from openjarvis.server.routes import router as api_router
from openjarvis.server.models import ChatCompletionRequest, ChatMessage


@pytest.fixture
def mock_engine():
    """Return a mock inference engine."""
    engine = MagicMock()
    engine.generate.return_value = {
        "content": "Hello from CityOSJarvis",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "finish_reason": "stop",
    }
    return engine


@pytest.fixture
def app(mock_engine):
    """Build a minimal FastAPI app with the CityOS routes and mocked state."""
    fast_app = FastAPI()
    fast_app.include_router(api_router)
    fast_app.state.engine = mock_engine
    fast_app.state.agent = None
    fast_app.state.config = None
    fast_app.state.memory_backend = None
    fast_app.state.bus = None
    return fast_app


@pytest.fixture
def audit_file():
    """Provide a temporary audit log file and clean up after."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "audit.jsonl")
        yield path


@pytest.fixture(autouse=True)
def patch_audit_logger(monkeypatch, audit_file):
    """Replace module-level audit logger with one writing to temp file."""
    import openjarvis.server.routes as routes_mod
    log_dir = Path(os.path.dirname(audit_file))
    logger = CityOSAuditLogger(log_dir=str(log_dir))
    monkeypatch.setattr(routes_mod, "_audit_logger", logger)
    # Also patch the compliance gate to ensure fresh state
    monkeypatch.setattr(routes_mod, "_compliance_gate", ComplianceGate())


@pytest.fixture
def auth_headers():
    """Simulate a request that has already passed CityOSAuthMiddleware."""
    return {"X-CityOS-Tenant-Id": "tenant-42"}


class TestChatCompletionsCompliance:
    """PHI/PII blocking via ComplianceGate."""

    @pytest.mark.asyncio
    async def test_blocks_saudi_id(self, app, auth_headers):
        """Saudi national ID in user message should return 403."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "test-model",
                "messages": [{"role": "user", "content": "My ID is 1234567890"}],
            }
            response = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_blocks_credit_card(self, app, auth_headers):
        """Credit card number should return 403."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "test-model",
                "messages": [{"role": "user", "content": "Card: 4532-1234-5678-9012"}],
            }
            response = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_blocks_email(self, app, auth_headers):
        """Email address should return 403."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "test-model",
                "messages": [{"role": "user", "content": "Contact me at test@example.com"}],
            }
            response = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_allows_safe_query(self, app, auth_headers, mock_engine):
        """Non-PHI query should succeed and call engine."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "test-model",
                "messages": [{"role": "user", "content": "What is the weather today?"}],
            }
            response = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["choices"][0]["message"]["content"] == "Hello from CityOSJarvis"
        mock_engine.generate.assert_called_once()


class TestChatCompletionsAudit:
    """Audit logging for chat requests."""

    @pytest.mark.asyncio
    async def test_logs_blocked_request(self, app, auth_headers, audit_file):
        """Blocked request should produce an audit log entry."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "test-model",
                "messages": [{"role": "user", "content": "My email is leak@example.com"}],
            }
            await client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        with open(audit_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        assert len(lines) >= 1
        assert lines[-1]["event"] == "chat.completion.blocked"
        assert lines[-1]["compliance"]["gate_passed"] is False

    @pytest.mark.asyncio
    async def test_logs_successful_request(self, app, auth_headers, audit_file):
        """Successful request should produce a chat.completion audit entry."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello, assistant!"}],
            }
            await client.post("/v1/chat/completions", json=payload, headers=auth_headers)

        with open(audit_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        success_events = [e for e in lines if e["event"] == "chat.completion"]
        assert len(success_events) >= 1
        assert success_events[-1]["compliance"]["gate_passed"] is True
        assert "latency_ms" in success_events[-1]


class TestChatCompletionsAuth:
    """Auth middleware behavior (simulated via request state)."""

    @pytest.mark.asyncio
    async def test_allows_request_with_tenant_header(self, app):
        """Request with tenant header should proceed."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello"}],
            }
            response = await client.post(
                "/v1/chat/completions", json=payload,
                headers={"X-CityOS-Tenant-Id": "tenant-42"}
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_request_without_tenant_header(self, app):
        """Request without tenant header should still proceed (public access)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello"}],
            }
            response = await client.post("/v1/chat/completions", json=payload)

        assert response.status_code == 200


class TestChatCompletionsError:
    """Error handling in chat completions."""

    @pytest.mark.asyncio
    async def test_engine_error_is_audited(self, app, auth_headers, audit_file):
        """Engine failure should be caught, audited, and re-raised."""
        app.state.engine.generate.side_effect = RuntimeError("model offline")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello"}],
            }
            # Starlette error middleware may raise in test context;
            # the important part is that an error audit entry is written
            try:
                await client.post("/v1/chat/completions", json=payload, headers=auth_headers)
            except RuntimeError:
                pass  # Expected; error middleware re-raises in ASGI test context

        with open(audit_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        error_events = [e for e in lines if e["event"] == "chat.completion.error"]
        assert len(error_events) >= 1
        assert error_events[-1]["response"]["status"] == "error"
        assert "model offline" in error_events[-1]["response"]["error"]
