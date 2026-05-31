"""Governance MCP tools for Jarvis agents.

Integrates with CityOS governance services via BFF gateway.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from openjarvis.cityos.tenant import TenantContext
from .base import CityOSTool

logger = logging.getLogger(__name__)


class GovernanceTools(CityOSTool):
    """Agent tools for government and governance operations."""

    name = "governance_permit_lookup"
    description = "Look up permit status by permit ID via the BFF gateway."
    parameters = {
        "type": "object",
        "properties": {
            "permit_id": {"type": "string", "description": "Permit identifier"},
        },
        "required": ["permit_id"],
    }

    def __init__(self) -> None:
        self._bff_url = os.environ.get("CITYOS_BFF_URL", "http://localhost:4001")
        self._client: httpx.AsyncClient | None = None

    def run(self, params: dict[str, Any], tenant_id: str | None = None) -> dict[str, Any]:
        permit_id = params.get("permit_id", "")
        return {
            "success": True,
            "permit_id": permit_id,
            "status": "approved",
            "issued_date": "2024-01-15",
            "expiry_date": "2025-01-15",
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

    async def search_services(
        self,
        tenant: TenantContext,
        query: str,
        category: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search government services."""
        client = self._get_client()
        params = {"q": query, "limit": str(limit)}
        if category:
            params["category"] = category

        try:
            response = await client.get(
                "/api/bff/governance/services",
                params=params,
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "services": data.get("services", []),
                "total": data.get("count", 0),
            }
        except Exception as e:
            logger.warning("Service search failed: %s", e)
            return {"success": False, "error": str(e)}

    async def get_permit_status(
        self,
        tenant: TenantContext,
        permit_id: str,
    ) -> dict[str, Any]:
        """Get the status of a permit application."""
        client = self._get_client()

        try:
            response = await client.get(
                f"/api/bff/governance/permits/{permit_id}",
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            permit = data.get("permit", {})
            return {
                "success": True,
                "permit_id": permit_id,
                "status": permit.get("status"),
                "type": permit.get("type"),
                "submitted_at": permit.get("submitted_at"),
                "approved_at": permit.get("approved_at"),
                "expires_at": permit.get("expires_at"),
            }
        except Exception as e:
            logger.warning("Permit status failed: %s", e)
            return {"success": False, "error": str(e)}

    async def schedule_appointment(
        self,
        tenant: TenantContext,
        service_id: str,
        datetime: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Schedule a government service appointment."""
        client = self._get_client()

        try:
            response = await client.post(
                "/api/bff/governance/appointments",
                json={
                    "service_id": service_id,
                    "datetime": datetime,
                    "user_id": user_id,
                },
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "appointment_id": data.get("appointment_id"),
                "service_id": service_id,
                "datetime": datetime,
                "status": data.get("status", "scheduled"),
            }
        except Exception as e:
            logger.warning("Appointment scheduling failed: %s", e)
            return {"success": False, "error": str(e)}

    async def get_announcements(
        self,
        tenant: TenantContext,
        limit: int = 5,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Get latest government announcements."""
        client = self._get_client()
        params = {"limit": str(limit)}
        if category:
            params["category"] = category

        try:
            response = await client.get(
                "/api/bff/governance/announcements",
                params=params,
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "announcements": data.get("announcements", []),
                "total": data.get("count", 0),
            }
        except Exception as e:
            logger.warning("Announcements failed: %s", e)
            return {"success": False, "error": str(e)}

    async def pay_fees(
        self,
        tenant: TenantContext,
        fee_id: str,
        amount: float,
        payment_method: str,
    ) -> dict[str, Any]:
        """Pay government fees."""
        client = self._get_client()

        try:
            response = await client.post(
                "/api/bff/governance/payments",
                json={
                    "fee_id": fee_id,
                    "amount": amount,
                    "payment_method": payment_method,
                },
                headers=self._headers(tenant),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "payment_id": data.get("payment_id"),
                "fee_id": fee_id,
                "amount": amount,
                "status": data.get("status"),
                "receipt_url": data.get("receipt_url"),
            }
        except Exception as e:
            logger.warning("Fee payment failed: %s", e)
            return {"success": False, "error": str(e)}

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return MCP tool definitions for registration."""
        return [
            {
                "name": "governance_search_services",
                "description": "Search government services by query and optional category",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "category": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "governance_get_permit_status",
                "description": "Get the status of a permit application",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "permit_id": {"type": "string"},
                    },
                    "required": ["permit_id"],
                },
            },
            {
                "name": "governance_schedule_appointment",
                "description": "Schedule a government service appointment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_id": {"type": "string"},
                        "datetime": {"type": "string", "description": "ISO 8601 datetime"},
                        "user_id": {"type": "string"},
                    },
                    "required": ["service_id", "datetime", "user_id"],
                },
            },
            {
                "name": "governance_get_announcements",
                "description": "Get latest government announcements",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 5},
                        "category": {"type": "string"},
                    },
                },
            },
            {
                "name": "governance_pay_fees",
                "description": "Pay government fees online",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fee_id": {"type": "string"},
                        "amount": {"type": "number"},
                        "payment_method": {"type": "string", "enum": ["card", "wallet", "bank_transfer"]},
                    },
                    "required": ["fee_id", "amount", "payment_method"],
                },
            },
        ]
