"""Shared MCP client configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from .config import Settings

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError:  # pragma: no cover - dependency is optional during bootstrap
    MultiServerMCPClient = None


DEFAULT_SERVER_NAME = "workspace"


@dataclass(slots=True)
class WorkspaceMCPOptions:
    """Configuration for the local workspace-mcp subprocess."""

    permissions: Sequence[str] = field(default_factory=tuple)
    tools: Sequence[str] = field(default_factory=tuple)
    command: str = "uvx"
    single_user: bool = True
    tool_tier: str = "core"
    transport: str = "stdio"
    server_name: str = DEFAULT_SERVER_NAME
    extra_env: dict[str, str] = field(default_factory=dict)


# This block builds the server process configuration for LangChain MCP.
def build_workspace_mcp_config(
    settings: Settings,
    *,
    options: WorkspaceMCPOptions | None = None,
) -> dict[str, dict[str, Any]]:
    options = options or WorkspaceMCPOptions()
    if options.permissions and options.tools:
        raise ValueError("Use either granular permissions or service tools, not both.")

    args = ["workspace-mcp"]
    if options.single_user:
        args.append("--single-user")
    if options.tool_tier:
        args.extend(["--tool-tier", options.tool_tier])
    if options.permissions:
        args.append("--permissions")
        args.extend(options.permissions)
    elif options.tools:
        args.append("--tools")
        args.extend(options.tools)

    env = {
        "GOOGLE_OAUTH_CLIENT_ID": settings.google_oauth_client_id,
        "GOOGLE_OAUTH_CLIENT_SECRET": settings.google_oauth_client_secret,
        "OAUTHLIB_INSECURE_TRANSPORT": settings.oauthlib_insecure_transport,
        "USER_GOOGLE_EMAIL": settings.user_google_email,
        "WORKSPACE_MCP_PORT": settings.workspace_mcp_port,
        "WORKSPACE_MCP_HTTP_PORT": settings.workspace_mcp_http_port,
    }
    env.update(options.extra_env)

    return {
        options.server_name: {
            "command": options.command,
            "args": args,
            "transport": options.transport,
            "env": env,
        }
    }


# This block creates the shared multi-server MCP client.
def create_mcp_client(
    settings: Settings,
    *,
    options: WorkspaceMCPOptions | None = None,
) -> Any:
    if MultiServerMCPClient is None:
        raise RuntimeError(
            "Missing dependency: langchain-mcp-adapters. "
            "Install project dependencies before creating the MCP client."
        )

    return MultiServerMCPClient(build_workspace_mcp_config(settings, options=options))
