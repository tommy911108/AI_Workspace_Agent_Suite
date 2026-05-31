"""Configuration helpers for the AI Workspace Agent Suite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import os

from dotenv import load_dotenv


class ConfigurationError(RuntimeError):
    """Raised when required local configuration is missing."""


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


@dataclass(slots=True)
class Settings:
    """Small settings object shared by the project modules."""

    openai_key: str = ""
    openai_base: str = ""
    openai_model: str = "gpt-4o"
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    oauthlib_insecure_transport: str = ""
    user_google_email: str = ""
    refund_agent_sender_name: str = "yenyu"
    local_timezone: str = "Asia/Taipei"
    workspace_mcp_port: str = "8000"
    workspace_mcp_http_port: str = "8001"

    @property
    def openai_api_key(self) -> str:
        """Expose a provider-agnostic API key field."""
        return self.openai_key

    @property
    def openai_base_url(self) -> str | None:
        """Return the optional custom OpenAI-compatible base URL."""
        return self.openai_base or None

    @property
    def workspace_cli_url(self) -> str:
        """Return the local HTTP sidecar URL used by workspace-cli."""
        return f"http://127.0.0.1:{self.workspace_mcp_http_port}/mcp"

    def missing_env_vars(self) -> list[str]:
        """Return missing environment variables for the current setup."""
        required = {
            "OPENAI_KEY": self.openai_key,
            "OPENAI_BASE": self.openai_base,
            "OPENAI_MODEL": self.openai_model,
            "GOOGLE_OAUTH_CLIENT_ID": self.google_oauth_client_id,
            "GOOGLE_OAUTH_CLIENT_SECRET": self.google_oauth_client_secret,
            "OAUTHLIB_INSECURE_TRANSPORT": self.oauthlib_insecure_transport,
            "USER_GOOGLE_EMAIL": self.user_google_email,
            "REFUND_AGENT_SENDER_NAME": self.refund_agent_sender_name,
        }
        return [name for name, value in required.items() if not value]

    def ensure_valid(self) -> "Settings":
        """Fail fast when the local environment is incomplete."""
        missing = self.missing_env_vars()
        if missing:
            raise ConfigurationError(
                "Missing required environment variables: "
                + ", ".join(sorted(missing))
            )
        return self


def _first_env_value(*names: str) -> str:
    """Read the first non-empty environment variable from a list."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def load_settings(env_path: str | Path | None = None, *, validate: bool = True) -> Settings:
    """Load settings from .env and process environment variables."""
    resolved_env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    load_dotenv(resolved_env_path, override=False)

    settings = Settings(
        openai_key=_first_env_value("OPENAI_KEY", "OPENAI_API_KEY"),
        openai_base=_first_env_value("OPENAI_BASE", "OPENAI_BASE_URL"),
        openai_model=_first_env_value("OPENAI_MODEL") or "gpt-4o",
        google_oauth_client_id=_first_env_value("GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_client_secret=_first_env_value("GOOGLE_OAUTH_CLIENT_SECRET"),
        oauthlib_insecure_transport=_first_env_value("OAUTHLIB_INSECURE_TRANSPORT"),
        user_google_email=_first_env_value("USER_GOOGLE_EMAIL"),
        refund_agent_sender_name=_first_env_value("REFUND_AGENT_SENDER_NAME") or "yenyu",
        local_timezone=_first_env_value("LOCAL_TIMEZONE", "CALENDAR_LOCAL_TIMEZONE") or "Asia/Taipei",
        workspace_mcp_port=_first_env_value("WORKSPACE_MCP_PORT") or "8000",
        workspace_mcp_http_port=_first_env_value("WORKSPACE_MCP_HTTP_PORT") or "8001",
    )

    return settings.ensure_valid() if validate else settings


def exportable_env_names() -> tuple[str, ...]:
    """Expose the expected environment variable names in one place."""
    return (
        "OPENAI_KEY",
        "OPENAI_BASE",
        "OPENAI_MODEL",
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET",
        "OAUTHLIB_INSECURE_TRANSPORT",
        "USER_GOOGLE_EMAIL",
        "REFUND_AGENT_SENDER_NAME",
        "LOCAL_TIMEZONE",
        "WORKSPACE_MCP_PORT",
        "WORKSPACE_MCP_HTTP_PORT",
    )


def format_missing_env_vars(names: Iterable[str]) -> str:
    """Format a readable error message for missing variables."""
    missing = [name for name in names if name]
    if not missing:
        return "No missing environment variables."
    joined = "\n".join(f"- {name}" for name in missing)
    return f"Missing environment variables:\n{joined}"
