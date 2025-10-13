"""
Example demonstrating how to use the DecoratorHandler class.

This example shows how to:
1. Create a DecoratorHandler instance
2. Register event handlers using both attribute-style and enum-style decorators
3. Handle event subtypes
4. Register multiple handlers for the same event
5. Mix synchronous and asynchronous handlers
6. Handle errors in event handlers
7. Create multiple isolated handler instances
8. Use the handler with a SlackEventConsumer
"""

import asyncio
import logging
from typing import Any, Dict, cast

from slack_mcp.backends.queue.memory import MemoryBackend
from slack_mcp.events import SlackEvent
from slack_mcp.webhook.event.consumer import SlackEventConsumer
from slack_mcp.webhook.event.handler.decorator import DecoratorHandler

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Create a DecoratorHandler instance
slack_event = DecoratorHandler()


# ---- Basic Usage Examples ----


# Register handlers using attribute-style decorators
@slack_event.message
async def handle_message(event: Dict[str, Any]) -> None:
    """Handle message events."""
    logger.info(f"Received message: {event.get('text', '')}")
    # Your message handling logic here


@slack_event.reaction_added
async def handle_reaction(event: Dict[str, Any]) -> None:
    """Handle reaction_added events."""
    logger.info(f"Reaction added: {event.get('reaction', '')}")
    # Your reaction handling logic here


# Register handlers using enum-style decorators
@slack_event(SlackEvent.APP_MENTION)
async def handle_app_mention(event: Dict[str, Any]) -> None:
    """Handle app_mention events."""
    logger.info(f"App mentioned: {event.get('text', '')}")
    # Your app mention handling logic here


@slack_event(SlackEvent.REACTION_ADDED)
async def handle_emoji_change(event: Dict[str, Any]) -> None:
    """Handle emoji_changed events."""
    logger.info(f"[Decorator-Enum] Emoji added event: {event.get('name', '')}")


# ---- Advanced Usage Examples ----


# Register a handler for a specific message subtype
@slack_event("message.channel_join")
def handle_channel_join(event: Dict[str, Any]) -> None:
    """Handle channel_join message subtype (synchronous handler)."""
    logger.info(f"User joined channel: {event.get('user', '')}")
    # Note: This is a synchronous handler (no async keyword)


# Register multiple handlers for the same event type
@slack_event.channel_created
async def log_channel_creation(event: Dict[str, Any]) -> None:
    """First handler for channel_created events."""
    logger.info(f"Channel created: {event.get('channel', {}).get('name', '')}")


@slack_event.channel_created
async def notify_admin_channel_creation(event: Dict[str, Any]) -> None:
    """Second handler for channel_created events."""
    channel_name = event.get("channel", {}).get("name", "")
    logger.info(f"Admin notification: New channel '{channel_name}' created")


# Handler that returns a value (can be used for processing pipelines)
@slack_event.pin_added
async def process_pin(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process pin_added events and return enriched data."""
    item = event.get("item", {})
    enriched_data = {
        "pin_type": item.get("type"),
        "channel": event.get("channel_id"),
        "timestamp": event.get("event_ts"),
        "pinned_by": event.get("user"),
    }
    logger.info(f"Pin processed: {enriched_data}")
    return enriched_data


# Error handling example
@slack_event.user_change
async def handle_user_change_with_error(event: Dict[str, Any]) -> None:
    """Demonstrate error handling in event handlers."""
    try:
        # Deliberately cause an error
        user_profile = event["user"]["profile"]
        nonexistent_field = user_profile["nonexistent_field"]
        logger.info(f"This won't be reached: {nonexistent_field}")
    except KeyError as e:
        logger.error(f"Error in user_change handler: {e}")
        # The error is caught here, preventing it from crashing the consumer


# Register a wildcard handler for all events
@slack_event
async def log_all_events(event: Dict[str, Any]) -> None:
    """Log all events."""
    event_type = event.get("type", "unknown")
    subtype = event.get("subtype", "")
    event_id = f"{event_type}{f'.{subtype}' if subtype else ''}"
    logger.debug(f"Received event: {event_id}")


# ---- Handler Isolation Example ----

# Create a second, isolated handler instance for a different component
analytics_handler = DecoratorHandler()


@analytics_handler.message
async def track_message_analytics(event: Dict[str, Any]) -> None:
    """Track analytics for message events in a separate handler."""
    logger.info("Analytics: Message event tracked")


@analytics_handler.reaction_added
async def track_reaction_analytics(event: Dict[str, Any]) -> None:
    """Track analytics for reaction events in a separate handler."""
    logger.info("Analytics: Reaction event tracked")


# ---- Custom Event Type Example ----


@slack_event("custom.event")
async def handle_custom_event(event: Dict[str, Any]) -> None:
    """Handle a custom event type not defined in SlackEvent enum."""
    logger.info(f"Custom event received: {event.get('data', '')}")


async def main() -> None:
    """Run the example."""
    # Create a memory backend for testing
    backend = MemoryBackend()

    # Create SlackEventConsumers with our handlers
    main_consumer = SlackEventConsumer(backend=backend, handler=slack_event)
    analytics_consumer = SlackEventConsumer(backend=backend, handler=analytics_handler)

    # Start the consumers in separate tasks
    main_consumer_task = asyncio.create_task(main_consumer.run(slack_event.handle_event))
    analytics_consumer_task = asyncio.create_task(analytics_consumer.run(analytics_handler.handle_event))

    # Give consumers a moment to start
    await asyncio.sleep(0.1)

    # Publish some test events to the backend
    # For MemoryBackend, we need to use a topic key (we'll use "slack_events")
    topic = "slack_events"
    test_events = [
        {"type": "message", "text": "Hello, world!"},
        {"type": "message", "subtype": "channel_join", "user": "U12345"},
        {"type": "reaction_added", "reaction": "thumbsup"},
        {"type": "app_mention", "text": "<@U12345> How are you?"},
        {"type": "channel_created", "channel": {"name": "new-project"}},
        {
            "type": "pin_added",
            "item": {"type": "message"},
            "channel_id": "C12345",
            "event_ts": "1234567890.123456",
            "user": "U12345",
        },
        {"type": "user_change", "user": {"profile": {}}},  # Will cause handled error
        {"type": "custom.event", "data": "Custom event data"},
    ]

    # Publish events with a small delay between them
    for event in test_events:
        await backend.publish(topic, cast(dict[str, Any], event))
        await asyncio.sleep(0.1)  # Small delay to make logs more readable

    # Let consumers run for a bit to process all events
    await asyncio.sleep(1)

    # Demonstrate handler methods and inspection
    logger.info("\n--- Handler Inspection ---")
    handlers = slack_event.get_handlers()
    logger.info(f"Registered event types: {list(handlers.keys())}")
    logger.info(f"Number of message handlers: {len(handlers.get('message', []))}")

    # Shut down the consumers
    await main_consumer.shutdown()
    await analytics_consumer.shutdown()
    await main_consumer_task
    await analytics_consumer_task

    logger.info("Example completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
