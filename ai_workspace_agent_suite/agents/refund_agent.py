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
    from langchain_core.tools import tool
except ImportError:  # pragma: no cover - dependency is optional during bootstrap
    AIMessage = Any
    BaseMessage = Any
    HumanMessage = None
    tool = None

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
1. Start with a broad search of recent unread inbox emails instead of relying only on refund-related keywords.
2. Read each candidate email carefully before taking action.
3. Classify each message as REFUND_REQUEST, RETURN_REQUEST, COMPLAINT, or OTHER.
4. Do not miss complaint emails just because the subject does not contain words like refund, return, or complaint.
5. Treat pre-sales questions, marketing messages, and general informational emails as OTHER.
6. Use these simple response policies:
   - REFUND_REQUEST: approve politely and mention a 3-5 business day processing window.
   - RETURN_REQUEST: provide return instructions and mention a prepaid label will follow if appropriate.
   - COMPLAINT: acknowledge the concern empathetically and promise a follow-up within 24 hours.
   - OTHER: do not send a reply and do not create a draft.
7. In auto-processing behavior, send the reply directly when the case is clear enough.
8. When replying to an existing email, prefer a true threaded reply using the original sender email, thread_id, and reply headers when available.
9. Always make sure the send tool includes a valid `to` email address copied from the original message sender.
10. If threaded reply metadata fails, retry in the safest way that still preserves email threading headers when possible.
11. Only create a draft when the email is actionable but the correct response is still uncertain.
12. If you classify an email as OTHER, always skip it.
13. Always sign replies with the sender name "{sender_name}" and never use placeholders like [Your Name].
14. When using send or draft tools, pass from_name="{sender_name}" whenever appropriate.
15. Only count a reply as sent if the send tool actually succeeds. If a tool call fails, report it as a failed send instead of claiming success.
16. End with a concise summary that lists what you processed and what actions were taken.
""".strip()


# This block provides the fixed auto mode instruction from the project requirements.
AUTO_REFUND_TASK_TEMPLATE = """
Process recent unread customer-support test emails autonomously.
Start with a broad unread inbox search so you can catch refund requests, return requests, complaint emails,
and OTHER test emails even when their subjects do not contain obvious keywords.
For each candidate email, read the content, classify it as REFUND_REQUEST, RETURN_REQUEST, COMPLAINT, or OTHER,
and take the appropriate action.
If the case is clear, send the reply directly.
Only create a draft if an actionable email is genuinely ambiguous.
If an email is classified as OTHER, skip it completely and do not create a draft.
For the standard 8-email evaluation batch, treat the cases as simple enough to classify directly and avoid creating drafts.
For the standard 8-email evaluation batch, reply inside the existing email conversation whenever thread metadata is available.
Always include a real recipient email in the `to` field when calling the send or draft tool.
Sign any response as "{sender_name}" and never use placeholders like [Your Name].
For evaluation mode, aim to process the full unread test batch and make sure complaint emails and OTHER emails are counted correctly.
At the end, report a short summary of how many emails you processed in each category and what replies were sent, drafted, skipped, or failed.
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


def _find_tool_by_name(tools: Sequence[Any], tool_name: str) -> Any | None:
    """Return the first tool with the requested name."""
    for tool_obj in tools:
        if getattr(tool_obj, "name", None) == tool_name:
            return tool_obj
    return None


def _is_gmail_not_found_error(exc: Exception) -> bool:
    """Detect Gmail reply-thread errors that can be retried as normal sends."""
    message = str(exc)
    return "Requested entity was not found" in message or "reason': 'notFound'" in message


def _build_safe_send_tool(send_tool: Any) -> Any:
    """Wrap send_gmail_message with a fallback that preserves reply headers."""
    if tool is None:
        return send_tool

    @tool("send_gmail_message")
    async def safe_send_gmail_message(
        to: str,
        subject: str,
        body: str,
        body_format: str = "plain",
        cc: str | None = None,
        bcc: str | None = None,
        from_name: str | None = None,
        from_email: str | None = None,
        thread_id: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
        include_signature: bool = True,
    ) -> str:
        """Send a Gmail message, retrying without reply-thread metadata if needed."""
        payload = {
            "to": to,
            "subject": subject,
            "body": body,
            "body_format": body_format,
            "cc": cc,
            "bcc": bcc,
            "from_name": from_name,
            "from_email": from_email,
            "thread_id": thread_id if thread_id and thread_id != "unknown" else None,
            "in_reply_to": in_reply_to,
            "references": references,
            "include_signature": include_signature,
        }

        try:
            return await send_tool.ainvoke(payload)
        except Exception as exc:
            has_threading = any(payload.get(key) for key in ("thread_id", "in_reply_to", "references"))
            if not has_threading or not _is_gmail_not_found_error(exc):
                raise

            # Gmail 404 usually means the provided thread_id is stale or wrong.
            # Retrying without thread_id but keeping RFC reply headers often preserves threading.
            fallback_payload = dict(payload)
            fallback_payload["thread_id"] = None

            try:
                return await send_tool.ainvoke(fallback_payload)
            except Exception as retry_exc:
                if not _is_gmail_not_found_error(retry_exc):
                    raise
                raise retry_exc

    return safe_send_gmail_message


def _build_safe_draft_tool(tool_name: str, draft_tool: Any) -> Any:
    """Wrap draft_gmail_message-like tools with a fallback that preserves reply headers."""
    if tool is None:
        return draft_tool

    @tool(tool_name)
    async def safe_draft_gmail_message(
        subject: str,
        body: str,
        to: str | None = None,
        body_format: str = "plain",
        cc: str | None = None,
        bcc: str | None = None,
        from_name: str | None = None,
        from_email: str | None = None,
        thread_id: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
        attachments: Any | None = None,
        include_signature: bool = True,
        quote_original: bool = False,
    ) -> str:
        """Create a Gmail draft, retrying without reply-thread metadata if needed."""
        payload = {
            "subject": subject,
            "body": body,
            "to": to,
            "body_format": body_format,
            "cc": cc,
            "bcc": bcc,
            "from_name": from_name,
            "from_email": from_email,
            "thread_id": thread_id if thread_id and thread_id != "unknown" else None,
            "in_reply_to": in_reply_to,
            "references": references,
            "attachments": attachments,
            "include_signature": include_signature,
            "quote_original": quote_original,
        }

        try:
            return await draft_tool.ainvoke(payload)
        except Exception as exc:
            has_threading = any(payload.get(key) for key in ("thread_id", "in_reply_to", "references"))
            if not has_threading or not _is_gmail_not_found_error(exc):
                raise

            fallback_payload = dict(payload)
            fallback_payload["thread_id"] = None
            fallback_payload["quote_original"] = False
            try:
                return await draft_tool.ainvoke(fallback_payload)
            except Exception as retry_exc:
                if not _is_gmail_not_found_error(retry_exc):
                    raise
                raise retry_exc

    return safe_draft_gmail_message


def _patch_refund_tools(tools: Sequence[Any]) -> list[Any]:
    """Replace fragile Gmail tools with safer local wrappers when needed."""
    send_tool = _find_tool_by_name(tools, "send_gmail_message")
    draft_tool = _find_tool_by_name(tools, "draft_gmail_message")
    create_draft_tool = _find_tool_by_name(tools, "create_gmail_draft")

    patched_tools: list[Any] = []
    for tool_obj in tools:
        tool_name = getattr(tool_obj, "name", None)
        if tool_name == "send_gmail_message" and send_tool is not None:
            patched_tools.append(_build_safe_send_tool(send_tool))
        elif tool_name == "draft_gmail_message" and draft_tool is not None:
            patched_tools.append(_build_safe_draft_tool("draft_gmail_message", draft_tool))
        elif tool_name == "create_gmail_draft" and create_draft_tool is not None:
            patched_tools.append(_build_safe_draft_tool("create_gmail_draft", create_draft_tool))
        else:
            patched_tools.append(tool_obj)
    return patched_tools


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
    return _patch_refund_tools(filtered_tools)


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
