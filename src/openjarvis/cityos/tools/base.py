"""Base class for CityOS MCP tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CityOSTool(ABC):
    """Base class for all CityOS domain tools.

    Subclasses must define:
    - name: str -- unique tool identifier
    - description: str -- human-readable description for the LLM
    - parameters: dict -- JSON schema for tool parameters
    """

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}

    @abstractmethod
    def run(
        self, params: dict[str, Any], tenant_id: str | None = None
    ) -> dict[str, Any]:
        """Execute the tool and return a result dict.

        Args:
            params: Validated parameters from the LLM
            tenant_id: Current tenant scope

        Returns:
            Result dict with at least a "success" key.
        """
        ...

    def get_spec(self) -> dict[str, Any]:
        """Return OpenAI function-calling spec for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
