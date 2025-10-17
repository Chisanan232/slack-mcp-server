"""Slack MCP Server - A powerful MCP server for Slack integration.

This package provides a Model Context Protocol (MCP) server implementation
for Slack, enabling AI assistants and other tools to interact with Slack
workspaces through a standardized interface.

The package is PEP 561 compliant and includes type stubs for static type
checking with MyPy and other type checkers.

Main Components:
    - mcp: MCP server implementation with Slack tools
    - webhook: Webhook server for receiving Slack events
    - integrate: Integrated server combining MCP and webhook functionality
    - backends: Queue backend implementations (memory, Redis, Kafka)
    - events: Slack event type definitions
    - types: Type definitions and protocols for type checking

Type System:
    The package provides comprehensive type definitions for static type checking:

    - Slack Types: SlackEventPayload, SlackChannelID, SlackUserID, etc.
    - Queue Types: QueueBackendProtocol, QueueKey, QueuePayload, QueueMessage
    - Handler Types: EventHandlerProtocol, EventHandlerFunc

    All types follow PEP 695 (Python 3.12+) using modern type statement syntax.

Example:
    >>> from slack_mcp import types, SlackEvent, QueueBackendProtocol
    >>> from slack_mcp.events import SlackEvent
    >>>
    >>> # Use type annotations
    >>> def handle_message(event: types.SlackEventPayload) -> None:
    ...     print(f"Received event: {event['type']}")
    >>>
    >>> # Implement a queue backend plugin
    >>> class MyBackend:
    ...     async def publish(self, key: types.QueueKey, payload: types.QueuePayload) -> None:
    ...         pass
    >>>
    >>> backend: QueueBackendProtocol = MyBackend()
"""

from __future__ import annotations

# Re-export commonly used types and protocols for convenience
from slack_mcp import types
from slack_mcp.events import SlackEvent
from slack_mcp.types import QueueBackendProtocol

__all__ = [
    "types",
    "SlackEvent",
    "QueueBackendProtocol",
]

__version__ = "0.0.1"
