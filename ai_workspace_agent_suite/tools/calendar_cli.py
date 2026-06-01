"""Lightweight workspace-cli calendar tools."""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any

from ..config import Settings

try:
    from langchain_core.tools import tool
except ImportError:  # pragma: no cover - dependency is optional during bootstrap
    tool = None


CLI_TIMEOUT_SECONDS = 15
CLI_MAX_RETRIES = 3
CLI_RETRY_DELAY_SECONDS = 1.0


def _is_transient_cli_error(message: str) -> bool:
    """Detect short-lived workspace-cli / sidecar session failures."""
    normalized = message.lower()
    transient_markers = (
        "session terminated",
        "connection refused",
        "all connection attempts failed",
        "server disconnected",
        "temporarily unavailable",
    )
    return any(marker in normalized for marker in transient_markers)


# This block runs workspace-cli against the local HTTP sidecar.
def _run_workspace_cli(url: str, args: list[str]) -> str:
    command = ["workspace-cli", "--url", url, *args]
    last_error = "Unknown CLI error"

    for attempt in range(1, CLI_MAX_RETRIES + 1):
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=CLI_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "workspace-cli is not installed or not on PATH. "
                "Install workspace-mcp CLI before using calendar CLI tools."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            if attempt < CLI_MAX_RETRIES:
                time.sleep(CLI_RETRY_DELAY_SECONDS)
                continue
            raise RuntimeError("workspace-cli timed out after 15 seconds.") from exc

        if completed.returncode == 0:
            output = completed.stdout.strip()
            if not output:
                return "workspace-cli returned no output."

            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                return output
            return json.dumps(parsed, indent=2, ensure_ascii=False)

        last_error = completed.stderr.strip() or completed.stdout.strip() or "Unknown CLI error"
        if attempt < CLI_MAX_RETRIES and _is_transient_cli_error(last_error):
            time.sleep(CLI_RETRY_DELAY_SECONDS)
            continue
        break

    raise RuntimeError(f"workspace-cli failed: {last_error}")


def _require_tool_support() -> None:
    if tool is None:
        raise RuntimeError(
            "Missing dependency: langchain-core. "
            "Install project dependencies before building calendar CLI tools."
        )


# This block creates the CLI-backed LangChain tools.
def build_calendar_cli_tools(settings: Settings) -> list[Any]:
    _require_tool_support()
    cli_url = settings.workspace_cli_url

    @tool
    def cli_tool_list() -> str:
        """List all tools exposed by the local workspace-cli bridge."""
        return _run_workspace_cli(cli_url, ["list"])

    @tool
    def cli_list_calendars() -> str:
        """Fast read-only list of available Google calendars."""
        return _run_workspace_cli(cli_url, ["call", "list_calendars"])

    @tool
    def cli_today_events(calendar_id: str = "primary") -> str:
        """Fast read-only lookup of today's calendar events."""
        return _run_workspace_cli(
            cli_url,
            [
                "call",
                "get_events",
                f"calendar_id={calendar_id}",
            ],
        )

    @tool
    def cli_list_events(
        time_min: str,
        time_max: str,
        calendar_id: str = "primary",
        query: str | None = None,
        max_results: int = 25,
    ) -> str:
        """Fast read-only lookup of calendar events in a custom date range."""
        args = [
            "call",
            "get_events",
            f"calendar_id={calendar_id}",
            f"time_min={time_min}",
            f"time_max={time_max}",
            f"max_results={max_results}",
        ]
        if query:
            args.append(f"query={query}")
        return _run_workspace_cli(cli_url, args)

    @tool
    def cli_get_event(event_id: str, calendar_id: str = "primary", detailed: bool = True) -> str:
        """Fast read-only lookup of one calendar event by event ID."""
        return _run_workspace_cli(
            cli_url,
            [
                "call",
                "get_events",
                f"calendar_id={calendar_id}",
                f"event_id={event_id}",
                f"detailed={json.dumps(detailed)}",
            ],
        )

    return [
        cli_tool_list,
        cli_list_calendars,
        cli_today_events,
        cli_list_events,
        cli_get_event,
    ]
