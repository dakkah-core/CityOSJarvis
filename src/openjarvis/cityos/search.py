"""Meilisearch indexer for Jarvis conversations and content.

Indexes AI conversations, generated reports, and uploaded documents
so they are searchable from CityOS portals.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from openjarvis.cityos.tenant import TenantContext

logger = logging.getLogger(__name__)


class CityOSSearch:
    """Meilisearch integration for Jarvis content.

    Index naming: jarvis_{tenant_id}_conversations
    """

    def __init__(self) -> None:
        self._url = os.environ.get("MEILISEARCH_URL", "http://localhost:7700")
        self._api_key = os.environ.get("MEILISEARCH_MASTER_KEY", "")
        self._client = None

    def _get_client(self) -> Any | None:  # noqa: ANN401
        if self._client is not None:
            return self._client
        try:
            import meilisearch

            self._client = meilisearch.Client(self._url, self._api_key)
            return self._client
        except Exception as e:
            logger.warning("Meilisearch client creation failed: %s", e)
            return None

    def _index_name(self, tenant_id: str, index_type: str) -> str:
        safe = tenant_id.replace("/", "_").lower()
        return f"jarvis_{safe}_{index_type}"

    async def index_conversation(
        self,
        tenant: TenantContext,
        conversation_id: str,
        messages: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Index a conversation for search."""
        client = self._get_client()
        if client is None:
            return False

        index_name = self._index_name(tenant.tenant_id, "conversations")

        try:
            # Create index if it doesn't exist
            try:
                client.create_index(index_name, {"primaryKey": "id"})
            except Exception:
                pass  # Index already exists

            index = client.index(index_name)

            # Build searchable document
            content = "\n".join(
                f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                for m in messages
            )

            doc = {
                "id": conversation_id,
                "tenant_id": tenant.tenant_id,
                "node_path": tenant.node_path,
                "content": content,
                "message_count": len(messages),
                "updated_at": metadata.get("updated_at") if metadata else None,
                "agent_id": metadata.get("agent_id") if metadata else None,
            }

            index.add_documents([doc])
            logger.info("Indexed conversation %s for tenant %s", conversation_id, tenant.tenant_id)
            return True
        except Exception as e:
            logger.warning("Failed to index conversation: %s", e)
            return False

    async def search_conversations(
        self,
        tenant: TenantContext,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search conversations for a tenant."""
        client = self._get_client()
        if client is None:
            return []

        index_name = self._index_name(tenant.tenant_id, "conversations")

        try:
            index = client.index(index_name)
            results = index.search(query, {"limit": limit, "filter": f"tenant_id = {tenant.tenant_id}"})
            return results.get("hits", [])
        except Exception as e:
            logger.warning("Search failed: %s", e)
            return []

    async def delete_conversation(self, tenant: TenantContext, conversation_id: str) -> bool:
        """Delete a conversation from the search index."""
        client = self._get_client()
        if client is None:
            return False

        index_name = self._index_name(tenant.tenant_id, "conversations")

        try:
            index = client.index(index_name)
            index.delete_document(conversation_id)
            return True
        except Exception as e:
            logger.warning("Failed to delete conversation from index: %s", e)
            return False
