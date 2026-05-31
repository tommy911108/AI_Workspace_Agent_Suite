"""Shared LangGraph ReAct graph helpers."""

from __future__ import annotations

from typing import Any, Callable, Sequence

from .state import AgentState

try:
    from langchain_core.messages import SystemMessage
    from langgraph.graph import END, StateGraph
    from langgraph.prebuilt import ToolNode
except ImportError:  # pragma: no cover - dependency is optional during bootstrap
    END = "__end__"
    StateGraph = None
    SystemMessage = None
    ToolNode = None


# This block creates the async agent node used in the ReAct loop.
def make_agent_node(model: Any, system_prompt: str) -> Callable[[AgentState], Any]:
    if SystemMessage is None:
        raise RuntimeError(
            "Missing dependency: langgraph/langchain-core. "
            "Install project dependencies before building the graph."
        )

    async def agent_node(state: AgentState) -> dict[str, list[Any]]:
        history = list(state["messages"])
        response = await model.ainvoke([SystemMessage(content=system_prompt), *history])
        return {"messages": [response]}

    return agent_node


# This block decides whether the graph should continue calling tools.
def should_continue(state: AgentState) -> str:
    messages = list(state.get("messages", []))
    if not messages:
        return END

    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    return "tools" if tool_calls else END


# This block compiles the shared ReAct graph structure.
def build_react_agent(model: Any, tools: Sequence[Any], system_prompt: str) -> Any:
    if StateGraph is None or ToolNode is None:
        raise RuntimeError(
            "Missing dependency: langgraph. "
            "Install project dependencies before building the graph."
        )

    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("agent", make_agent_node(model, system_prompt))
    graph_builder.add_node("tools", ToolNode(list(tools)))
    graph_builder.set_entry_point("agent")
    graph_builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph_builder.add_edge("tools", "agent")
    return graph_builder.compile()
