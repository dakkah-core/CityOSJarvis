"""Expanded audit logging tests."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from openjarvis.cityos.audit import AuditEvent, CityOSAuditLogger
from openjarvis.cityos.tenant import TenantContext


class TestAuditEvent:
    def test_event_creation(self) -> None:
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event="chat.completed",
            actor={"sub": "user-123", "roles": ["ai_user"]},
            request={"message": "Hello"},
            response={"content": "Hi there"},
            tools_called=[],
            latency_ms=150.0,
            compliance={"allowed": True},
        )
        assert event.event == "chat.completed"
        assert event.latency_ms == 150.0

    def test_event_serialization(self) -> None:
        event = AuditEvent(
            timestamp="2024-01-01T00:00:00+00:00",
            event="test",
            actor={"sub": "u1"},
            request={},
            response={},
            tools_called=[],
            latency_ms=0.0,
            compliance={},
        )
        d = event.__dict__ if hasattr(event, "__dict__") else {}
        if not d:
            d = {
                "timestamp": event.timestamp,
                "event": event.event,
                "actor": event.actor,
                "request": event.request,
                "response": event.response,
                "tools_called": event.tools_called,
                "latency_ms": event.latency_ms,
                "compliance": event.compliance,
                "correlation_id": event.correlation_id,
            }
        assert d["event"] == "test"
        assert d["timestamp"] == "2024-01-01T00:00:00+00:00"


class TestCityOSAuditLogger:
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield tmp

    @pytest.fixture
    def logger(self, temp_dir: str) -> CityOSAuditLogger:
        return CityOSAuditLogger(log_dir=temp_dir)

    @pytest.fixture
    def tenant(self) -> TenantContext:
        return TenantContext(
            tenant_id="test-tenant",
            node_path="global.sa.dakkah",
            realm_roles=["ai_user"],
            user_sub="user-123",
        )

    def test_log_creates_file(self, logger: CityOSAuditLogger, tenant: TenantContext) -> None:
        logger.log(
            event="chat.completed",
            tenant=tenant,
            request={"message": "Hello"},
            response={"content": "Hi"},
        )

        assert logger._file.exists()

    def test_log_contains_event_data(self, logger: CityOSAuditLogger, tenant: TenantContext) -> None:
        logger.log(
            event="chat.completed",
            tenant=tenant,
            request={"message": "Hello"},
            response={"content": "Hi"},
        )

        with open(logger._file) as f:
            line = f.readline()
            data = json.loads(line)

        assert data["event"] == "chat.completed"
        assert data["actor"]["tenant_id"] == "test-tenant"

    def test_log_sanitizes_content(self, logger: CityOSAuditLogger, tenant: TenantContext) -> None:
        logger.log(
            event="chat.completed",
            tenant=tenant,
            request={"content": "secret message"},
            response={"text": "response text"},
        )

        with open(logger._file) as f:
            line = f.readline()
            data = json.loads(line)

        # Sanitized fields should be redacted with length info
        assert "REDACTED" in data["request"]["content"]
        assert "REDACTED" in data["response"]["text"]

    def test_log_without_tenant(self, logger: CityOSAuditLogger) -> None:
        logger.log(
            event="system.startup",
            tenant=None,
            request={},
            response={"status": "ok"},
        )

        with open(logger._file) as f:
            line = f.readline()
            data = json.loads(line)

        assert data["event"] == "system.startup"

    def test_multiple_logs_append(self, logger: CityOSAuditLogger, tenant: TenantContext) -> None:
        for i in range(3):
            logger.log(
                event="chat.completed",
                tenant=tenant,
                request={"message": f"Msg {i}"},
                response={"content": f"Resp {i}"},
            )

        with open(logger._file) as f:
            lines = f.readlines()

        assert len(lines) == 3

    def test_correlation_id_propagation(self, logger: CityOSAuditLogger, tenant: TenantContext) -> None:
        logger.log(
            event="chat",
            tenant=tenant,
            request={},
            response={},
            correlation_id="corr-abc-123",
        )

        with open(logger._file) as f:
            data = json.loads(f.readline())

        assert data["correlation_id"] == "corr-abc-123"

    def test_latency_tracking(self, logger: CityOSAuditLogger, tenant: TenantContext) -> None:
        logger.log(
            event="chat",
            tenant=tenant,
            request={},
            response={},
            latency_ms=250.5,
        )

        with open(logger._file) as f:
            data = json.loads(f.readline())

        assert data["latency_ms"] == 250.5

    def test_tools_called_tracking(self, logger: CityOSAuditLogger, tenant: TenantContext) -> None:
        logger.log(
            event="chat",
            tenant=tenant,
            request={},
            response={},
            tools_called=["governance.lookup_permit", "commerce.search"],
        )

        with open(logger._file) as f:
            data = json.loads(f.readline())

        assert data["tools_called"] == ["governance.lookup_permit", "commerce.search"]

    def test_compliance_data(self, logger: CityOSAuditLogger, tenant: TenantContext) -> None:
        logger.log(
            event="chat",
            tenant=tenant,
            request={},
            response={},
            compliance={"classified_as": "public", "gate_passed": True},
        )

        with open(logger._file) as f:
            data = json.loads(f.readline())

        assert data["compliance"]["classified_as"] == "public"
        assert data["compliance"]["gate_passed"] is True
