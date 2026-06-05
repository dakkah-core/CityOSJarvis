"""Healthcare tool: facility directory (non-PHI only)."""

from __future__ import annotations

from typing import Any

from .base import CityOSTool


class HealthcareTool(CityOSTool):
    name = "healthcare_facility_directory"
    description = (
        "Find healthcare facilities (hospitals, clinics, pharmacies) by "
        "location or specialty. Does NOT provide patient data."
    )
    parameters = {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City or district name"},
            "specialty": {
                "type": "string",
                "description": "Medical specialty (e.g., cardiology, pediatrics)",
            },
            "facility_type": {
                "type": "string",
                "enum": ["hospital", "clinic", "pharmacy", "laboratory"],
                "description": "Type of facility",
            },
        },
        "required": ["location"],
    }

    def run(
        self, params: dict[str, Any], tenant_id: str | None = None
    ) -> dict[str, Any]:
        location = params.get("location", "")
        # TODO: Integrate with CityOS healthcare domain API
        return {
            "success": True,
            "location": location,
            "facilities": [
                {
                    "name": f"{location} General Hospital",
                    "type": "hospital",
                    "address": f"Main St, {location}",
                    "phone": "+966 11 000 0000",
                    "hours": "24/7",
                }
            ],
            "disclaimer": (
                "This is directory information only. For medical emergencies, call 997."
            ),
        }
