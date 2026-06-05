"""Tests for CityOS audit logging — structured, append-only, sanitized.

Verifies that:
- Audit events are written as JSON Lines
- Raw message content is redacted (no PII in logs)
- Query interface works for compliance review
- Tenant isolation is maintained in logs
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from openjarvis.cityos.audit import AuditEvent, CityOSAuditLogger
from openjarvis.cityos.tenant import TenantContext


class TestAuditEvent:
    """Test the AuditEvent dataclass."""

    def test_event_structure(self):
        event = AuditEvent(
            timestamp="2026-05-30T10:00:00Z",
            event="chat.completion",
            actor={"sub": "user-123", "tenant_id": "tenant-42"},
            request={"model": "ollama", "messages_count": 3},
            response={"status": "success", "tokens_used": 150},
            tools_called=["governance.lookup_permit"],
            latency_ms=420.5,
            compliance={"classified_as": "public", "gate_passed": True},
            correlation_id="corr-abc-123",
        )
        assert event.event == "chat.completion"
        assert event.actor["tenant_id"] == "tenant-42"
        assert event.latency_ms == 420.5
        assert event.correlation_id == "corr-abc-123"

    def test_defaults(self):
        event = AuditEvent(
            timestamp="2026-05-30T10:00:00Z",
            event="test",
            actor={},
            request={},
        )
        assert event.response is None
        assert event.tools_called == []
        assert event.latency_ms is None
        assert event.compliance == {}
        assert event.correlation_id is None


class TestAuditLoggerWrite:
    """Test writing audit events."""

    def test_log_creates_file(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(
            event="chat.completion",
            tenant=None,
            request={"model": "test"},
        )
        log_file = Path(temp_log_dir) / "audit.jsonl"
        assert log_file.exists()

    def test_log_appends_json_line(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(
            event="chat.completion",
            tenant=None,
            request={"model": "test"},
        )
        log_file = Path(temp_log_dir) / "audit.jsonl"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["event"] == "chat.completion"
        assert record["timestamp"]  # Should have auto-generated timestamp

    def test_log_with_tenant(self, temp_log_dir):
        tenant = TenantContext(
            tenant_id="tenant-99",
            node_path="global/sa/riyadh",
            realm_roles=["admin"],
            user_sub="user-456",
        )
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(
            event="voice.intent",
            tenant=tenant,
            request={"intent": "weather_query"},
            tools_called=["weather.lookup"],
            latency_ms=250.0,
        )

        log_file = Path(temp_log_dir) / "audit.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert record["actor"]["tenant_id"] == "tenant-99"
        assert record["actor"]["user_sub"] == "user-456"
        assert record["actor"]["roles"] == ["admin"]
        assert record["tools_called"] == ["weather.lookup"]
        assert record["latency_ms"] == 250.0

    def test_log_appends_multiple_events(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        for i in range(3):
            logger.log(
                event=f"event-{i}",
                tenant=None,
                request={"index": i},
            )

        log_file = Path(temp_log_dir) / "audit.jsonl"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 3
        for i, line in enumerate(lines):
            record = json.loads(line)
            assert record["event"] == f"event-{i}"


class TestSanitization:
    """Test that raw message content is redacted from audit logs."""

    def test_content_redacted(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(
            event="chat.completion",
            tenant=None,
            request={
                "model": "ollama",
                "content": "My secret message here",
                "other_field": "preserved",
            },
        )

        log_file = Path(temp_log_dir) / "audit.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert record["request"]["content"] == "[REDACTED:22chars]"
        assert record["request"]["other_field"] == "preserved"

    def test_text_redacted(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(
            event="voice.stt",
            tenant=None,
            request={"text": "Spoken words here"},
        )

        log_file = Path(temp_log_dir) / "audit.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert "[REDACTED:" in record["request"]["text"]

    def test_prompt_redacted(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(
            event="chat.completion",
            tenant=None,
            request={"prompt": "System prompt with instructions"},
        )

        log_file = Path(temp_log_dir) / "audit.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert "[REDACTED:" in record["request"]["prompt"]

    def test_nested_dict_redacted(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(
            event="chat.completion",
            tenant=None,
            request={
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there"},
                ],
            },
        )

        log_file = Path(temp_log_dir) / "audit.jsonl"
        record = json.loads(log_file.read_text().strip())
        # Nested dicts in lists should also be sanitized
        messages = record["request"]["messages"]
        assert "[REDACTED:" in messages[0]["content"]
        assert "[REDACTED:" in messages[1]["content"]
        assert messages[0]["role"] == "user"  # Non-sensitive fields preserved

    def test_response_also_redacted(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(
            event="chat.completion",
            tenant=None,
            request={"model": "test"},
            response={"content": "Assistant response text", "status": "ok"},
        )

        log_file = Path(temp_log_dir) / "audit.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert "[REDACTED:" in record["response"]["content"]
        assert record["response"]["status"] == "ok"


class TestQuery:
    """Test the read-only query interface for compliance review."""

    def test_query_by_tenant(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)

        tenant_a = TenantContext("tenant-a", None, [], "user-1")
        tenant_b = TenantContext("tenant-b", None, [], "user-2")

        logger.log(event="event-1", tenant=tenant_a, request={})
        logger.log(event="event-2", tenant=tenant_b, request={})
        logger.log(event="event-3", tenant=tenant_a, request={})

        results = logger.query(tenant_id="tenant-a")
        assert len(results) == 2
        assert all(r["actor"]["tenant_id"] == "tenant-a" for r in results)

    def test_query_by_event_type(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(event="chat.completion", tenant=None, request={})
        logger.log(event="voice.intent", tenant=None, request={})
        logger.log(event="chat.completion", tenant=None, request={})

        results = logger.query(event_type="chat.completion")
        assert len(results) == 2

    def test_query_limit(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        for i in range(10):
            logger.log(event=f"event-{i}", tenant=None, request={})

        results = logger.query(limit=3)
        assert len(results) == 3

    def test_query_since(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(event="old-event", tenant=None, request={})
        logger.log(event="new-event", tenant=None, request={})

        # Query for events since a recent timestamp (should only get new-event)
        results = logger.query(since="2099-01-01T00:00:00Z")
        assert len(results) == 0  # No events after 2099

    def test_query_empty_log(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        results = logger.query()
        assert results == []

    def test_query_handles_corrupt_lines(self, temp_log_dir):
        logger = CityOSAuditLogger(log_dir=temp_log_dir)
        logger.log(event="valid", tenant=None, request={})

        # Append a corrupt line
        log_file = Path(temp_log_dir) / "audit.jsonl"
        with log_file.open("a") as f:
            f.write("this is not json\n")

        logger.log(event="also-valid", tenant=None, request={})

        results = logger.query()
        assert len(results) == 2  # Corrupt line skipped


class TestEnvironmentConfig:
    """Test that logger respects environment configuration."""

    def test_uses_env_var_for_log_dir(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("CITYOS_AUDIT_DIR", "/tmp/test-audit-logs")
            logger = CityOSAuditLogger()
            # Use normpath for cross-platform comparison
            assert os.path.normpath(str(logger._log_dir)) == os.path.normpath(
                "/tmp/test-audit-logs"
            )

    def test_uses_default_when_no_env(self):
        # Ensure env var is not set
        os.environ.pop("CITYOS_AUDIT_DIR", None)
        logger = CityOSAuditLogger()
        assert os.path.normpath(str(logger._log_dir)) == os.path.normpath(
            "/var/log/cityosjarvis"
        )

    def test_log_dir_created(self, temp_log_dir):
        subdir = Path(temp_log_dir) / "nested" / "audit"
        assert not subdir.exists()
        logger = CityOSAuditLogger(log_dir=str(subdir))
        # Directory created on init
        assert subdir.exists()
        # File created on first log
        logger.log(event="test", tenant=None, request={})
        assert (subdir / "audit.jsonl").exists()
