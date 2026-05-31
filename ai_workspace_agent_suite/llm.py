"""LLM initialization helpers for the agent suite."""

from __future__ import annotations

from typing import Any, Sequence

from .config import Settings

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover - dependency is optional during bootstrap
    ChatOpenAI = None


# This block creates the shared chat model configuration.
def create_chat_model(settings: Settings, *, temperature: float = 0.0) -> Any:
    if ChatOpenAI is None:
        raise RuntimeError(
            "Missing dependency: langchain-openai. "
            "Install project dependencies before running the agents."
        )

    model_kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key,
        "temperature": temperature,
    }

    if settings.openai_base_url:
        model_kwargs["base_url"] = settings.openai_base_url

    return ChatOpenAI(**model_kwargs)


# This block centralizes tool binding behavior.
def bind_tools(model: Any, tools: Sequence[Any]) -> Any:
    return model.bind_tools(list(tools))
