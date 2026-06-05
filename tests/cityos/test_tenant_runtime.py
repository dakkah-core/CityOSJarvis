"""Tests for tenant-aware agent runtime."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from openjarvis.cityos.tenant import TenantContext
from openjarvis.cityos.tenant_runtime import TenantAwareAgentRunner


@pytest.fixture
def tenant() -> TenantContext:
    return TenantContext(
        tenant_id="test-tenant",
        node_path="global.sa.dakkah",
        realm_roles=["ai_user"],
        user_sub="user-123",
    )


@pytest.fixture
def mock_agent() -> MagicMock:
    agent = MagicMock()
    mock_result = MagicMock()
    mock_result.content = "Test response"
    mock_result.tool_results = []
    mock_result.turns = 1
    agent.run.return_value = mock_result
    return agent


class TestTenantAwareAgentRunner:
    def test_run_without_tenant(self, mock_agent: MagicMock) -> None:
        runner = TenantAwareAgentRunner(mock_agent, tenant=None)
        result = runner.run("Hello", "You are a helper")

        assert result["content"] == "Test response"
        mock_agent.run.assert_called_once()

    def test_run_with_tenant(
        self, mock_agent: MagicMock, tenant: TenantContext
    ) -> None:
        runner = TenantAwareAgentRunner(mock_agent, tenant=tenant)
        result = runner.run("Hello", "You are a helper")

        assert result["content"] == "Test response"

    def test_tenant_prefixes_applied(
        self, mock_agent: MagicMock, tenant: TenantContext
    ) -> None:
        runner = TenantAwareAgentRunner(mock_agent, tenant=tenant)

        # Mock context with memory, traces, conversation
        mock_ctx = MagicMock()
        mock_ctx.memory = MagicMock()
        mock_ctx.memory.index_name = "jarvis_memory"
        mock_ctx.traces = MagicMock()
        mock_ctx.traces.table_name = "jarvis_traces"
        mock_ctx.conversation = MagicMock()
        mock_ctx.conversation.session_id = "default"

        runner._apply_tenant_prefixes(mock_ctx)

        assert mock_ctx.memory.index_name == "jarvis_memory_test-tenant"
        assert mock_ctx.traces.table_name == "jarvis_traces_test-tenant"
        assert mock_ctx.conversation.session_id == "default_test-tenant"

    def test_no_prefixes_when_no_tenant(self, mock_agent: MagicMock) -> None:
        runner = TenantAwareAgentRunner(mock_agent, tenant=None)

        mock_ctx = MagicMock()
        mock_ctx.memory = MagicMock()
        mock_ctx.memory.index_name = "jarvis_memory"

        runner._apply_tenant_prefixes(mock_ctx)

        # Should not modify when tenant is None
        assert mock_ctx.memory.index_name == "jarvis_memory"

    def test_tool_execution_logged(
        self, mock_agent: MagicMock, tenant: TenantContext
    ) -> None:
        # Setup agent with tool results
        mock_result = MagicMock()
        mock_result.content = "Done"
        mock_tool_result = MagicMock()
        mock_tool_result.name = "cityos_weather"
        mock_tool_result.status = "success"
        mock_tool_result.result = {"temperature": 35}
        mock_result.tool_results = [mock_tool_result]
        mock_result.turns = 1
        mock_agent.run.return_value = mock_result

        runner = TenantAwareAgentRunner(mock_agent, tenant=tenant)

        # The audit logger is instantiated in __init__, so we patch the instance method
        with patch.object(runner.audit, "log") as mock_log:
            runner.run("What's the weather?", "You are a helper")

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["event"] == "tool.executed"

    def test_result_format(self, mock_agent: MagicMock) -> None:
        runner = TenantAwareAgentRunner(mock_agent, tenant=None)
        result = runner.run("Hello", "You are a helper")

        assert "content" in result
        assert "tool_results" in result
        assert "turns" in result
        assert isinstance(result["tool_results"], list)

    def test_system_prompt_in_messages(self, mock_agent: MagicMock) -> None:
        runner = TenantAwareAgentRunner(mock_agent, tenant=None)
        runner.run("User query", "System prompt here")

        # Verify agent.run was called with context containing system prompt
        mock_agent.run.assert_called_once()
        call_kwargs = mock_agent.run.call_args[1]
        assert "context" in call_kwargs
