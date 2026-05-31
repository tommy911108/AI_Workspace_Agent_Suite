"""Agent modules for the AI Workspace Agent Suite."""

from .refund_agent import (
    REFUND_TOOL_CANDIDATES,
    build_auto_refund_task,
    build_refund_agent,
    get_refund_mcp_options,
    load_refund_tools,
    run_auto_refund_processing_with_task,
    run_interactive_chat,
)
from .calendar_agent import (
    CALENDAR_MCP_TOOL_CANDIDATES,
    build_calendar_agent,
    get_calendar_mcp_options,
    load_calendar_tools,
    run_calendar_demo,
    run_calendar_interactive_chat,
)

__all__ = [
    "CALENDAR_MCP_TOOL_CANDIDATES",
    "REFUND_TOOL_CANDIDATES",
    "build_auto_refund_task",
    "build_calendar_agent",
    "build_refund_agent",
    "get_calendar_mcp_options",
    "get_refund_mcp_options",
    "load_calendar_tools",
    "load_refund_tools",
    "run_calendar_demo",
    "run_calendar_interactive_chat",
    "run_auto_refund_processing_with_task",
    "run_interactive_chat",
]
