"""Expanded tests for MCP tool registry and execution."""

from __future__ import annotations

import pytest

from openjarvis.cityos.tools import (
    CommerceTools,
    FleetTools,
    GovernanceTools,
    HealthcareTool,
    PublicSafetyTool,
    TransportationTool,
)


class TestToolSpecs:
    """Test tool specification validation."""

    @pytest.mark.parametrize(
        "tool_class",
        [
            GovernanceTools,
            CommerceTools,
            HealthcareTool,
            TransportationTool,
            FleetTools,
            PublicSafetyTool,
        ],
    )
    def test_tool_has_name(self, tool_class) -> None:
        tool = tool_class()
        assert tool.name
        assert isinstance(tool.name, str)

    @pytest.mark.parametrize(
        "tool_class",
        [
            GovernanceTools,
            CommerceTools,
            HealthcareTool,
            TransportationTool,
            FleetTools,
            PublicSafetyTool,
        ],
    )
    def test_tool_has_description(self, tool_class) -> None:
        tool = tool_class()
        assert tool.description
        assert isinstance(tool.description, str)
        assert len(tool.description) > 10

    @pytest.mark.parametrize(
        "tool_class",
        [
            GovernanceTools,
            CommerceTools,
            HealthcareTool,
            TransportationTool,
            FleetTools,
            PublicSafetyTool,
        ],
    )
    def test_tool_has_parameters(self, tool_class) -> None:
        tool = tool_class()
        assert tool.parameters
        assert "type" in tool.parameters
        assert tool.parameters["type"] == "object"

    @pytest.mark.parametrize(
        "tool_class",
        [
            GovernanceTools,
            CommerceTools,
            HealthcareTool,
            TransportationTool,
            FleetTools,
            PublicSafetyTool,
        ],
    )
    def test_get_spec_format(self, tool_class) -> None:
        tool = tool_class()
        spec = tool.get_spec()
        assert spec["type"] == "function"
        assert "function" in spec
        assert spec["function"]["name"] == tool.name


class TestToolExecution:
    """Test tool execution with various inputs."""

    def test_governance_missing_param(self) -> None:
        tool = GovernanceTools()
        result = tool.run({})  # Missing permit_id
        assert "success" in result

    def test_commerce_pagination_params(self) -> None:
        tool = CommerceTools()
        result = tool.run({"query": "test", "limit": 50})
        assert result["success"]
        assert "results" in result

    def test_healthcare_facility_types(self) -> None:
        tool = HealthcareTool()
        for facility_type in ["hospital", "clinic", "pharmacy", "laboratory"]:
            result = tool.run({"location": "Dakkah", "facility_type": facility_type})
            assert result["success"], f"Failed for {facility_type}"

    def test_transportation_modes(self) -> None:
        tool = TransportationTool()
        for mode in ["bus", "metro", "taxi", "any"]:
            result = tool.run({"origin": "A", "destination": "B", "mode": mode})
            assert result["success"], f"Failed for {mode}"

    def test_fleet_vehicle_id(self) -> None:
        tool = FleetTools()
        result = tool.run({"vehicle_id": "VH-TEST-001"})
        assert result["success"]
        assert "vehicle_id" in result

    def test_public_safety_severity_levels(self) -> None:
        tool = PublicSafetyTool()
        for severity in ["low", "medium", "high", "critical"]:
            result = tool.run(
                {
                    "incident_type": "test",
                    "location": "Test St",
                    "severity": severity,
                }
            )
            assert result["success"], f"Failed for {severity}"

    def test_all_tools_with_tenant_id(self) -> None:
        tools = [
            GovernanceTools(),
            CommerceTools(),
            HealthcareTool(),
            TransportationTool(),
            FleetTools(),
            PublicSafetyTool(),
        ]
        for tool in tools:
            result = tool.run({}, tenant_id="test-tenant")
            assert "success" in result

    def test_all_tools_without_tenant_id(self) -> None:
        tools = [
            GovernanceTools(),
            CommerceTools(),
            HealthcareTool(),
            TransportationTool(),
            FleetTools(),
            PublicSafetyTool(),
        ]
        for tool in tools:
            result = tool.run({})
            assert "success" in result


class TestToolResultStructure:
    """Verify tool results have consistent structure."""

    @pytest.mark.parametrize(
        "tool_class",
        [
            GovernanceTools,
            CommerceTools,
            HealthcareTool,
            TransportationTool,
            FleetTools,
            PublicSafetyTool,
        ],
    )
    def test_result_has_success_key(self, tool_class) -> None:
        tool = tool_class()
        result = tool.run({})
        assert "success" in result
        assert isinstance(result["success"], bool)

    @pytest.mark.parametrize(
        "tool_class",
        [
            GovernanceTools,
            CommerceTools,
            HealthcareTool,
            TransportationTool,
            FleetTools,
            PublicSafetyTool,
        ],
    )
    def test_result_is_json_serializable(self, tool_class) -> None:
        import json

        tool = tool_class()
        result = tool.run({})
        # Should not raise
        json.dumps(result)
