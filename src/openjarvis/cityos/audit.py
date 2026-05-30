"""Audit logging for CityOS compliance.

Every request to CityOSJarvis is logged in a structured, append-only
format compatible with CityOS BFF audit trails.

Log format (JSON Lines):
    {
        "timestamp": "2026-05-30T12:00:00Z",
        "event": "chat.completion",
        "actor": {"sub": "uuid", "tenant_id": "tenant-42"},
        "request": {"model": "ollama", "messages_count": 3},
        "response": {"status": "success", "tokens_used": 150},
        "tools_called": ["governance.lookup_permit"],
        "latency_ms": 420,
        "compliance": {"classified_as": "public", "gate_passed": true}
    }
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .tenant import TenantContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AuditEvent:
    """A single audit event."""

    timestamp: str
    event: str
    actor: dict[str, Any]
    request: dict[str, Any]
    response: dict[str, Any] | None = None
    tools_called: list[str] = field(default_factory=list)
    latency_ms: float | None = None
    compliance: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None


class CityOSAuditLogger:
    """Append-only audit logger for CityOSJarvis.

    Writes to a JSON Lines file. In production, this should be
    forwarded to CityOS's centralized audit store (Loki, PostgreSQL).
    """

    def __init__(self, log_dir: str | None = None) -> None:
        self._log_dir = Path(log_dir or os.environ.get("CITYOS_AUDIT_DIR", "/var/log/cityosjarvis"))
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._file = self._log_dir / "audit.jsonl"

    def log(
        self,
        *,
        event: str,
        tenant: TenantContext | None,
        request: dict[str, Any],
        response: dict[str, Any] | None = None,
        tools_called: list[str] | None = None,
        latency_ms: float | None = None,
        compliance: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Append a single audit event."""
        actor: dict[str, Any] = {}
        if tenant:
            actor = tenant.to_log_dict()

        audit_event = AuditEvent(
            timestamp=self._now_iso(),
            event=event,
            actor=actor,
            request=self._sanitize(request),
            response=self._sanitize(response) if response else None,
            tools_called=tools_called or [],
            latency_ms=latency_ms,
            compliance=compliance or {},
            correlation_id=correlation_id,
        )

        try:
            with self._file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(audit_event), ensure_ascii=False, default=str) + "\n")
        except OSError as e:
            logger.error("Failed to write audit log: %s", e)

    def _now_iso(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def _sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove any raw message content to avoid storing PII in audit logs."""
        # Deep copy and redact message content
        sanitized = {}
        for key, value in data.items():
            if key in ("content", "text", "prompt") and isinstance(value, str):
                sanitized[key] = f"[REDACTED:{len(value)}chars]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    def query(
        self,
        *,
        tenant_id: str | None = None,
        event_type: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query audit logs (read-only, for compliance review)."""
        results: list[dict[str, Any]] = []
        if not self._file.exists():
            return results

        try:
            with self._file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if tenant_id and record.get("actor", {}).get("tenant_id") != tenant_id:
                        continue
                    if event_type and record.get("event") != event_type:
                        continue
                    if since and record.get("timestamp", "") < since:
                        continue

                    results.append(record)
                    if len(results) >= limit:
                        break
        except OSError as e:
            logger.error("Failed to read audit log: %s", e)

        return results
