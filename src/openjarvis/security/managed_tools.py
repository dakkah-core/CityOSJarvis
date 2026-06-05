"""Managed-agent tool policy helpers."""

from __future__ import annotations

from typing import Any, Iterable

DANGEROUS_MANAGED_TOOLS = frozenset(
    {
        "apply_patch",
        "code_interpreter",
        "code_interpreter_docker",
        "db_query",
        "docker_shell_exec",
        "file_write",
        "git_commit",
        "git_push",
        "shell_exec",
    }
)


def managed_agent_dangerous_tools_allowed(config: Any) -> bool:
    """Return whether managed agents may use dangerous local execution tools."""
    agent_manager = getattr(config, "agent_manager", None)
    return bool(getattr(agent_manager, "allow_dangerous_tools", False))


def normalize_tool_names(tools: Any) -> list[str]:
    """Normalize an agent config's tools field into names."""
    if isinstance(tools, str):
        return [name.strip() for name in tools.split(",") if name.strip()]
    if isinstance(tools, Iterable) and not isinstance(tools, (bytes, bytearray, dict)):
        names: list[str] = []
        for item in tools:
            if isinstance(item, str) and item.strip():
                names.append(item.strip())
            elif isinstance(item, dict):
                fn = item.get("function", {})
                name = fn.get("name") if isinstance(fn, dict) else None
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())
        return names
    return []


def blocked_managed_agent_tools(
    agent_config: dict[str, Any] | None,
    *,
    allow_dangerous_tools: bool,
) -> list[str]:
    """Return dangerous tool names requested by a managed-agent config."""
    if allow_dangerous_tools:
        return []
    tool_names = normalize_tool_names((agent_config or {}).get("tools"))
    return sorted(set(tool_names).intersection(DANGEROUS_MANAGED_TOOLS))


def sanitize_managed_agent_tools(
    agent_config: dict[str, Any],
    *,
    allow_dangerous_tools: bool,
) -> tuple[dict[str, Any], list[str]]:
    """Return a config copy with dangerous tools removed when not allowed."""
    blocked = blocked_managed_agent_tools(
        agent_config,
        allow_dangerous_tools=allow_dangerous_tools,
    )
    if not blocked:
        return dict(agent_config), []

    sanitized = dict(agent_config)
    blocked_set = set(blocked)
    tools = sanitized.get("tools")
    if isinstance(tools, str):
        allowed = [
            name for name in normalize_tool_names(tools) if name not in blocked_set
        ]
        sanitized["tools"] = ",".join(allowed)
    elif isinstance(tools, list):
        sanitized["tools"] = [
            item
            for item in tools
            if not (
                (isinstance(item, str) and item in blocked_set)
                or (
                    isinstance(item, dict)
                    and isinstance(item.get("function"), dict)
                    and item["function"].get("name") in blocked_set
                )
            )
        ]
    return sanitized, blocked
