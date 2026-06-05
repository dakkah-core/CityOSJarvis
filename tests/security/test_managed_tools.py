from types import SimpleNamespace

from openjarvis.security.managed_tools import (
    blocked_managed_agent_tools,
    managed_agent_dangerous_tools_allowed,
    sanitize_managed_agent_tools,
)


def test_blocks_dangerous_managed_tools_by_default():
    blocked = blocked_managed_agent_tools(
        {"tools": ["calculator", "shell_exec", "code_interpreter"]},
        allow_dangerous_tools=False,
    )
    assert blocked == ["code_interpreter", "shell_exec"]


def test_allows_dangerous_tools_only_when_configured():
    config = SimpleNamespace(agent_manager=SimpleNamespace(allow_dangerous_tools=True))
    assert managed_agent_dangerous_tools_allowed(config) is True
    blocked = blocked_managed_agent_tools(
        {"tools": "shell_exec,calculator"},
        allow_dangerous_tools=managed_agent_dangerous_tools_allowed(config),
    )
    assert blocked == []


def test_sanitizes_existing_agent_config_for_background_ticks():
    sanitized, blocked = sanitize_managed_agent_tools(
        {"tools": ["shell_exec", "calculator", "file_write"]},
        allow_dangerous_tools=False,
    )
    assert blocked == ["file_write", "shell_exec"]
    assert sanitized["tools"] == ["calculator"]
