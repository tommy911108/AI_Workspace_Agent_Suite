"""Shared state definitions for LangGraph agents."""

from __future__ import annotations

from typing import Annotated, Any, Sequence, TypedDict

try:
    from langchain_core.messages import BaseMessage
    from langgraph.graph.message import add_messages
except ImportError:  # pragma: no cover - dependency is optional during bootstrap
    BaseMessage = Any
    add_messages = object()


class AgentState(TypedDict):
    """Shared message history used across the ReAct loop."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
