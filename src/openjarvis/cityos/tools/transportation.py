"""Transportation tool: route lookup, traffic status."""

from __future__ import annotations

from typing import Any

from .base import CityOSTool


class TransportationTool(CityOSTool):
    name = "transportation_route_lookup"
    description = "Find public transportation routes between two locations."
    parameters = {
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "Starting location"},
            "destination": {"type": "string", "description": "Destination location"},
            "mode": {
                "type": "string",
                "enum": ["bus", "metro", "taxi", "any"],
                "default": "any",
            },
        },
        "required": ["origin", "destination"],
    }

    def run(self, params: dict[str, Any], tenant_id: str | None = None) -> dict[str, Any]:
        origin = params.get("origin", "")
        destination = params.get("destination", "")
        # TODO: Integrate with CityOS transportation API
        return {
            "success": True,
            "origin": origin,
            "destination": destination,
            "routes": [
                {
                    "mode": "metro",
                    "duration_minutes": 25,
                    "transfers": 1,
                    "fare_sar": 4,
                }
            ],
        }
