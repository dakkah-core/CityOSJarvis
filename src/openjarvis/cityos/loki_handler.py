"""Loki log forwarding integration for CityOSJarvis audit logs.

Forwards structured audit events to Grafana Loki for centralized log aggregation.
Uses tenant_id and correlation_id as labels for efficient querying.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class LokiHandler:
    """Forwards audit logs to Grafana Loki."""

    def __init__(self, loki_url: str | None = None) -> None:
        self.loki_url = (
            loki_url or os.environ.get("LOKI_URL", "http://localhost:3100")
        ).rstrip("/")
        self.push_url = f"{self.loki_url}/loki/api/v1/push"
        self.enabled = os.environ.get("ENABLE_LOKI", "true").lower() == "true"
        if not self.enabled:
            logger.info("Loki forwarding disabled")

    def _create_payload(self, event: dict[str, Any]) -> dict[str, Any]:
        """Create Loki push payload from audit event."""
        ts_ns = str(int(time.time() * 1e9))
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))

        tenant_id = event.get("tenant_id", "unknown")
        correlation_id = event.get("correlation_id", "")
        event_type = event.get("event", "unknown")

        return {
            "streams": [
                {
                    "stream": {
                        "service": "cityosjarvis",
                        "job": "cityosjarvis-audit",
                        "tenant_id": str(tenant_id),
                        "event_type": str(event_type),
                        "correlation_id": str(correlation_id)
                        if correlation_id
                        else "none",
                    },
                    "values": [[ts_ns, line]],
                }
            ]
        }

    def send(self, event: dict[str, Any]) -> bool:
        """Send a single audit event to Loki."""
        if not self.enabled:
            return False

        payload = self._create_payload(event)
        data = json.dumps(payload).encode("utf-8")

        req = Request(
            self.push_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(req, timeout=5) as resp:
                if resp.status == 204:
                    logger.debug("Forwarded audit event to Loki")
                    return True
                logger.warning("Loki returned %s", resp.status)
                return False
        except URLError as e:
            logger.warning("Failed to forward to Loki: %s", e)
            return False

    def send_batch(self, events: list[dict[str, Any]]) -> bool:
        """Send multiple audit events to Loki in a single request."""
        if not self.enabled or not events:
            return False

        streams: dict[tuple[str, str, str], list[list[str]]] = {}

        for event in events:
            ts_ns = str(int(time.time() * 1e9))
            line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
            tenant_id = str(event.get("tenant_id", "unknown"))
            event_type = str(event.get("event", "unknown"))
            correlation_id = str(event.get("correlation_id", "")) or "none"
            key = (tenant_id, event_type, correlation_id)
            streams.setdefault(key, []).append([ts_ns, line])

        payload = {
            "streams": [
                {
                    "stream": {
                        "service": "cityosjarvis",
                        "job": "cityosjarvis-audit",
                        "tenant_id": key[0],
                        "event_type": key[1],
                        "correlation_id": key[2],
                    },
                    "values": values,
                }
                for key, values in streams.items()
            ]
        }

        data = json.dumps(payload).encode("utf-8")
        req = Request(
            self.push_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(req, timeout=10) as resp:
                return resp.status == 204
        except URLError as e:
            logger.warning("Failed to forward batch to Loki: %s", e)
            return False
