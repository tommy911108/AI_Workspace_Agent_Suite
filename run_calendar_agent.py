"""CLI entry point for the calendar agent."""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from ai_workspace_agent_suite.agents.calendar_agent import (
    build_calendar_agent,
    get_calendar_mcp_options,
    load_calendar_tools,
    run_calendar_demo,
    run_calendar_interactive_chat,
)
from ai_workspace_agent_suite.config import ConfigurationError, load_settings
from ai_workspace_agent_suite.llm import create_chat_model
from ai_workspace_agent_suite.mcp_client import create_mcp_client
from ai_workspace_agent_suite.utils import build_setup_guide, format_section_title


# This block parses the local CLI options for the calendar agent.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the AI Workspace Agent Suite calendar agent."
    )
    parser.add_argument(
        "--mode",
        choices=("chat", "demo"),
        default="chat",
        help="Choose interactive chat or fixed demo mode.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Override the model temperature for experimentation.",
    )
    return parser.parse_args()


def _print_setup_guide() -> None:
    print(format_section_title("Setup Guide"))
    print(build_setup_guide())
    print("Calendar agent reminder:")
    print("- This agent uses workspace-mcp for MCP tools.")
    print("- Simple read queries also use workspace-cli through the local HTTP sidecar.")


def _is_google_auth_action_required(exc: Exception) -> bool:
    """Detect the auth-needed error returned by workspace-mcp/workspace-cli."""
    message = str(exc)
    return (
        "ACTION REQUIRED: Google Authentication Needed" in message
        or "GoogleAuthenticationError" in message
        or "oauth2callback" in message
    )


def _format_nested_exception(exc: BaseException) -> str:
    """Unwrap ExceptionGroup messages for clearer CLI output."""
    if hasattr(exc, "exceptions"):
        parts: list[str] = []
        for inner in getattr(exc, "exceptions", []):
            parts.append(_format_nested_exception(inner))
        cleaned = [part.strip() for part in parts if part.strip()]
        return "\n\n".join(cleaned) if cleaned else str(exc)
    return str(exc)


async def _build_runtime(args: argparse.Namespace) -> tuple[Any, Any, Any]:
    settings = load_settings()
    model = create_chat_model(settings, temperature=args.temperature)
    mcp_client = create_mcp_client(settings, options=get_calendar_mcp_options())
    return settings, model, mcp_client


async def _run_agent_mode(agent: Any, mode: str) -> None:
    if mode == "demo":
        print(format_section_title("Calendar Demo"))
        await run_calendar_demo(agent)
    else:
        print(format_section_title("Calendar Chat"))
        print("Type `demo` to run the fixed examples. Type `exit` or `quit` to leave.")
        await run_calendar_interactive_chat(agent)


async def main() -> int:
    args = parse_args()

    try:
        settings, model, mcp_client = await _build_runtime(args)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}")
        _print_setup_guide()
        return 1
    except RuntimeError as exc:
        print(f"Startup error: {exc}")
        return 1

    try:
        server_name = get_calendar_mcp_options().server_name
        async with mcp_client.session(server_name) as mcp_session:
            tools = await load_calendar_tools(mcp_session, settings)
            agent = build_calendar_agent(model, tools, settings)
            auth_retry_used = False

            while True:
                try:
                    await _run_agent_mode(agent, args.mode)
                    break
                except Exception as exc:  # pragma: no cover - depends on external services
                    if _is_google_auth_action_required(exc) and not auth_retry_used:
                        auth_retry_used = True
                        print(format_section_title("Google Auth Required"))
                        print(str(exc))
                        print(
                            "\nComplete the Google authorization in your browser, wait for the redirect page to finish, "
                            "then come back here."
                        )
                        input("Press Enter after the browser flow finishes to retry the original command...")
                        continue
                    raise
    except Exception as exc:  # pragma: no cover - depends on external services
        print(f"Runtime error: {_format_nested_exception(exc)}")
        print("Check workspace-mcp, workspace-cli, OAuth, Calendar API access, and installed dependencies.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
