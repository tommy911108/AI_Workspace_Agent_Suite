"""CLI entry point for the refund email agent."""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from ai_workspace_agent_suite.agents.refund_agent import (
    build_auto_refund_task,
    build_refund_agent,
    get_refund_mcp_options,
    load_refund_tools,
    run_auto_refund_processing_with_task,
    run_interactive_chat,
)
from ai_workspace_agent_suite.config import ConfigurationError, load_settings
from ai_workspace_agent_suite.llm import create_chat_model
from ai_workspace_agent_suite.mcp_client import create_mcp_client
from ai_workspace_agent_suite.utils import build_setup_guide, format_section_title


# This block parses the local CLI options for the refund agent.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the AI Workspace Agent Suite refund email agent."
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "chat"),
        default="auto",
        help="Choose autonomous processing or interactive chat mode.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Override the model temperature for experimentation.",
    )
    return parser.parse_args()


# This block prints a short local setup guide when configuration is incomplete.
def _print_setup_guide() -> None:
    print(format_section_title("Setup Guide"))
    print(build_setup_guide())
    print("Refund agent reminder:")
    print("- This agent uses workspace-mcp over stdio, not workspace-cli directly.")
    print("- OAuth and Gmail API access must already be configured.")


def _is_google_auth_action_required(exc: Exception) -> bool:
    """Detect the auth-needed error returned by workspace-mcp."""
    message = str(exc)
    return (
        "ACTION REQUIRED: Google Authentication Needed" in message
        or "GoogleAuthenticationError" in message
        or "oauth2callback" in message
    )


async def _run_agent_mode(agent: Any, mode: str, auto_task: str) -> None:
    """Run the selected refund agent mode."""
    if mode == "auto":
        print(format_section_title("Auto Refund Processing"))
        summary = await run_auto_refund_processing_with_task(agent, auto_task)
        print(summary)
    else:
        print(format_section_title("Refund Agent Chat"))
        print("Type `exit` or `quit` to leave the chat.")
        await run_interactive_chat(agent)


async def _build_runtime(args: argparse.Namespace) -> tuple[Any, Any, Any]:
    settings = load_settings()
    model = create_chat_model(settings, temperature=args.temperature)
    mcp_client = create_mcp_client(settings, options=get_refund_mcp_options())
    return settings, model, mcp_client


# This block wires together settings, MCP tools, and the refund graph.
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
        # This block keeps one MCP session open so the OAuth callback server survives the browser flow.
        server_name = get_refund_mcp_options().server_name
        async with mcp_client.session(server_name) as mcp_session:
            tools = await load_refund_tools(mcp_session)
            agent = build_refund_agent(model, tools, settings)
            auto_task = build_auto_refund_task(settings.refund_agent_sender_name)
            auth_retry_used = False

            while True:
                try:
                    await _run_agent_mode(agent, args.mode, auto_task)
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
        print(f"Runtime error: {exc}")
        print("Check workspace-mcp, OAuth, Gmail API access, and installed dependencies.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
