"""Fleet MCP tools for Jarvis agents.

Integrates with Fleetbase backend via BFF gateway.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from openjarvis.cityos.tenant import TenantContext

logger = logging.getLogger(__name__)


class FleetTools:
    """Agent tools for fleet management operations."""

    def __init__(self) -> None:
        self._bff_url = os.environ.get("CITYOS_BFF_URL", "http://localhost:4001")
        self._client: httpx.AsyncClient | None = None

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

    async def get_vehicle_status(
        self,
        tenant: TenantContext,
        vehicle_id: str,
    ) -> dict[str, Any]:
        """Get real-time vehicle status."""
        client = self._get_client()

        try:
            response = await client.get(
                f"/api/bff/fleet/vehicles/{vehicle_id}",
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            vehicle = data.get("vehicle", {})
            return {
                "success": True,
                "vehicle_id": vehicle_id,
                "status": vehicle.get("status"),
                "location": vehicle.get("location"),
                "driver": vehicle.get("driver"),
                "fuel_level": vehicle.get("fuel_level"),
                "last_updated": vehicle.get("updated_at"),
            }
        except Exception as e:
            logger.warning("Vehicle status failed: %s", e)
            return {"success": False, "error": str(e)}

    async def optimize_route(
        self,
        tenant: TenantContext,
        waypoints: list[dict[str, float]],
        optimize_for: str = "time",
    ) -> dict[str, Any]:
        """Optimize a route for given waypoints."""
        client = self._get_client()

        try:
            response = await client.post(
                "/api/bff/fleet/routes/optimize",
                json={"waypoints": waypoints, "optimize_for": optimize_for},
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "route": data.get("route"),
                "distance_km": data.get("distance_km"),
                "duration_min": data.get("duration_min"),
                "waypoints": data.get("waypoints", []),
            }
        except Exception as e:
            logger.warning("Route optimization failed: %s", e)
            return {"success": False, "error": str(e)}

    async def get_driver_schedule(
        self,
        tenant: TenantContext,
        driver_id: str,
        date: str | None = None,
    ) -> dict[str, Any]:
        """Get driver schedule for a date."""
        client = self._get_client()
        params = {}
        if date:
            params["date"] = date

        try:
            response = await client.get(
                f"/api/bff/fleet/drivers/{driver_id}/schedule",
                params=params,
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "driver_id": driver_id,
                "date": date,
                "shifts": data.get("shifts", []),
                "trips": data.get("trips", []),
                "hours_worked": data.get("hours_worked", 0),
            }
        except Exception as e:
            logger.warning("Driver schedule failed: %s", e)
            return {"success": False, "error": str(e)}

    async def report_incident(
        self,
        tenant: TenantContext,
        vehicle_id: str,
        driver_id: str,
        incident_type: str,
        description: str,
        location: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Report a fleet incident."""
        client = self._get_client()

        try:
            response = await client.post(
                "/api/bff/fleet/incidents",
                json={
                    "vehicle_id": vehicle_id,
                    "driver_id": driver_id,
                    "type": incident_type,
                    "description": description,
                    "location": location,
                },
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "incident_id": data.get("incident_id"),
                "status": data.get("status", "reported"),
            }
        except Exception as e:
            logger.warning("Incident report failed: %s", e)
            return {"success": False, "error": str(e)}

    async def get_maintenance_alerts(
        self,
        tenant: TenantContext,
        severity: str | None = None,
    ) -> dict[str, Any]:
        """Get vehicle maintenance alerts."""
        client = self._get_client()
        params = {}
        if severity:
            params["severity"] = severity

        try:
            response = await client.get(
                "/api/bff/fleet/maintenance/alerts",
                params=params,
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "alerts": data.get("alerts", []),
                "total": data.get("count", 0),
            }
        except Exception as e:
            logger.warning("Maintenance alerts failed: %s", e)
            return {"success": False, "error": str(e)}

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return MCP tool definitions for registration."""
        return [
            {
                "name": "fleet_get_vehicle_status",
                "description": "Get real-time status of a vehicle",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vehicle_id": {"type": "string"},
                    },
                    "required": ["vehicle_id"],
                },
            },
            {
                "name": "fleet_optimize_route",
                "description": "Optimize a route for given waypoints",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "waypoints": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "lat": {"type": "number"},
                                    "lng": {"type": "number"},
                                },
                            },
                        },
                        "optimize_for": {"type": "string", "enum": ["time", "distance", "fuel"], "default": "time"},
                    },
                    "required": ["waypoints"],
                },
            },
            {
                "name": "fleet_get_driver_schedule",
                "description": "Get driver schedule for a date",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "driver_id": {"type": "string"},
                        "date": {"type": "string", "description": "YYYY-MM-DD"},
                    },
                    "required": ["driver_id"],
                },
            },
            {
                "name": "fleet_report_incident",
                "description": "Report a fleet incident",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "vehicle_id": {"type": "string"},
                        "driver_id": {"type": "string"},
                        "incident_type": {"type": "string", "enum": ["accident", "breakdown", "violation", "theft", "other"]},
                        "description": {"type": "string"},
                        "location": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lng": {"type": "number"},
                            },
                        },
                    },
                    "required": ["vehicle_id", "driver_id", "incident_type", "description"],
                },
            },
            {
                "name": "fleet_get_maintenance_alerts",
                "description": "Get vehicle maintenance alerts",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    },
                },
            },
        ]
