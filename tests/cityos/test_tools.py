"""Tests for CityOS MCP tools."""

from __future__ import annotations

import pytest

from openjarvis.cityos.tools import (
    GovernanceTools,
    CommerceTools,
    HealthcareTool,
    TransportationTool,
    FleetTools,
    PublicSafetyTool,
)


class TestGovernanceTools:
    def test_permit_lookup_returns_status(self):
        tool = GovernanceTools()
        result = tool.run({"permit_id": "PERM-2024-001"})
        assert result["success"] is True
        assert result["permit_id"] == "PERM-2024-001"
        assert "status" in result

    def test_spec_has_required_fields(self):
        tool = GovernanceTools()
        spec = tool.get_spec()
        assert spec["function"]["name"] == "governance_permit_lookup"
        assert "permit_id" in spec["function"]["parameters"]["properties"]


class TestCommerceTools:
    def test_product_search_returns_results(self):
        tool = CommerceTools()
        result = tool.run({"query": "laptop"})
        assert result["success"] is True
        assert result["query"] == "laptop"
        assert len(result["results"]) > 0


class TestHealthcareTool:
    def test_facility_directory_returns_facilities(self):
        tool = HealthcareTool()
        result = tool.run({"location": "Riyadh", "facility_type": "hospital"})
        assert result["success"] is True
        assert len(result["facilities"]) > 0
        assert "disclaimer" in result

    def test_no_phi_in_response(self):
        tool = HealthcareTool()
        result = tool.run({"location": "Riyadh"})
        response_str = str(result)
        # Ensure no patient data patterns
        assert "patient" not in response_str.lower()
        assert "diagnosis" not in response_str.lower()


class TestTransportationTool:
    def test_route_lookup_returns_routes(self):
        tool = TransportationTool()
        result = tool.run({"origin": "King Fahd Road", "destination": "Airport"})
        assert result["success"] is True
        assert len(result["routes"]) > 0


class TestFleetTools:
    def test_vehicle_status_returns_location(self):
        tool = FleetTools()
        result = tool.run({"vehicle_id": "VH-001"})
        assert result["success"] is True
        assert "location" in result
        assert "status" in result


class TestPublicSafetyTool:
    def test_incident_report_returns_ticket(self):
        tool = PublicSafetyTool()
        result = tool.run({
            "incident_type": "traffic",
            "location": "Main St & 5th Ave",
            "description": "Broken traffic light",
        })
        assert result["success"] is True
        assert "ticket_id" in result
        assert result["status"] == "received"

    def test_missing_parameters_handled_gracefully(self):
        tool = PublicSafetyTool()
        # Our stub does not enforce required params at runtime;
        # parameter validation is handled by the OpenAI function calling layer.
        result = tool.run({"incident_type": "traffic"})
        assert result["success"] is True
