"""Tests for Loki log forwarding integration."""

from __future__ import annotations

import json
import time
from unittest.mock import patch, MagicMock

import pytest

from openjarvis.cityos.loki_handler import LokiHandler


class TestLokiHandler:
    def test_init_from_env(self) -> None:
        with patch.dict("os.environ", {"LOKI_URL": "http://loki:3100"}):
            handler = LokiHandler()
            assert handler.loki_url == "http://loki:3100"

    def test_init_from_arg(self) -> None:
        handler = LokiHandler("http://custom:3100")
        assert handler.loki_url == "http://custom:3100"

    def test_disabled_when_env_false(self) -> None:
        with patch.dict("os.environ", {"ENABLE_LOKI": "false"}):
            handler = LokiHandler()
            assert handler.enabled is False

    def test_create_payload_structure(self) -> None:
        handler = LokiHandler("http://loki:3100")
        event = {
            "event": "chat.completed",
            "tenant_id": "t1",
            "correlation_id": "abc-123",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        payload = handler._create_payload(event)

        assert "streams" in payload
        assert len(payload["streams"]) == 1
        stream = payload["streams"][0]
        assert stream["stream"]["tenant_id"] == "t1"
        assert stream["stream"]["event_type"] == "chat.completed"
        assert stream["stream"]["correlation_id"] == "abc-123"
        assert len(stream["values"]) == 1

    def test_send_success(self) -> None:
        handler = LokiHandler("http://loki:3100")
        handler.enabled = True

        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        with patch("openjarvis.cityos.loki_handler.urlopen", return_value=mock_response):
            result = handler.send({"event": "test", "tenant_id": "t1"})

        assert result is True

    def test_send_failure(self) -> None:
        handler = LokiHandler("http://loki:3100")
        handler.enabled = True

        with patch("urllib.request.urlopen") as mock_urlopen:
            from urllib.error import URLError
            mock_urlopen.side_effect = URLError("Connection refused")
            result = handler.send({"event": "test", "tenant_id": "t1"})

        assert result is False

    def test_send_when_disabled(self) -> None:
        handler = LokiHandler("http://loki:3100")
        handler.enabled = False

        result = handler.send({"event": "test", "tenant_id": "t1"})
        assert result is False

    def test_send_batch_groups_by_labels(self) -> None:
        handler = LokiHandler("http://loki:3100")
        handler.enabled = True

        events = [
            {"event": "chat", "tenant_id": "t1", "correlation_id": "a"},
            {"event": "chat", "tenant_id": "t1", "correlation_id": "b"},
            {"event": "voice", "tenant_id": "t2", "correlation_id": "c"},
        ]

        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        with patch("openjarvis.cityos.loki_handler.urlopen", return_value=mock_response):
            result = handler.send_batch(events)

        assert result is True

    def test_send_batch_empty(self) -> None:
        handler = LokiHandler("http://loki:3100")
        handler.enabled = True

        result = handler.send_batch([])
        assert result is False

    def test_tenant_label_on_all_events(self) -> None:
        handler = LokiHandler("http://loki:3100")
        event = {"event": "test", "tenant_id": "tenant-42"}

        payload = handler._create_payload(event)
        assert payload["streams"][0]["stream"]["tenant_id"] == "tenant-42"

    def test_unknown_tenant_defaults(self) -> None:
        handler = LokiHandler("http://loki:3100")
        event = {"event": "test"}  # No tenant_id

        payload = handler._create_payload(event)
        assert payload["streams"][0]["stream"]["tenant_id"] == "unknown"

    def test_timestamp_is_nanoseconds(self) -> None:
        handler = LokiHandler("http://loki:3100")
        event = {"event": "test", "tenant_id": "t1"}

        payload = handler._create_payload(event)
        ts_str = payload["streams"][0]["values"][0][0]
        ts = int(ts_str)

        # Should be nanoseconds (much larger than milliseconds)
        assert ts > 1e15
        assert ts < 1e20
