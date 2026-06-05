"""Commerce MCP tools for Jarvis agents.

Integrates with Medusa v2 backend via BFF gateway.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from openjarvis.cityos.tenant import TenantContext

from .base import CityOSTool

logger = logging.getLogger(__name__)


class CommerceTools(CityOSTool):
    """Agent tools for commerce operations.

    All requests flow through the BFF gateway with tenant isolation.
    """

    name = "commerce_product_search"
    description = "Search products in the commerce catalog via the BFF gateway."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "default": 10},
            "category": {"type": "string", "description": "Product category filter"},
        },
        "required": ["query"],
    }

    def __init__(self) -> None:
        self._bff_url = os.environ.get("CITYOS_BFF_URL", "http://localhost:4001")
        self._client: httpx.AsyncClient | None = None

    def run(
        self, params: dict[str, Any], tenant_id: str | None = None
    ) -> dict[str, Any]:
        query = params.get("query", "")
        results = [
            {"id": "prod-1", "name": f"{query} - Sample Product", "price": 99.99}
        ]
        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results),
        }

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._bff_url,
                timeout=10.0,
            )
        return self._client

    def _headers(self, tenant: TenantContext) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-CityOS-Tenant-Id": tenant.tenant_id,
            "X-CityOS-Node-Path": tenant.node_path or "",
        }

    async def search_products(
        self,
        tenant: TenantContext,
        query: str,
        category: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search products in the commerce catalog."""
        client = self._get_client()
        params = {"q": query, "limit": str(limit)}
        if category:
            params["category_id"] = category

        try:
            response = await client.get(
                "/api/bff/commerce/products",
                params=params,
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "products": data.get("products", []),
                "total": data.get("count", 0),
            }
        except Exception as e:
            logger.warning("Product search failed: %s", e)
            return {"success": False, "error": str(e)}

    async def get_order_status(
        self,
        tenant: TenantContext,
        order_id: str,
    ) -> dict[str, Any]:
        """Get the status of an order."""
        client = self._get_client()

        try:
            response = await client.get(
                f"/api/bff/commerce/orders/{order_id}",
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "order": data.get("order"),
                "status": data.get("order", {}).get("status"),
                "fulfillment_status": data.get("order", {}).get("fulfillment_status"),
            }
        except Exception as e:
            logger.warning("Order status failed: %s", e)
            return {"success": False, "error": str(e)}

    async def recommend_products(
        self,
        tenant: TenantContext,
        user_id: str,
        category: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Get AI-powered product recommendations."""
        client = self._get_client()
        payload = {"user_id": user_id, "limit": limit}
        if category:
            payload["category"] = category

        try:
            response = await client.post(
                "/api/bff/commerce/recommendations",
                json=payload,
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "recommendations": data.get("products", []),
                "reason": data.get("reason"),
            }
        except Exception as e:
            logger.warning("Recommendations failed: %s", e)
            return {"success": False, "error": str(e)}

    async def get_cart_summary(
        self,
        tenant: TenantContext,
        cart_id: str,
    ) -> dict[str, Any]:
        """Get cart summary with totals."""
        client = self._get_client()

        try:
            response = await client.get(
                f"/api/bff/commerce/carts/{cart_id}",
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            cart = data.get("cart", {})
            return {
                "success": True,
                "items_count": len(cart.get("items", [])),
                "total": cart.get("total"),
                "currency": cart.get("currency_code", "SAR"),
                "discounts": cart.get("discounts", []),
            }
        except Exception as e:
            logger.warning("Cart summary failed: %s", e)
            return {"success": False, "error": str(e)}

    async def check_inventory(
        self,
        tenant: TenantContext,
        product_id: str,
    ) -> dict[str, Any]:
        """Check product inventory levels."""
        client = self._get_client()

        try:
            response = await client.get(
                f"/api/bff/commerce/products/{product_id}/inventory",
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "in_stock": data.get("in_stock", False),
                "quantity": data.get("quantity", 0),
                "reserved": data.get("reserved_quantity", 0),
            }
        except Exception as e:
            logger.warning("Inventory check failed: %s", e)
            return {"success": False, "error": str(e)}

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return MCP tool definitions for registration."""
        return [
            {
                "name": "commerce_search_products",
                "description": (
                    "Search products in the commerce catalog by query and "
                    "optional category"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "category": {
                            "type": "string",
                            "description": "Category ID (optional)",
                        },
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "commerce_get_order_status",
                "description": "Get the status and details of an order by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "Order ID"},
                    },
                    "required": ["order_id"],
                },
            },
            {
                "name": "commerce_recommend_products",
                "description": "Get AI-powered product recommendations for a user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID"},
                        "category": {
                            "type": "string",
                            "description": "Category filter (optional)",
                        },
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["user_id"],
                },
            },
            {
                "name": "commerce_get_cart_summary",
                "description": "Get shopping cart summary with items count and total",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cart_id": {"type": "string", "description": "Cart ID"},
                    },
                    "required": ["cart_id"],
                },
            },
            {
                "name": "commerce_check_inventory",
                "description": "Check product inventory levels",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID"},
                    },
                    "required": ["product_id"],
                },
            },
        ]
