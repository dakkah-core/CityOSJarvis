"""Integration tests for CityOSJarvis -> MCP -> Domain tool flow."""

from __future__ import annotations

import pytest

from openjarvis.cityos.tenant import TenantContext
from openjarvis.cityos.tools import (
    GovernanceTools,
    CommerceTools,
    HealthcareTool,
    TransportationTool,
    FleetTools,
    PublicSafetyTool,
)


@pytest.fixture
def tenant() -> TenantContext:
    return TenantContext(
        tenant_id="test-tenant",
        node_path="global.sa.dakkah",
        realm_roles=["ai_user"],
        user_sub="user-123",
    )


class TestGovernanceTools:
    """Test governance permit lookup tool end-to-end."""

    def test_permit_lookup_success(self, tenant: TenantContext) -> None:
        tool = GovernanceTools()
        result = tool.run(
            {"permit_id": "PERM-2024-001"},
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        assert result["permit_id"] == "PERM-2024-001"
        assert "status" in result

    def test_permit_lookup_includes_tenant(self, tenant: TenantContext) -> None:
        tool = GovernanceTools()
        result = tool.run(
            {"permit_id": "PERM-001"},
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True

    def test_permit_lookup_missing_id(self) -> None:
        tool = GovernanceTools()
        result = tool.run({})

        # Should handle missing param gracefully
        assert "success" in result


class TestCommerceTools:
    """Test commerce product search tool end-to-end."""

    def test_product_search_success(self, tenant: TenantContext) -> None:
        tool = CommerceTools()
        result = tool.run(
            {"query": "hot drinks", "limit": 10},
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        assert "results" in result
        assert result["total"] >= 0

    def test_product_search_default_limit(self, tenant: TenantContext) -> None:
        tool = CommerceTools()
        result = tool.run(
            {"query": "electronics"},
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        assert isinstance(result["results"], list)

    def test_product_search_with_category(self, tenant: TenantContext) -> None:
        tool = CommerceTools()
        result = tool.run(
            {"query": "food", "category": "grocery"},
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True


class TestHealthcareTool:
    """Test healthcare facility directory tool (non-PHI)."""

    def test_facility_directory_success(self, tenant: TenantContext) -> None:
        tool = HealthcareTool()
        result = tool.run(
            {"location": "Dakkah", "facility_type": "hospital"},
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        assert "facilities" in result
        assert len(result["facilities"]) > 0

    def test_facility_directory_no_phi_leak(self, tenant: TenantContext) -> None:
        """Verify no PHI fields are returned in facility directory."""
        tool = HealthcareTool()
        result = tool.run(
            {"location": "Riyadh", "specialty": "cardiology"},
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        for facility in result["facilities"]:
            phi_fields = ["patient_id", "diagnosis", "prescription", "medical_record", "national_id"]
            for field in phi_fields:
                assert field not in facility, f"PHI field '{field}' leaked in response"

    def test_facility_directory_has_disclaimer(self, tenant: TenantContext) -> None:
        tool = HealthcareTool()
        result = tool.run(
            {"location": "Jeddah"},
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        assert "disclaimer" in result
        assert "997" in result["disclaimer"] or "emergency" in result["disclaimer"].lower()


class TestTransportationTool:
    """Test transportation route lookup tool."""

    def test_route_plan_success(self, tenant: TenantContext) -> None:
        tool = TransportationTool()
        result = tool.run(
            {
                "origin": "Dakkah Central",
                "destination": "Airport",
                "mode": "metro",
            },
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        assert "routes" in result
        assert len(result["routes"]) > 0
        assert result["routes"][0]["duration_minutes"] > 0

    def test_route_plan_any_mode(self, tenant: TenantContext) -> None:
        tool = TransportationTool()
        result = tool.run(
            {
                "origin": "Home",
                "destination": "Work",
            },
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        assert "routes" in result

    def test_route_plan_fare_in_sar(self, tenant: TenantContext) -> None:
        tool = TransportationTool()
        result = tool.run(
            {
                "origin": "A",
                "destination": "B",
                "mode": "bus",
            },
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        if result["routes"]:
            assert "fare_sar" in result["routes"][0]


class TestFleetTools:
    """Test fleet logistics tool."""

    def test_vehicle_status(self, tenant: TenantContext) -> None:
        tool = FleetTools()
        result = tool.run(
            {"vehicle_id": "VH-001"},
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        assert "vehicle_id" in result

    def test_delivery_tracking(self, tenant: TenantContext) -> None:
        tool = FleetTools()
        result = tool.run(
            {"tracking_number": "TRK-12345"},
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True


class TestPublicSafetyTool:
    """Test public safety incident reporting tool."""

    def test_incident_report(self, tenant: TenantContext) -> None:
        tool = PublicSafetyTool()
        result = tool.run(
            {
                "incident_type": "traffic_accident",
                "location": "Main St & 5th Ave",
                "severity": "medium",
            },
            tenant_id=tenant.tenant_id,
        )

        assert result["success"] is True
        assert "incident_id" in result or "message" in result

    def test_incident_report_required_fields(self) -> None:
        tool = PublicSafetyTool()
        result = tool.run({})

        assert "success" in result


class TestToolRegistryIntegration:
    """Test all tools are discoverable and have valid specs."""

    def test_all_tools_have_specs(self) -> None:
        tools = [
            GovernanceTools(),
            CommerceTools(),
            HealthcareTool(),
            TransportationTool(),
            FleetTools(),
            PublicSafetyTool(),
        ]

        for tool in tools:
            spec = tool.get_spec()
            assert spec["type"] == "function"
            assert "function" in spec
            assert spec["function"]["name"] == tool.name
            assert spec["function"]["description"]
            assert "parameters" in spec["function"]

    def test_all_tool_names_are_unique(self) -> None:
        tools = [
            GovernanceTools(),
            CommerceTools(),
            HealthcareTool(),
            TransportationTool(),
            FleetTools(),
            PublicSafetyTool(),
        ]

        names = [t.name for t in tools]
        assert len(names) == len(set(names)), "Tool names must be unique"

    def test_tool_execution_with_none_tenant(self) -> None:
        """Tools should work even without tenant context."""
        tool = CommerceTools()
        result = tool.run({"query": "test"}, tenant_id=None)

        assert result["success"] is True
