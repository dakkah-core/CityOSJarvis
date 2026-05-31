"""Event bridge between OpenJarvis internal EventBus and CityOS outbox/events.

Publishes Jarvis AI events (chat completions, tool executions, voice queries)
to the CityOS event bus so other domains can react.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from starlette.requests import Request

from openjarvis.cityos.tenant import TenantContext

logger = logging.getLogger(__name__)


class CityOSEventBridge:
    """Bridge Jarvis internal events to CityOS outbox.

    In production, this publishes to:
    - Redis Pub/Sub (cityos-events)
    - CityOS Outbox table (Postgres)
    - Kuzzle realtime (for mobile push)

    Falls back to no-op if CityOS services are not available.
    """

    def __init__(self) -> None:
        self._redis_url = os.environ.get("REDIS_URL", "")
        self._kuzzle_url = os.environ.get("KUZZLE_URL", "")
        self._postgres_dsn = os.environ.get("DATABASE_URL", "")
        self._redis = None
        self._kuzzle = None

    async def _get_redis(self) -> Any | None:  # noqa: ANN401
        if self._redis is not None:
            return self._redis
        if not self._redis_url:
            return None
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            return self._redis
        except Exception as e:
            logger.warning("Redis not available for event bridge: %s", e)
            return None

    async def _publish_redis(self, channel: str, payload: dict[str, Any]) -> None:
        r = await self._get_redis()
        if r is None:
            return
        try:
            await r.publish(channel, json.dumps(payload))
        except Exception as e:
            logger.warning("Redis publish failed: %s", e)

    async def _publish_kuzzle(self, index: str, collection: str, document: dict[str, Any]) -> None:
        if not self._kuzzle_url:
            return
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self._kuzzle_url}/cityos/{collection}/_create",
                    json=document,
                    headers={"Content-Type": "application/json"},
                )
        except Exception as e:
            logger.warning("Kuzzle publish failed: %s", e)

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        tenant: TenantContext | None = None,
        request: Request | None = None,
    ) -> None:
        """Publish a Jarvis event to CityOS infrastructure.

        Args:
            event_type: Dot-namespaced event type, e.g. "jarvis.chat.completed"
            payload: Event payload dict
            tenant: Optional tenant context for scoping
            request: Optional request for correlation ID
        """
        envelope = {
            "event": event_type,
            "timestamp": payload.get("timestamp") or __import__("time").time(),
            "payload": payload,
            "source": "jarvis",
            "version": "1.0",
        }

        if tenant:
            envelope["tenant_id"] = tenant.tenant_id
            envelope["node_path"] = tenant.node_path
            envelope["user_sub"] = tenant.user_sub

        if request:
            corr = request.headers.get("X-Correlation-Id")
            if corr:
                envelope["correlation_id"] = corr

        # Publish to Redis (cityos-events channel)
        await self._publish_redis("cityos:events", envelope)
        await self._publish_redis(f"cityos:events:{tenant.tenant_id if tenant else 'default'}", envelope)

        # Publish to Kuzzle (realtime for mobile)
        await self._publish_kuzzle(
            "cityos",
            "jarvis_events",
            {
                "event": event_type,
                "tenant_id": tenant.tenant_id if tenant else "default",
                "payload": payload,
            },
        )

        logger.debug("Published event %s to CityOS", event_type)

    async def publish_chat_completed(
        self,
        tenant: TenantContext,
        conversation_id: str,
        message_count: int,
        tokens_used: int,
        request: Request | None = None,
    ) -> None:
        """Publish a chat completion event."""
        await self.publish(
            "jarvis.chat.completed",
            {
                "conversation_id": conversation_id,
                "message_count": message_count,
                "tokens_used": tokens_used,
            },
            tenant=tenant,
            request=request,
        )

    async def publish_tool_executed(
        self,
        tenant: TenantContext,
        tool_name: str,
        agent_id: str,
        success: bool,
        duration_ms: float,
        request: Request | None = None,
    ) -> None:
        """Publish a tool execution event."""
        await self.publish(
            "jarvis.tool.executed",
            {
                "tool_name": tool_name,
                "agent_id": agent_id,
                "success": success,
                "duration_ms": duration_ms,
            },
            tenant=tenant,
            request=request,
        )

    async def publish_voice_query(
        self,
        tenant: TenantContext,
        intent: str,
        confidence: float,
        language: str,
        request: Request | None = None,
    ) -> None:
        """Publish a voice query event."""
        await self.publish(
            "jarvis.voice.query",
            {
                "intent": intent,
                "confidence": confidence,
                "language": language,
            },
            tenant=tenant,
            request=request,
        )
