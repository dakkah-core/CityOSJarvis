"""Kuzzle real-time chat integration for CityOSJarvis.

Provides bidirectional WebSocket communication between Jarvis backend
and CityOS mobile/web clients via Kuzzle.

Usage:
    from openjarvis.cityos.kuzzle_chat import KuzzleChatManager

    manager = KuzzleChatManager()
    await manager.publish_message(
        conversation_id="conv-123",
        tenant_id="tenant-456",
        message={"role": "assistant", "content": "Hello!"}
    )
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class KuzzleChatManager:
    """Manages real-time chat messaging via Kuzzle.

    Rooms:
    - cityos:jarvis:chat:{conversation_id} — per-conversation room
    - cityos:jarvis:chat:{tenant_id} — per-tenant broadcast
    - cityos:jarvis:system — system-wide announcements
    """

    def __init__(self) -> None:
        self._kuzzle_url = os.environ.get("KUZZLE_URL", "http://localhost:7512")
        self._api_key = os.environ.get("KUZZLE_API_KEY", "")
        self._client: Any | None = None  # noqa: ANN401

    def _get_client(self) -> Any | None:  # noqa: ANN401
        if self._client is not None:
            return self._client
        try:
            import httpx

            self._client = httpx.AsyncClient(
                base_url=self._kuzzle_url,
                timeout=10.0,
                headers={"Content-Type": "application/json"},
            )
            return self._client
        except Exception as e:
            logger.warning("Kuzzle client creation failed: %s", e)
            return None

    def _room_id(self, conversation_id: str) -> str:
        return f"cityos:jarvis:chat:{conversation_id}"

    def _tenant_room_id(self, tenant_id: str) -> str:
        return f"cityos:jarvis:chat:{tenant_id}"

    async def publish_message(
        self,
        conversation_id: str,
        tenant_id: str,
        message: dict[str, Any],
        correlation_id: str | None = None,
    ) -> bool:
        """Publish a chat message to Kuzzle for real-time delivery.

        Args:
            conversation_id: The conversation ID
            tenant_id: The tenant ID
            message: Message dict with role, content, timestamp
            correlation_id: Optional correlation ID for tracing

        Returns:
            True if published successfully
        """
        client = self._get_client()
        if client is None:
            return False

        document = {
            "conversation_id": conversation_id,
            "tenant_id": tenant_id,
            "message": message,
            "timestamp": message.get("timestamp") or __import__("time").time(),
            "correlation_id": correlation_id,
        }

        try:
            response = await client.post(
                "/cityos/jarvis_messages/_create",
                json=document,
            )
            response.raise_for_status()
            logger.debug(
                "Published message to Kuzzle: conversation=%s tenant=%s",
                conversation_id,
                tenant_id,
            )
            return True
        except Exception as e:
            logger.warning("Kuzzle publish failed: %s", e)
            return False

    async def subscribe_to_conversation(
        self,
        conversation_id: str,
        callback: Any,  # noqa: ANN401
    ) -> bool:
        """Subscribe to a conversation room.

        Note: In production, this is handled by the client-side
        Kuzzle SDK (mobile/web), not the backend.
        """
        logger.info(
            "Subscription request for conversation=%s (handled client-side)",
            conversation_id,
        )
        return True

    async def notify_typing(
        self,
        conversation_id: str,
        tenant_id: str,
        user_id: str,
        is_typing: bool,
    ) -> bool:
        """Publish typing indicator."""
        return await self.publish_message(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            message={
                "role": "system",
                "type": "typing_indicator",
                "user_id": user_id,
                "is_typing": is_typing,
                "timestamp": __import__("time").time(),
            },
        )

    async def notify_presence(
        self,
        conversation_id: str,
        tenant_id: str,
        user_id: str,
        status: str,  # "online", "offline", "away"
    ) -> bool:
        """Publish user presence update."""
        return await self.publish_message(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            message={
                "role": "system",
                "type": "presence",
                "user_id": user_id,
                "status": status,
                "timestamp": __import__("time").time(),
            },
        )

    async def system_broadcast(
        self,
        tenant_id: str,
        notification_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """Broadcast a system notification to all users in a tenant."""
        client = self._get_client()
        if client is None:
            return False

        document = {
            "tenant_id": tenant_id,
            "type": notification_type,
            "payload": payload,
            "timestamp": __import__("time").time(),
        }

        try:
            response = await client.post(
                "/cityos/jarvis_notifications/_create",
                json=document,
            )
            response.raise_for_status()
            logger.info(
                "System broadcast to tenant=%s: type=%s",
                tenant_id,
                notification_type,
            )
            return True
        except Exception as e:
            logger.warning("Kuzzle broadcast failed: %s", e)
            return False
