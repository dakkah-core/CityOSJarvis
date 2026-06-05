"""Tests for Grafana Loki log forwarding."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from openjarvis.cityos.loki_handler import LokiHandler


class TestLokiHandler:
    @pytest.fixture
    def handler(self):
        return LokiHandler(loki_url="http://localhost:3100")

    def test_init(self, handler: LokiHandler) -> None:
        assert handler.push_url == "http://localhost:3100/loki/api/v1/push"
        assert handler.loki_url == "http://localhost:3100"
        assert handler.enabled is True

    def test_default_url_from_env(self) -> None:
        with patch.dict(os.environ, {"LOKI_URL": "http://loki:3100"}):
            h = LokiHandler()
            assert h.loki_url == "http://loki:3100"

    def test_disabled_when_env_set(self) -> None:
        with patch.dict(os.environ, {"ENABLE_LOKI": "false"}):
            h = LokiHandler()
            assert h.enabled is False

    def test_create_payload_structure(self, handler: LokiHandler) -> None:
        event = {
            "tenant_id": "t1",
            "correlation_id": "corr-123",
            "event": "chat.completed",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        payload = handler._create_payload(event)
        assert "streams" in payload
        assert len(payload["streams"]) == 1
        stream = payload["streams"][0]
        assert stream["stream"]["tenant_id"] == "t1"
        assert stream["stream"]["correlation_id"] == "corr-123"
        assert stream["stream"]["event_type"] == "chat.completed"
        assert len(stream["values"]) == 1
        # values are [timestamp_ns, line_json]
        assert len(stream["values"][0]) == 2

    def test_create_payload_default_correlation(self, handler: LokiHandler) -> None:
        event = {"tenant_id": "t1", "event": "test"}
        payload = handler._create_payload(event)
        stream = payload["streams"][0]
        assert stream["stream"]["correlation_id"] == "none"

    @patch("openjarvis.cityos.loki_handler.urlopen")
    def test_send_success(self, mock_urlopen, handler: LokiHandler) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        event = {
            "tenant_id": "t1",
            "correlation_id": "trace-123",
            "event": "chat.completed",
        }
        result = handler.send(event)
        assert result is True

    @patch("openjarvis.cityos.loki_handler.urlopen")
    def test_send_failure(self, mock_urlopen, handler: LokiHandler) -> None:
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        event = {"tenant_id": "t1", "event": "chat.completed"}
        result = handler.send(event)
        assert result is False

    def test_send_when_disabled(self, handler: LokiHandler) -> None:
        handler.enabled = False
        event = {"tenant_id": "t1", "event": "chat.completed"}
        result = handler.send(event)
        assert result is False

    @patch("openjarvis.cityos.loki_handler.urlopen")
    def test_send_batch_success(self, mock_urlopen, handler: LokiHandler) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        events = [
            {"tenant_id": "t1", "event": "chat.completed"},
            {"tenant_id": "t1", "event": "chat.completed"},
            {"tenant_id": "t2", "event": "voice.processed"},
        ]
        result = handler.send_batch(events)
        assert result is True

    def test_send_batch_empty(self, handler: LokiHandler) -> None:
        result = handler.send_batch([])
        assert result is False

    def test_send_batch_when_disabled(self, handler: LokiHandler) -> None:
        handler.enabled = False
        result = handler.send_batch([{"tenant_id": "t1", "event": "test"}])
        assert result is False
