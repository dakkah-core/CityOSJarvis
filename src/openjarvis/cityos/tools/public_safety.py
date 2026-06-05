"""Public safety tool: incident reporting."""

from __future__ import annotations

from typing import Any

from .base import CityOSTool


class PublicSafetyTool(CityOSTool):
    name = "public_safety_report_incident"
    description = (
        "Submit a non-emergency incident report (traffic, sanitation, "
        "infrastructure). For emergencies, call 911."
    )
    parameters = {
        "type": "object",
        "properties": {
            "incident_type": {
                "type": "string",
                "enum": [
                    "traffic",
                    "sanitation",
                    "infrastructure",
                    "lighting",
                    "other",
                ],
            },
            "location": {"type": "string", "description": "Street address or landmark"},
            "description": {"type": "string", "description": "Detailed description"},
        },
        "required": ["incident_type", "location", "description"],
    }

    def run(
        self, params: dict[str, Any], tenant_id: str | None = None
    ) -> dict[str, Any]:
        # TODO: Integrate with CityOS public safety API
        return {
            "success": True,
            "ticket_id": f"INC-{hash(params.get('description', '')) % 100000:05d}",
            "status": "received",
            "message": (
                "Your report has been received and will be reviewed within 24 hours."
            ),
        }
