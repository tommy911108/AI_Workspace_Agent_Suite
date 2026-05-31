"""Refund email agent implementation."""

from __future__ import annotations

from typing import Any, Sequence

from ..config import Settings
from ..graph import build_react_agent
from ..llm import bind_tools
from ..mcp_client import WorkspaceMCPOptions
from ..prompts import REFUND_AGENT_PROMPT, build_system_prompt
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


# This block keeps the refund tool selection compatible with multiple MCP variants.
REFUND_TOOL_CANDIDATES: tuple[str, ...] = (
    "search_gmail_messages",
    "get_gmail_message_content",
    "get_gmail_messages_content_batch",
    "send_gmail_message",
    "draft_gmail_message",
    "create_gmail_draft",
    "get_gmail_thread_content",
    "get_gmail_thread",
    "list_gmail_labels",
)


# This block gives the refund agent a stricter workflow and reply policy.
REFUND_WORKFLOW_PROMPT_TEMPLATE = """
Follow this workflow when processing refund-related inbox tasks:
1. Search the inbox for unread refund, return, and complaint emails.
2. Read each relevant email carefully before taking action.
3. Classify each message as REFUND_REQUEST, RETURN_REQUEST, COMPLAINT, or OTHER.
4. Use these simple response policies:
   - REFUND_REQUEST: approve politely and mention a 3-5 business day processing window.
   - RETURN_REQUEST: provide return instructions and mention a prepaid label will follow if appropriate.
   - COMPLAINT: acknowledge the concern empathetically and promise a follow-up within 24 hours.
   - OTHER: do not send a reply.
5. In auto-processing behavior, send the reply directly when the case is clear enough.
6. Only create a draft when you are uncertain about the correct response or the request is ambiguous.
7. When replying in an existing conversation, preserve threading with thread_id.
8. Always sign replies with the sender name "{sender_name}" and never use placeholders like [Your Name].
9. When using send or draft tools, pass from_name="{sender_name}" whenever appropriate.
10. End with a concise summary that lists what you processed and what actions were taken.
""".strip()


# This block provides the fixed auto mode instruction from the project requirements.
AUTO_REFUND_TASK_TEMPLATE = """
Process refund and return emails autonomously.
Use Gmail tools to search for unread emails related to refunds, returns, complaints, and unhappy customers.
For each relevant email, read the content, classify it as REFUND_REQUEST, RETURN_REQUEST, COMPLAINT, or OTHER,
and take the appropriate action. Reply within the existing thread when you decide to respond.
If the case is clear, send the reply directly.
Only create a draft if you are genuinely uncertain about the correct response.
Sign any response as "{sender_name}" and never use placeholders like [Your Name].
Skip unrelated emails.
At the end, report a short summary of how many emails you processed in each category and what replies were sent or drafted.
""".strip()


def get_refund_mcp_options() -> WorkspaceMCPOptions:
    """Return the MCP configuration used by the refund agent."""
    return WorkspaceMCPOptions(
        permissions=("gmail:send",),
        tool_tier="extended",
        single_user=True,
        transport="stdio",
    )


def build_refund_system_prompt(sender_name: str) -> str:
    """Combine the shared and refund-specific prompts."""
    workflow_prompt = REFUND_WORKFLOW_PROMPT_TEMPLATE.format(sender_name=sender_name)
    refund_prompt = "\n\n".join([REFUND_AGENT_PROMPT, workflow_prompt])
    return build_system_prompt(refund_prompt)


async def load_refund_tools(mcp_session: Any) -> list[Any]:
    """Load and filter the Gmail tools needed by the refund workflow."""
    if load_mcp_tools is None:
        raise RuntimeError(
            "Missing dependency: langchain-mcp-adapters. "
            "Install project dependencies before loading MCP tools."
        )

    tools = await load_mcp_tools(mcp_session)
    allowed_names = set(REFUND_TOOL_CANDIDATES)
    filtered_tools = filter_tools_by_name(tools, allowed_names)
    if not filtered_tools:
        raise RuntimeError(
            "No Gmail refund tools were loaded from workspace-mcp. "
            "Check your workspace-mcp installation, OAuth setup, and Gmail permissions."
        )
    return filtered_tools


def build_refund_agent(model: Any, tools: Sequence[Any], settings: Settings) -> Any:
    """Build the refund agent on top of the shared ReAct graph."""
    system_prompt = build_refund_system_prompt(settings.refund_agent_sender_name)
    tool_enabled_model = bind_tools(model, tools)
    return build_react_agent(tool_enabled_model, tools, system_prompt)


def _require_langchain_messages() -> None:
    """Fail with a clear error if langchain-core is not installed."""
    if HumanMessage is None:
        raise RuntimeError(
            "Missing dependency: langchain-core. "
            "Install project dependencies before running the refund agent."
        )


def _get_final_response(result: dict[str, Any]) -> str:
    """Extract the final readable text from a graph result."""
    messages = result.get("messages", [])
    final_text = extract_last_message_text(messages)
    if final_text.strip():
        return final_text
    return "The refund agent finished, but no final text response was returned."


async def run_auto_refund_processing(agent: Any) -> str:
    """Run the fixed autonomous refund-processing workflow."""
    _require_langchain_messages()
    default_task = build_auto_refund_task("yenyu")
    result = await agent.ainvoke({"messages": [HumanMessage(content=default_task)]})
    return _get_final_response(result)


async def run_auto_refund_processing_with_task(agent: Any, auto_task: str) -> str:
    """Run the fixed autonomous refund-processing workflow."""
    _require_langchain_messages()
    result = await agent.ainvoke({"messages": [HumanMessage(content=auto_task)]})
    return _get_final_response(result)


def build_auto_refund_task(sender_name: str) -> str:
    """Build the formatted auto mode task."""
    return AUTO_REFUND_TASK_TEMPLATE.format(sender_name=sender_name)


async def run_interactive_chat(agent: Any) -> None:
    """Run a simple multi-turn CLI chat loop for the refund agent."""
    _require_langchain_messages()
    history: list[BaseMessage] = []

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Refund agent chat ended.")
            break

        history.append(HumanMessage(content=user_input))
        result = await agent.ainvoke({"messages": history})
        agent_reply = _get_final_response(result)
        print(f"Agent: {agent_reply}")

        messages = result.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage):
            history.extend(messages[len(history):])
        else:
            history = list(messages)
