"""Tests for Prometheus metrics collection."""

from __future__ import annotations

import pytest

from openjarvis.cityos.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    ACTIVE_CONNECTIONS,
    COMPLIANCE_CHECKS,
    CHAT_TOKENS,
    MetricsMiddleware,
)


class TestPrometheusMetrics:
    def test_request_count_exists(self) -> None:
        assert REQUEST_COUNT is not None
        assert "cityosjarvis_requests" in REQUEST_COUNT._name

    def test_request_latency_exists(self) -> None:
        assert REQUEST_LATENCY is not None
        assert "cityosjarvis_request_duration" in REQUEST_LATENCY._name

    def test_active_connections_exists(self) -> None:
        assert ACTIVE_CONNECTIONS is not None
        assert "active_connections" in ACTIVE_CONNECTIONS._name

    def test_compliance_checks_exists(self) -> None:
        assert COMPLIANCE_CHECKS is not None
        assert "compliance_checks" in COMPLIANCE_CHECKS._name

    def test_chat_tokens_exists(self) -> None:
        assert CHAT_TOKENS is not None
        assert "chat_tokens" in CHAT_TOKENS._name

    def test_metrics_middleware_init(self) -> None:
        async def mock_app(scope, receive, send):
            pass

        middleware = MetricsMiddleware(mock_app)
        assert middleware is not None

    def test_request_count_labels(self) -> None:
        # Verify label names
        labels = list(REQUEST_COUNT._labelnames)
        assert "method" in labels
        assert "endpoint" in labels
        assert "status_code" in labels

    def test_request_latency_buckets(self) -> None:
        buckets = list(REQUEST_LATENCY._upper_bounds)
        assert 0.001 in buckets
        assert 10.0 in buckets

    def test_compliance_labels(self) -> None:
        labels = list(COMPLIANCE_CHECKS._labelnames)
        assert "result" in labels
        assert "category" in labels
