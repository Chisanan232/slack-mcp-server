"""
Type definitions for the Slack MCP server package.

This module provides centralized type aliases and type definitions following
PEP 561, PEP 484, PEP 585, and PEP 695 standards for static type checking with MyPy.

Type aliases use the modern `type` statement (PEP 695) introduced in Python 3.12,
which provides better type inference and cleaner syntax compared to TypeAlias.

Type Hierarchy:
    - JSON types: Basic JSON-compatible types
    - Slack types: Slack-specific type definitions
    - Event types: Event handling type definitions
    - Handler types: Handler function signatures
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Protocol,
    Union,
    runtime_checkable,
)

if TYPE_CHECKING:
    from slack_sdk import WebClient
    from slack_sdk.web import SlackResponse

__all__ = [
    # JSON types
    "JSONValue",
    "JSONDict",
    "JSONList",
    "JSONPrimitive",
    # Slack types
    "SlackChannelID",
    "SlackUserID",
    "SlackTimestamp",
    "SlackToken",
    "SlackEventType",
    "SlackEventPayload",
    "SlackMessagePayload",
    "SlackClient",
    "SlackAPIResponse",
    # Transport types
    "TransportType",
    "MCPTransport",
    # Handler types
    "EventHandlerFunc",
    "AsyncEventHandlerFunc",
    "SyncEventHandlerFunc",
    # Protocol types
    "EventHandlerProtocol",
]

# ============================================================================
# JSON Type Definitions (PEP 484/585/695)
# ============================================================================

type JSONPrimitive = Union[str, int, float, bool, None]
"""Primitive JSON-compatible types."""

type JSONValue = Union[JSONPrimitive, JSONDict, JSONList]
"""Any valid JSON value type."""

type JSONDict = Dict[str, JSONValue]
"""JSON object represented as a dictionary."""

type JSONList = List[JSONValue]
"""JSON array represented as a list."""

# ============================================================================
# Slack Type Definitions
# ============================================================================

type SlackChannelID = str
"""Slack channel ID (e.g., 'C1234567890' or '#general')."""

type SlackUserID = str
"""Slack user ID (e.g., 'U1234567890')."""

type SlackTimestamp = str
"""Slack message timestamp (e.g., '1234567890.123456')."""

type SlackToken = str
"""Slack API token (e.g., 'xoxb-...' for bot tokens, 'xoxp-...' for user tokens)."""

type SlackEventType = str
"""Slack event type string (e.g., 'message', 'reaction_added')."""

type SlackEventPayload = Dict[str, Any]
"""Slack event payload as received from the Events API."""

type SlackMessagePayload = Dict[str, Any]
"""Slack message payload structure."""

if TYPE_CHECKING:
    type SlackClient = WebClient
    """Type alias for Slack SDK WebClient."""

    type SlackAPIResponse = SlackResponse
    """Type alias for Slack SDK API response."""
else:
    type SlackClient = Any
    type SlackAPIResponse = Any

# ============================================================================
# Transport Type Definitions
# ============================================================================

type TransportType = Literal["stdio", "sse", "streamable-http"]
"""MCP transport types supported by the server."""

type MCPTransport = Literal["stdio", "sse", "streamable-http"]
"""Alias for TransportType for backward compatibility."""

# ============================================================================
# Event Handler Type Definitions
# ============================================================================

type SyncEventHandlerFunc = Callable[[SlackEventPayload], None]
"""Synchronous event handler function signature."""

type AsyncEventHandlerFunc = Callable[[SlackEventPayload], Awaitable[None]]
"""Asynchronous event handler function signature."""

type EventHandlerFunc = Union[SyncEventHandlerFunc, AsyncEventHandlerFunc]
"""Event handler function that can be sync or async."""

# ============================================================================
# Protocol Definitions (PEP 544)
# ============================================================================


@runtime_checkable
class EventHandlerProtocol(Protocol):
    """Protocol for objects that can handle Slack events.

    This protocol defines the interface that all event handlers must implement.
    It follows PEP 544 for structural subtyping.

    Example:
        >>> class MyHandler:
        ...     async def handle_event(self, event: Dict[str, Any]) -> None:
        ...         print(f"Handling event: {event['type']}")
        >>>
        >>> handler: EventHandlerProtocol = MyHandler()
    """

    async def handle_event(self, event: SlackEventPayload) -> None:
        """Handle a Slack event.

        Args:
            event: The Slack event payload
        """
        ...


# ============================================================================
# Type Guards and Validators
# ============================================================================


def is_slack_channel_id(value: str) -> bool:
    """Type guard to check if a string is a valid Slack channel ID.

    Args:
        value: The string to check

    Returns:
        True if the value is a valid Slack channel ID format

    Example:
        >>> is_slack_channel_id("C1234567890")
        True
        >>> is_slack_channel_id("#general")
        True
        >>> is_slack_channel_id("invalid")
        False
    """
    return value.startswith(("C", "G", "D", "#"))


def is_slack_user_id(value: str) -> bool:
    """Type guard to check if a string is a valid Slack user ID.

    Args:
        value: The string to check

    Returns:
        True if the value is a valid Slack user ID format

    Example:
        >>> is_slack_user_id("U1234567890")
        True
        >>> is_slack_user_id("W1234567890")
        True
        >>> is_slack_user_id("invalid")
        False
    """
    return value.startswith(("U", "W", "B"))


def is_slack_timestamp(value: str) -> bool:
    """Type guard to check if a string is a valid Slack timestamp.

    Args:
        value: The string to check

    Returns:
        True if the value is a valid Slack timestamp format

    Example:
        >>> is_slack_timestamp("1234567890.123456")
        True
        >>> is_slack_timestamp("invalid")
        False
    """
    try:
        parts = value.split(".")
        return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()
    except (AttributeError, ValueError):
        return False
