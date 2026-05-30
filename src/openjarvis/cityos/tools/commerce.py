"""Commerce tool: product catalog, order status."""

from __future__ import annotations

from typing import Any

from .base import CityOSTool


class CommerceTool(CityOSTool):
    name = "commerce_product_search"
    description = "Search the product catalog by keyword or category."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword"},
            "category": {"type": "string", "description": "Product category filter"},
            "limit": {"type": "integer", "description": "Max results", "default": 10},
        },
        "required": ["query"],
    }

    def run(self, params: dict[str, Any], tenant_id: str | None = None) -> dict[str, Any]:
        query = params.get("query", "")
        # TODO: Integrate with Medusa commerce API
        return {
            "success": True,
            "query": query,
            "results": [
                {"id": "prod_1", "name": f"Result for {query}", "price": 100, "currency": "SAR"}
            ],
            "total": 1,
        }
