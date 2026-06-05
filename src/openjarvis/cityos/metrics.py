"""Prometheus metrics for CityOSJarvis.

Exposes:
- Request count by method, endpoint, status
- Request latency histogram
- Active connections gauge
- Compliance gate results counter
- Chat metrics (tokens, conversations, messages)
- Voice metrics (queries, languages, duration)
- Tool execution metrics (calls, latency, errors)
- LLM provider health (up/down, fallback activations)
- Prompt guard metrics (blocked, warned, allowed)
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# ── HTTP Request metrics ──────────────────────────────────────────────────────

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

# ── Chat metrics ──────────────────────────────────────────────────────────────

CHAT_REQUESTS = Counter(
    "cityosjarvis_chat_requests_total",
    "Total chat requests",
    ["tenant_id", "agent_id", "model"],
)

CHAT_TOKENS = Histogram(
    "cityosjarvis_chat_tokens_used",
    "Tokens used per chat completion",
    ["tenant_id", "model"],
    buckets=[10, 50, 100, 250, 500, 1000, 2000, 4000, 8000],
)

CHAT_MESSAGES = Counter(
    "cityosjarvis_chat_messages_total",
    "Total chat messages sent/received",
    ["tenant_id", "role"],
)

CONVERSATIONS_ACTIVE = Gauge(
    "cityosjarvis_conversations_active",
    "Number of active conversations",
    ["tenant_id"],
)

CHAT_DURATION = Histogram(
    "cityosjarvis_chat_duration_seconds",
    "Chat completion duration",
    ["tenant_id", "model", "stream"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

# ── Voice metrics ─────────────────────────────────────────────────────────────

VOICE_QUERIES = Counter(
    "cityosjarvis_voice_queries_total",
    "Total voice queries",
    ["tenant_id", "language", "intent"],
)

VOICE_DURATION = Histogram(
    "cityosjarvis_voice_duration_seconds",
    "Voice query duration",
    ["tenant_id", "language"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

VOICE_CONFIDENCE = Histogram(
    "cityosjarvis_voice_confidence",
    "Voice recognition confidence",
    ["tenant_id", "language"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# ── Tool execution metrics ────────────────────────────────────────────────────

TOOL_CALLS = Counter(
    "cityosjarvis_tool_calls_total",
    "Total tool calls",
    ["tenant_id", "tool_name", "agent_id", "status"],
)

TOOL_LATENCY = Histogram(
    "cityosjarvis_tool_duration_seconds",
    "Tool execution duration",
    ["tenant_id", "tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ── LLM Provider metrics ──────────────────────────────────────────────────────

PROVIDER_HEALTH = Gauge(
    "cityosjarvis_provider_up",
    "LLM provider health (1 = up, 0 = down)",
    ["provider", "model"],
)

PROVIDER_FALLBACKS = Counter(
    "cityosjarvis_provider_fallbacks_total",
    "Total fallback activations",
    ["from_provider", "to_provider", "reason"],
)

PROVIDER_LATENCY = Histogram(
    "cityosjarvis_provider_latency_seconds",
    "LLM provider response latency",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

PROVIDER_ERRORS = Counter(
    "cityosjarvis_provider_errors_total",
    "LLM provider errors",
    ["provider", "model", "error_type"],
)

# ── Prompt Guard metrics ──────────────────────────────────────────────────────

PROMPT_GUARD_SCANS = Counter(
    "cityosjarvis_prompt_guard_scans_total",
    "Total prompt guard scans",
    ["tenant_id", "action"],
)

PROMPT_GUARD_SCORE = Histogram(
    "cityosjarvis_prompt_guard_risk_score",
    "Prompt guard risk score distribution",
    ["tenant_id"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# ── Compliance metrics ────────────────────────────────────────────────────────

COMPLIANCE_CHECKS = Counter(
    "cityosjarvis_compliance_checks_total",
    "Total compliance checks",
    ["result", "category"],
)

PII_REDACTIONS = Counter(
    "cityosjarvis_pii_redactions_total",
    "Total PII redactions",
    ["tenant_id", "pii_type"],
)

# ── Storage metrics ───────────────────────────────────────────────────────────

STORAGE_UPLOADS = Counter(
    "cityosjarvis_storage_uploads_total",
    "Total file uploads",
    ["tenant_id", "purpose", "fallback"],
)

STORAGE_DOWNLOADS = Counter(
    "cityosjarvis_storage_downloads_total",
    "Total file downloads",
    ["tenant_id", "purpose"],
)

# ── Search metrics ────────────────────────────────────────────────────────────

SEARCH_QUERIES = Counter(
    "cityosjarvis_search_queries_total",
    "Total search queries",
    ["tenant_id", "index_type"],
)

SEARCH_LATENCY = Histogram(
    "cityosjarvis_search_duration_seconds",
    "Search query duration",
    ["tenant_id", "index_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
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
            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()
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
