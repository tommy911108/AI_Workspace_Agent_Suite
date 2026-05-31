"""Shared package for the AI Workspace Agent Suite."""

from .config import ConfigurationError, Settings, load_settings

__all__ = [
    "ConfigurationError",
    "Settings",
    "load_settings",
]
