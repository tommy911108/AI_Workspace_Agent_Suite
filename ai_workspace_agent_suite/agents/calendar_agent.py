"""Calendar agent implementation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..config import Settings
from ..graph import build_react_agent
from ..llm import bind_tools
from ..mcp_client import WorkspaceMCPOptions
from ..prompts import CALENDAR_AGENT_PROMPT, build_system_prompt
from ..tools.calendar_cli import build_calendar_cli_tools
from ..utils import extract_last_message_text, filter_tools_by_name

try:
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
except ImportError:  # pragma: no cover - dependency is optional during bootstrap
    AIMessage = Any
    BaseMessage = Any
    HumanMessage = None

try:
    from langchain_mcp_adapters.tools import load_mcp_tools
except ImportError:  # pragma: no cover - dependency is optional during bootstrap
    load_mcp_tools = None


# This block tracks the calendar MCP tools required by the project.
CALENDAR_MCP_TOOL_CANDIDATES: tuple[str, ...] = (
    "list_calendars",
    "get_events",
    "manage_event",
    "query_freebusy",
)


# This block defines the calendar agent's tool-selection policy.
CALENDAR_WORKFLOW_PROMPT = """
Follow these rules when handling calendar tasks:
1. Use CLI tools for simple read-only tasks when possible:
   - listing calendars
   - checking today's events
   - checking events in a time range
   - retrieving one event by ID
2. Use MCP calendar tools for richer actions:
   - create event
   - update event
   - delete event
   - RSVP
   - free/busy lookup
3. Before updating or deleting an event, require explicit user confirmation in the conversation.
4. For create actions, confirm the important details in your final answer.
5. If event details are ambiguous, ask for clarification instead of guessing.
6. End with a concise, practical answer.
""".strip()


CALENDAR_DEMO_QUERIES: tuple[str, ...] = (
    "What calendars do I have?",
    "What's on my calendar today?",
    "Show me my events for the next 7 days.",
)


def get_calendar_mcp_options() -> WorkspaceMCPOptions:
    """Return the MCP configuration used by the calendar agent."""
    return WorkspaceMCPOptions(
        permissions=("calendar:full",),
        tool_tier="extended",
        single_user=True,
        transport="stdio",
    )


def _build_calendar_time_context(settings: Settings) -> str:
    """Build the local time context used for relative date resolution."""
    try:
        local_timezone = ZoneInfo(settings.local_timezone)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(
            f"Invalid LOCAL_TIMEZONE value: {settings.local_timezone}. "
            "Use a valid IANA timezone such as Asia/Taipei."
        ) from exc

    local_now = datetime.now(local_timezone)
    timezone_name = settings.local_timezone
    utc_offset = local_now.strftime("%z")
    formatted_offset = f"UTC{utc_offset[:3]}:{utc_offset[3:]}" if utc_offset else "UTC offset unknown"
    local_timestamp = local_now.strftime("%Y-%m-%d %H:%M:%S")
    local_date = local_now.strftime("%Y-%m-%d")
    tomorrow_date = local_now.date() + timedelta(days=1)
    return "\n".join(
        [
            "Use the local time context below when resolving relative date words.",
            f"Current local datetime: {local_timestamp}",
            f"Current local date: {local_date}",
            f"Current timezone: {timezone_name}",
            f"Current UTC offset: {formatted_offset}",
            f"Tomorrow's date: {tomorrow_date.isoformat()}",
            "Resolve words like today, tomorrow, next Monday, and this afternoon into exact dates before calling tools.",
            "In your final answer, mention the resolved absolute date when the user used a relative time expression.",
        ]
    )


def build_calendar_system_prompt(settings: Settings) -> str:
    """Combine the shared and calendar-specific prompts."""
    calendar_prompt = "\n\n".join(
        [CALENDAR_AGENT_PROMPT, CALENDAR_WORKFLOW_PROMPT, _build_calendar_time_context(settings)]
    )
    return build_system_prompt(calendar_prompt)


async def load_calendar_tools(mcp_session: Any, settings: Settings) -> list[Any]:
    """Load MCP calendar tools and append lightweight CLI tools."""
    if load_mcp_tools is None:
        raise RuntimeError(
            "Missing dependency: langchain-mcp-adapters. "
            "Install project dependencies before loading MCP tools."
        )

    mcp_tools = await load_mcp_tools(mcp_session)
    filtered_mcp_tools = filter_tools_by_name(
        mcp_tools,
        set(CALENDAR_MCP_TOOL_CANDIDATES),
    )
    if not filtered_mcp_tools:
        raise RuntimeError(
            "No calendar MCP tools were loaded from workspace-mcp. "
            "Check your workspace-mcp installation, OAuth setup, and Calendar permissions."
        )

    cli_tools = build_calendar_cli_tools(settings)
    return [*filtered_mcp_tools, *cli_tools]


def build_calendar_agent(model: Any, tools: Sequence[Any], settings: Settings) -> Any:
    """Build the calendar agent on top of the shared ReAct graph."""
    system_prompt = build_calendar_system_prompt(settings)
    tool_enabled_model = bind_tools(model, tools)
    return build_react_agent(tool_enabled_model, tools, system_prompt)


def _require_langchain_messages() -> None:
    if HumanMessage is None:
        raise RuntimeError(
            "Missing dependency: langchain-core. "
            "Install project dependencies before running the calendar agent."
        )


def _get_final_response(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    final_text = extract_last_message_text(messages)
    if final_text.strip():
        return final_text
    return "The calendar agent finished, but no final text response was returned."


async def run_calendar_demo(agent: Any) -> None:
    """Run the fixed calendar demo prompts."""
    _require_langchain_messages()
    for index, query in enumerate(CALENDAR_DEMO_QUERIES, start=1):
        print(f"\n[{index}] {query}")
        result = await agent.ainvoke({"messages": [HumanMessage(content=query)]})
        print(_get_final_response(result))


async def run_calendar_interactive_chat(agent: Any) -> None:
    """Run a simple multi-turn CLI chat loop for the calendar agent."""
    _require_langchain_messages()
    history: list[BaseMessage] = []

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Calendar agent chat ended.")
            break
        if user_input.lower() == "demo":
            await run_calendar_demo(agent)
            continue

        history.append(HumanMessage(content=user_input))
        result = await agent.ainvoke({"messages": history})
        agent_reply = _get_final_response(result)
        print(f"Agent: {agent_reply}")

        messages = result.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage):
            history.extend(messages[len(history):])
        else:
            history = list(messages)
