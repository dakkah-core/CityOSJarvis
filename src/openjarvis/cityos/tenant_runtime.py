"""Tenant-aware runtime integration for OpenJarvis agents.

This module wraps agent execution with tenant isolation:
- Prefixes memory stores per tenant
- Prefixes trace stores per tenant
- Prefixes conversation history per tenant
- Logs tool execution with tenant context
"""

from __future__ import annotations

import logging
from typing import Any

from .audit import CityOSAuditLogger
from .tenant import TenantContext

logger = logging.getLogger(__name__)


class TenantAwareAgentRunner:
    """Wraps an OpenJarvis agent with tenant-scoped execution."""

    def __init__(self, agent: Any, tenant: TenantContext | None) -> None:
        self.agent = agent
        self.tenant = tenant
        self.audit = CityOSAuditLogger()

    def _apply_tenant_prefixes(self, context: Any) -> None:
        """Apply tenant prefixes to memory, trace, and conversation stores."""
        if self.tenant is None:
            return

        tenant_id = self.tenant.tenant_id

        # Prefix memory store
        if hasattr(context, "memory") and hasattr(context.memory, "index_name"):
            original = context.memory.index_name or "jarvis_memory"
            context.memory.index_name = f"{original}_{tenant_id}"
            logger.debug("Tenant memory index: %s", context.memory.index_name)

        # Prefix trace store
        if hasattr(context, "traces") and hasattr(context.traces, "table_name"):
            original = context.traces.table_name or "jarvis_traces"
            context.traces.table_name = f"{original}_{tenant_id}"
            logger.debug("Tenant trace table: %s", context.traces.table_name)

        # Prefix conversation store
        if hasattr(context, "conversation") and hasattr(
            context.conversation, "session_id"
        ):
            original = context.conversation.session_id or "default"
            context.conversation.session_id = f"{original}_{tenant_id}"
            logger.debug(
                "Tenant conversation session: %s", context.conversation.session_id
            )

    def run(self, query: str, system_prompt: str) -> dict[str, Any]:
        """Run the agent with tenant isolation and audit logging."""
        from openjarvis.agents._stubs import AgentContext
        from openjarvis.core.types import Message, Role

        ctx = AgentContext()
        messages = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=query),
        ]
        for m in messages:
            ctx.conversation.add(m)

        # Apply tenant-scoped prefixes
        self._apply_tenant_prefixes(ctx)

        # Execute agent
        result = self.agent.run(query, context=ctx)

        # Log tool execution
        if result.tool_results:
            for tr in result.tool_results:
                self.audit.log(
                    event="tool.executed",
                    tenant=self.tenant,
                    request={"tool_name": tr.name, "query": query},
                    response={"status": tr.status, "result": str(tr.result)[:200]},
                )

        return {
            "content": result.content,
            "tool_results": [
                {"name": tr.name, "status": tr.status, "result": tr.result}
                for tr in (result.tool_results or [])
            ],
            "turns": result.turns,
        }
