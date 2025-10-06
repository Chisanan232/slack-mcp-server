"""
Example implementation demonstrating all three Slack event handler styles.

This example shows:
1. OO-style handlers via BaseSlackEventHandler subclassing
2. Decorator-style handlers with Enum arguments
3. Decorator-style handlers with attribute access

All three styles can be used together or separately depending on your preference.
"""

import asyncio
import logging
from typing import Any, Dict

from slack_mcp.backends.loader import load_backend
from slack_mcp.events import SlackEvent
from slack_mcp.webhook.event.consumer import SlackEventConsumer
from slack_mcp.webhook.event.handler.base import BaseSlackEventHandler
from slack_mcp.webhook.event.handler.decorator import DecoratorHandler

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Create DecoratorHandler instance for decorator-style handlers
slack_event = DecoratorHandler()

# ----- 1. OO-Style Handler (Subclassing) -----


class MySlackHandler(BaseSlackEventHandler):
    """Example Slack event handler using the OO-style pattern."""

    async def on_message(self, event: Dict[str, Any]) -> None:
        """Handle generic message events."""
        logger.info(f"[OO-Style] Received message: {event.get('text', '')}")

    async def on_message__channels(self, event: Dict[str, Any]) -> None:
        """Handle message.channels events specifically."""
        channel = event.get("channel", "unknown")
        logger.info(f"[OO-Style] Channel message in {channel}: {event.get('text', '')}")

    async def on_reaction_added(self, event: Dict[str, Any]) -> None:
        """Handle reaction_added events."""
        reaction = event.get("reaction", "")
        logger.info(f"[OO-Style] Reaction added: :{reaction}:")

    async def on_unknown(self, event: Dict[str, Any]) -> None:
        """Handle unknown event types."""
        event_type = event.get("type", "unknown")
        logger.info(f"[OO-Style] Unknown event type: {event_type}")


# ----- 2. Decorator-Style Handler (Enum Arguments) -----


@slack_event(SlackEvent.APP_MENTION)
async def handle_app_mention(event: Dict[str, Any]) -> None:
    """Handle app_mention events."""
    logger.info(f"[Decorator-Enum] App mentioned: {event.get('text', '')}")


@slack_event(SlackEvent.REACTION_ADDED)
async def handle_emoji_add(event: Dict[str, Any]) -> None:
    """Handle emoji_changed events."""
    logger.info(f"[Decorator-Enum] Emoji added event: {event.get('name', '')}")


@slack_event(SlackEvent.EMOJI_CHANGED)
async def handle_emoji_change(event: Dict[str, Any]) -> None:
    """Handle emoji_changed events."""
    logger.info(f"[Decorator-Enum] Emoji changed event: {event.get('name', '')}")


# ----- 3. Decorator-Style Handler (Attribute Access) -----


@slack_event.reaction_removed
async def handle_reaction_removed(event: Dict[str, Any]) -> None:
    """Handle reaction_removed events."""
    reaction = event.get("reaction", "")
    logger.info(f"[Decorator-Attr] Reaction removed: :{reaction}:")


@slack_event.message_groups
async def handle_group_message(event: Dict[str, Any]) -> None:
    """Handle message.groups events."""
    group = event.get("channel", "unknown")
    logger.info(f"[Decorator-Attr] Group message in {group}: {event.get('text', '')}")


# ----- Main function to set up the consumer -----


async def main() -> None:
    """Set up and run the Slack event consumer."""
    # Load the backend based on environment variables
    backend = load_backend()

    # Create an instance of the OO-style handler
    handler = MySlackHandler()

    # Create the consumer with the OO-style handler
    # (The decorator-style handlers will be called automatically via dispatch_event)
    consumer = SlackEventConsumer(backend, handler)

    try:
        # Run the consumer indefinitely
        logger.info("Starting Slack event consumer...")
        await consumer.run(handler.handle_event)
    except KeyboardInterrupt:
        # Handle graceful shutdown
        logger.info("Shutting down...")
        await consumer.shutdown()


if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())
