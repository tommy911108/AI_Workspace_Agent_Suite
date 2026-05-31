"""Small helper functions shared by agent modules."""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from .config import exportable_env_names


# This block builds a short setup guide for missing local configuration.
def build_setup_guide() -> str:
    expected_lines = "\n".join(f"- {name}" for name in exportable_env_names())
    return (
        "Local setup is incomplete.\n"
        "Please make sure these environment variables exist in .env:\n"
        f"{expected_lines}\n\n"
        "For MCP verification later:\n"
        "1. Start workspace-mcp in the google_workspace_mcp repo.\n"
        "2. Run `workspace-cli list`.\n"
        "3. Run `workspace-cli call list_calendars`.\n"
    )


# This block extracts the last assistant-style message content.
def extract_last_message_text(messages: Sequence[Any]) -> str:
    for message in reversed(messages):
        content = getattr(message, "content", "")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            merged = "\n".join(part for part in text_parts if part)
            if merged.strip():
                return merged
    return ""


# This block helps keep tool-name filtering consistent.
def filter_tools_by_name(tools: Iterable[Any], allowed_names: set[str]) -> list[Any]:
    return [tool for tool in tools if getattr(tool, "name", None) in allowed_names]


# This block formats a simple title for CLI output.
def format_section_title(title: str) -> str:
    return f"\n=== {title.strip()} ==="
