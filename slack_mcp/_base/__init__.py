"""Base utilities for Slack MCP server factories.

This package exports foundational abstractions used by the Slack MCP server,
primarily the base server factory interface that other server factories inherit.
"""

from .app import BaseServerFactory

__all__ = ["BaseServerFactory"]
