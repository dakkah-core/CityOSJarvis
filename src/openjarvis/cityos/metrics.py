"""Prometheus metrics for CityOSJarvis.

Exposes:
- Request count by method, endpoint, status
- Request latency histogram
- Active connections gauge
- Compliance gate results counter
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Request metrics
REQUEST_COUNT = Counter(
    "cityosjarvis_requests_total",
    "Total requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "cityosjarvis_request_duration_seconds",
    "Request latency",
    ["method", "endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ACTIVE_CONNECTIONS = Gauge(
    "cityosjarvis_active_connections",
    "Number of active connections",
)

# Compliance metrics
COMPLIANCE_CHECKS = Counter(
    "cityosjarvis_compliance_checks_total",
    "Total compliance checks",
    ["result", "category"],
)

# Chat metrics
CHAT_TOKENS = Histogram(
    "cityosjarvis_chat_tokens_used",
    "Tokens used per chat completion",
    ["model"],
    buckets=[10, 50, 100, 250, 500, 1000, 2000, 4000, 8000],
)


class MetricsMiddleware:
    """ASGI middleware that records request count and latency."""

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "unknown")

        # Simplify endpoint label (remove IDs)
        endpoint = _simplify_path(path)

        ACTIVE_CONNECTIONS.inc()
        start = time.perf_counter()

        status_code = "500"

        async def wrapped_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = str(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, receive, wrapped_send)
        finally:
            latency = time.perf_counter() - start
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
            ACTIVE_CONNECTIONS.dec()


def _simplify_path(path: str) -> str:
    """Replace path parameters with placeholders for metric labels."""
    parts = path.split("/")
    simplified = []
    for part in parts:
        if part and part not in ("v1", "api", "health") and len(part) > 20:
            # Likely an ID
            simplified.append("{id}")
        else:
            simplified.append(part)
    return "/".join(simplified) or "/"


def metrics_endpoint() -> Response:
    """Return Prometheus metrics."""
    from fastapi.responses import Response as FastAPIResponse
    return FastAPIResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
