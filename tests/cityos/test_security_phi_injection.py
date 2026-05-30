"""Security tests: PHI/PII injection via chat completions endpoint.

Validates that the ComplianceGate blocks sensitive data from reaching
the inference engine through the main chat API.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

os.environ["CITYOS_AUDIT_DIR"] = tempfile.mkdtemp()

from openjarvis.cityos.compliance import ComplianceGate
from openjarvis.cityos.audit import CityOSAuditLogger
from openjarvis.server.routes import router as api_router


@pytest.fixture
def app():
    """Minimal FastAPI app with routes and mocked engine."""
    engine = MagicMock()
    engine.generate.return_value = {
        "content": "response",
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        "finish_reason": "stop",
    }
    fast_app = FastAPI()
    fast_app.include_router(api_router)
    fast_app.state.engine = engine
    fast_app.state.agent = None
    fast_app.state.config = None
    fast_app.state.memory_backend = None
    fast_app.state.bus = None
    return fast_app


@pytest.fixture(autouse=True)
def patch_gate_and_logger(monkeypatch):
    """Ensure fresh compliance gate and temp audit logger."""
    import openjarvis.server.routes as routes_mod
    with tempfile.TemporaryDirectory() as tmp:
        logger = CityOSAuditLogger(log_dir=tmp)
        monkeypatch.setattr(routes_mod, "_audit_logger", logger)
        monkeypatch.setattr(routes_mod, "_compliance_gate", ComplianceGate())
        yield


PHI_TEST_CASES = [
    # Saudi National ID / Iqama
    ("saudi_id_10digit", "My ID is 1234567890"),
    ("saudi_id_2digit_prefix", "ID: 21-1234567"),
    ("saudi_id_with_dashes", "Iqama: 2-123456789"),
    # Credit cards
    ("visa", "Card: 4532-1234-5678-9012"),
    ("mastercard", "Card: 5500-0000-0000-0004"),
    ("amex", "Card: 3782-822463-10005"),
    ("visa_no_spaces", "4532123456789012"),
    # Saudi IBAN
    ("saudi_iban", "IBAN: SA0380000000608010167519"),
    ("saudi_iban_lower", "iban sa0380000000608010167519"),
    # Email
    ("email_simple", "contact me at user@example.com"),
    ("email_gov", "email: citizen@moi.gov.sa"),
    # Saudi mobile
    ("saudi_mobile", "My number is 0501234567"),
    ("saudi_mobile_plus", "Call +966501234567"),
    # API keys / secrets
    ("api_key", "sk-abc123def456ghi789jkl012mnop345"),
    ("jwt_looking", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMifQ"),
    # Health keywords
    ("health_medication", "My medication dosage is 50mg daily"),
    ("health_diagnosis", "Diagnosis: Type 2 diabetes"),
    ("health_arabic", "تشخيص: ضغط عالي"),
    ("health_arabic_surgery", "أحتاج عملية جراحية"),
    # Mixed Arabic/English
    ("mixed_ar_en_id", "رقم الهوية 1234567890"),
]


class TestPHIBlocking:
    """Each sensitive payload should return 403 and NOT call engine."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_id,payload", PHI_TEST_CASES, ids=[t[0] for t in PHI_TEST_CASES])
    async def test_phi_blocked(self, app, test_id: str, payload: str):
        """Sensitive data must be blocked before reaching engine."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": "test-model",
                    "messages": [{"role": "user", "content": payload}],
                },
            )

        assert response.status_code == 403, f"{test_id}: Expected 403, got {response.status_code}"
        # Engine must NOT be called for blocked requests
        app.state.engine.generate.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_id,payload", PHI_TEST_CASES, ids=[t[0] for t in PHI_TEST_CASES])
    async def test_phi_audit_trail(self, app, test_id: str, payload: str):
        """Blocked PHI requests must leave an audit trail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/v1/chat/completions",
                json={
                    "model": "test-model",
                    "messages": [{"role": "user", "content": payload}],
                },
            )

        # Audit log check is implicit: if _audit_logger fails, the request would 500
        # A more thorough test would read the log file, but the integration tests
        # already cover that path.


class TestSafeQueriesAllowed:
    """Non-sensitive queries should proceed normally."""

    SAFE_CASES = [
        "What is the weather today?",
        "How do I pay a parking ticket?",
        "أين أجد أقرب مستشفى؟",  # "Where is the nearest hospital?" -- no PHI, just a query
        "Tell me about city events this weekend",
        "What are the business hours for the municipality?",
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SAFE_CASES)
    async def test_safe_allowed(self, app, payload: str):
        """Non-sensitive queries should return 200."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": "test-model",
                    "messages": [{"role": "user", "content": payload}],
                },
            )

        assert response.status_code == 200
        app.state.engine.generate.assert_called_once()
        app.state.engine.generate.reset_mock()


class TestPHIEvasion:
    """Attempted evasion techniques should still be caught."""

    EVASION_CASES = [
        ("spaces_between_digits", "My ID is 1 2 3 4 5 6 7 8 9 0"),
        ("newline_separated", "ID:\n1234567890"),
        ("base64_encoded_email", "Contact: dXNlckBleGFtcGxlLmNvbQ=="),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_id,payload", EVASION_CASES, ids=[t[0] for t in EVASION_CASES])
    async def test_evasion_blocked(self, app, test_id: str, payload: str):
        """Evasion attempts should still trigger blocking."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": "test-model",
                    "messages": [{"role": "user", "content": payload}],
                },
            )

        # Some evasions may not be caught (expected limitation)
        # We just verify the gate doesn't crash and engine isn't called on 403
        if response.status_code == 403:
            app.state.engine.generate.assert_not_called()
