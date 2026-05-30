"""Expanded tests for tenant-aware agent runtime."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from openjarvis.cityos.tenant_runtime import TenantAwareAgentRunner
from openjarvis.cityos.tenant import TenantContext


class TestTenantAwareAgentRunner:
    @pytest.fixture
    def mock_agent(self):
        agent = MagicMock()
        result = MagicMock()
        result.content = "Test response"
        result.tool_results = []
        result.turns = 1
        agent.run.return_value = result
        return agent

    @pytest.fixture
    def tenant(self):
        return TenantContext(
            tenant_id="test-tenant",
            node_path="global.sa.dakkah",
            realm_roles=["ai_user"],
            user_sub="user-123",
        )

    def test_run_without_tenant(self, mock_agent):
        runner = TenantAwareAgentRunner(mock_agent, None)
        result = runner.run("Hello", "You are a helpful assistant.")
        assert result["content"] == "Test response"
        mock_agent.run.assert_called_once()

    def test_run_with_tenant(self, mock_agent, tenant):
        runner = TenantAwareAgentRunner(mock_agent, tenant)
        result = runner.run("Hello", "You are a helpful assistant.")
        assert result["content"] == "Test response"

    def test_apply_tenant_prefixes_memory(self, mock_agent, tenant):
        runner = TenantAwareAgentRunner(mock_agent, tenant)
        ctx = MagicMock()
        ctx.memory.index_name = "jarvis_memory"
        ctx.traces.table_name = "jarvis_traces"
        ctx.conversation.session_id = "default"

        runner._apply_tenant_prefixes(ctx)

        assert ctx.memory.index_name == "jarvis_memory_test-tenant"
        assert ctx.traces.table_name == "jarvis_traces_test-tenant"
        assert ctx.conversation.session_id == "default_test-tenant"

    def test_apply_tenant_prefixes_no_tenant(self, mock_agent):
        runner = TenantAwareAgentRunner(mock_agent, None)
        ctx = MagicMock()
        ctx.memory.index_name = "jarvis_memory"

        runner._apply_tenant_prefixes(ctx)
        assert ctx.memory.index_name == "jarvis_memory"

    def test_tool_results_audited(self, mock_agent, tenant):
        tr = MagicMock()
        tr.name = "governance.lookup_permit"
        tr.status = "success"
        tr.result = {"permit_id": "P-123"}
        mock_agent.run.return_value.tool_results = [tr]
        mock_agent.run.return_value.content = "Found permit"

        runner = TenantAwareAgentRunner(mock_agent, tenant)
        result = runner.run("Find permit", "System prompt")

        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["name"] == "governance.lookup_permit"

    def test_run_with_tool_results_empty(self, mock_agent, tenant):
        mock_agent.run.return_value.tool_results = None
        runner = TenantAwareAgentRunner(mock_agent, tenant)
        result = runner.run("Hello", "System prompt")
        assert result["tool_results"] == []

    def test_run_preserves_turns(self, mock_agent, tenant):
        mock_agent.run.return_value.turns = 3
        runner = TenantAwareAgentRunner(mock_agent, tenant)
        result = runner.run("Hello", "System prompt")
        assert result["turns"] == 3
