"""
Example demonstrating type checking with the Slack MCP Server package.

This example shows how to use the types module for static type checking
with MyPy and other type checkers.

Run MyPy on this file to verify type checking:
    uv run mypy examples/type_checking_example.py
"""

from __future__ import annotations

from typing import Any

from slack_mcp import SlackEvent, types
from slack_mcp.webhook.event.handler import BaseSlackEventHandler


# Example 1: Using type annotations with Slack events
class TypedSlackHandler(BaseSlackEventHandler):
    """Example handler with proper type annotations."""

    async def on_message(self, event: types.SlackEventPayload) -> None:
        """Handle message events with type safety."""
        # Type checker knows these are the correct types
        channel: types.SlackChannelID = event["channel"]
        text: str = event.get("text", "")
        user: types.SlackUserID = event.get("user", "")
        timestamp: types.SlackTimestamp = event.get("ts", "")

        print(f"Message from {user} in {channel} at {timestamp}: {text}")

    async def on_reaction_added(self, event: types.SlackEventPayload) -> None:
        """Handle reaction events with type safety."""
        reaction: str = event.get("reaction", "")
        user: types.SlackUserID = event.get("user", "")
        item: dict[str, Any] = event.get("item", {})

        print(f"User {user} added reaction :{reaction}: to {item}")


# Example 2: Using Protocol types
class CustomEventHandler:
    """Custom handler that implements EventHandlerProtocol."""

    async def handle_event(self, event: types.SlackEventPayload) -> None:
        """Handle any Slack event."""
        event_type: types.SlackEventType = event.get("type", "unknown")
        print(f"Handling event type: {event_type}")


def register_handler(handler: types.EventHandlerProtocol) -> None:
    """Register a handler using the protocol type.

    This function accepts any object that implements the EventHandlerProtocol,
    regardless of inheritance hierarchy.
    """
    print(f"Registered handler: {handler.__class__.__name__}")


# Example 3: Using type guards
def validate_slack_identifiers(
    channel: str, user: str, timestamp: str
) -> tuple[bool, bool, bool]:
    """Validate Slack identifiers using type guards."""
    is_valid_channel = types.is_slack_channel_id(channel)
    is_valid_user = types.is_slack_user_id(user)
    is_valid_timestamp = types.is_slack_timestamp(timestamp)

    return is_valid_channel, is_valid_user, is_valid_timestamp


# Example 4: Working with queue backends
async def process_queue_messages(backend: types.QueueBackendProtocol) -> None:
    """Process messages from a queue backend with type safety."""
    async for message in backend.consume(group="example-consumer"):
        payload: types.QueuePayload = message
        event_type: str = payload.get("type", "unknown")
        print(f"Processing queue message: {event_type}")


# Example 5: Using JSON types
def process_json_data(data: types.JSONDict) -> types.JSONValue:
    """Process JSON data with proper type annotations."""
    # Type checker knows data is a dictionary
    event_type: types.JSONValue = data.get("type")
    nested_data: types.JSONDict = data.get("event", {})  # type: ignore

    return nested_data


# Example 6: Working with transport types
def configure_transport(transport: types.TransportType) -> dict[str, Any]:
    """Configure MCP transport with type safety."""
    config: dict[str, Any] = {"transport": transport}

    if transport == "sse":
        config["host"] = "0.0.0.0"
        config["port"] = 8000
    elif transport == "streamable-http":
        config["host"] = "0.0.0.0"
        config["port"] = 8000
    elif transport == "stdio":
        config["stdio"] = True

    return config


# Example 7: Event handler function types
async def async_message_handler(event: types.SlackEventPayload) -> None:
    """Async event handler function."""
    print(f"Async handler: {event.get('type')}")


def sync_message_handler(event: types.SlackEventPayload) -> None:
    """Sync event handler function."""
    print(f"Sync handler: {event.get('type')}")


def register_event_handler(handler: types.EventHandlerFunc) -> None:
    """Register an event handler (sync or async)."""
    print(f"Registered handler: {handler.__name__}")


# Main demonstration
def main() -> None:
    """Demonstrate type checking features."""
    print("=== Type Checking Examples ===\n")

    # Example 1: Handler with protocol compliance
    handler = TypedSlackHandler()
    register_handler(handler)

    # Example 2: Custom handler with protocol compliance
    custom_handler = CustomEventHandler()
    register_handler(custom_handler)

    # Example 3: Type guards
    print("\n=== Type Guard Validation ===")
    results = validate_slack_identifiers("C1234567890", "U1234567890", "1234567890.123456")
    print(f"Channel valid: {results[0]}")
    print(f"User valid: {results[1]}")
    print(f"Timestamp valid: {results[2]}")

    # Example 4: Invalid identifiers
    invalid_results = validate_slack_identifiers("invalid", "bad", "wrong")
    print(f"Invalid channel: {not invalid_results[0]}")
    print(f"Invalid user: {not invalid_results[1]}")
    print(f"Invalid timestamp: {not invalid_results[2]}")

    # Example 5: Transport configuration
    print("\n=== Transport Configuration ===")
    for transport in ["stdio", "sse", "streamable-http"]:
        config = configure_transport(transport)  # type: ignore
        print(f"{transport}: {config}")

    # Example 6: SlackEvent enum
    print("\n=== SlackEvent Enum ===")
    print(f"Total events: {len(SlackEvent)}")
    print(f"Message event: {SlackEvent.MESSAGE}")
    print(f"Reaction added: {SlackEvent.REACTION_ADDED}")

    # Example 7: Event handler registration
    print("\n=== Event Handler Registration ===")
    register_event_handler(async_message_handler)
    register_event_handler(sync_message_handler)

    print("\n✓ All type checking examples completed successfully!")


if __name__ == "__main__":
    main()
