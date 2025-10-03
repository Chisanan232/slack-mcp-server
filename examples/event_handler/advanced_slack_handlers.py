"""
Advanced Slack Event Handler Example

This example demonstrates handling various Slack event types using both:
1. OO-style handler (subclassing BaseSlackEventHandler)
2. Decorator-style handlers (using both enum arguments and attribute access)

The example shows how to handle:
- Common message events with different subtypes
- Reaction events (added/removed)
- Channel events (created, renamed, etc.)
- User presence changes
- App-related events
- And more!

This can be used as a reference for implementing handlers for any event
listed in docs/.ai_discussion_conclusion/all_slack_event_types.md
"""

import asyncio
import logging
from typing import Any, Dict

from slack_mcp.backends.loader import load_backend
from slack_mcp.events import SlackEvent
from slack_mcp.webhook.event.consumer import SlackEventConsumer
from slack_mcp.webhook.event.handler.base import BaseSlackEventHandler
from slack_mcp.webhook.event.handler.decorator import DecoratorHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Create DecoratorHandler instance for decorator-style handlers
slack_event = DecoratorHandler()


# ===== PART 1: OO-STYLE HANDLER =====


class AdvancedSlackEventHandler(BaseSlackEventHandler):
    """OO-style Slack event handler showing various event type implementations."""

    def __init__(self):
        super().__init__()
        self.channel_info = {}  # Example state storage
        self.reaction_counts = {}  # Example counter for reactions

    # === Message Events ===

    async def on_message(self, event: Dict[str, Any]) -> None:
        """Handle general message events."""
        logger.info(f"[OO] Message received: {event.get('text', '')}")

    async def on_message__channels(self, event: Dict[str, Any]) -> None:
        """Handle message.channels events (messages in public channels)."""
        channel = event.get("channel")
        text = event.get("text", "")
        logger.info(f"[OO] Channel message in {channel}: {text}")

        # Example of extracting mentions from a message
        if "<@" in text:
            mentions = [
                item.split("<@")[1].split(">")[0]
                for item in text.split()
                if item.startswith("<@") and item.endswith(">")
            ]
            logger.info(f"[OO] Mentioned users: {mentions}")

    async def on_message__im(self, event: Dict[str, Any]) -> None:
        """Handle message.im events (direct messages)."""
        user = event.get("user")
        text = event.get("text", "")
        logger.info(f"[OO] DM from {user}: {text}")

        # Example of handling commands in DMs
        if text.startswith("!"):
            command = text[1:].split()[0]
            logger.info(f"[OO] Command received in DM: {command}")

    # === Reaction Events ===

    async def on_reaction_added(self, event: Dict[str, Any]) -> None:
        """Handle reaction_added events."""
        reaction = event.get("reaction", "")
        item = event.get("item", {})
        user = event.get("user", "")

        # Example of tracking reaction counts
        if reaction not in self.reaction_counts:
            self.reaction_counts[reaction] = 0
        self.reaction_counts[reaction] += 1

        logger.info(f"[OO] Reaction :{reaction}: added by {user} to item type: {item.get('type')}")

    # === Channel Events ===

    async def on_channel_created(self, event: Dict[str, Any]) -> None:
        """Handle channel_created events."""
        channel_info = event.get("channel", {})
        channel_id = channel_info.get("id")
        name = channel_info.get("name")

        # Store channel info for later use
        self.channel_info[channel_id] = channel_info

        logger.info(f"[OO] Channel created: #{name} ({channel_id})")

    async def on_channel_rename(self, event: Dict[str, Any]) -> None:
        """Handle channel_rename events."""
        channel = event.get("channel", {})
        channel_id = channel.get("id")
        new_name = channel.get("name")

        # Update stored channel info
        if channel_id in self.channel_info:
            old_name = self.channel_info[channel_id].get("name", "unknown")
            self.channel_info[channel_id]["name"] = new_name
            logger.info(f"[OO] Channel renamed from #{old_name} to #{new_name}")
        else:
            logger.info(f"[OO] Channel renamed to #{new_name}")

    # === User Events ===

    async def on_user_change(self, event: Dict[str, Any]) -> None:
        """Handle user_change events (profile updates, status changes)."""
        user = event.get("user", {})
        user_id = user.get("id")
        real_name = user.get("real_name", "Unknown")
        status_text = user.get("profile", {}).get("status_text", "")

        logger.info(f"[OO] User {real_name} ({user_id}) updated profile. Status: {status_text}")

    # === App Events ===

    async def on_app_mention(self, event: Dict[str, Any]) -> None:
        """Handle app_mention events (when the app is @mentioned)."""
        user = event.get("user")
        text = event.get("text", "")
        channel = event.get("channel")

        logger.info(f"[OO] App mentioned by {user} in {channel}: {text}")

        # Example command parsing from mentions
        cleaned_text = text.split(">", 1)[1].strip() if ">" in text else text
        words = cleaned_text.split()
        if words:
            command = words[0]
            args = words[1:]
            logger.info(f"[OO] Command from mention: {command}, args: {args}")

    # === Unknown Events ===

    async def on_unknown(self, event: Dict[str, Any]) -> None:
        """Handle any events that don't have specific handlers."""
        event_type = event.get("type", "unknown")
        logger.info(f"[OO] Received unhandled event type: {event_type}")


# ===== PART 2: DECORATOR-STYLE HANDLERS WITH ENUM ARGUMENTS =====


@slack_event(SlackEvent.TEAM_JOIN)
async def handle_team_join(event: Dict[str, Any]) -> None:
    """Handle team_join events when new users join the workspace."""
    user = event.get("user", {})
    user_id = user.get("id")
    name = user.get("real_name", user.get("name", "Unknown"))

    logger.info(f"[Decorator-Enum] New user joined: {name} ({user_id})")


@slack_event(SlackEvent.EMOJI_CHANGED)
async def handle_emoji_changes(event: Dict[str, Any]) -> None:
    """Handle emoji_changed events (emoji added, removed, or renamed)."""
    subtype = event.get("subtype")
    name = event.get("name")

    if subtype == "add":
        logger.info(f"[Decorator-Enum] New emoji added: :{name}:")
    elif subtype == "remove":
        names = event.get("names", [name] if name else [])
        logger.info(f"[Decorator-Enum] Emoji(s) removed: {', '.join([f':{n}:' for n in names])}")
    elif subtype == "rename":
        old_name = event.get("old_name", "unknown")
        logger.info(f"[Decorator-Enum] Emoji renamed from :{old_name}: to :{name}:")


@slack_event(SlackEvent.CHANNEL_ARCHIVE)
@slack_event(SlackEvent.CHANNEL_UNARCHIVE)
async def handle_channel_archive_events(event: Dict[str, Any]) -> None:
    """Handle both channel archive and unarchive events with a single function."""
    channel = event.get("channel")
    user = event.get("user")
    is_archived = event.get("type") == "channel_archive"
    action = "archived" if is_archived else "unarchived"

    logger.info(f"[Decorator-Enum] Channel {channel} was {action} by {user}")


# Example of a priority handler (called first with priority=0)
@slack_event(SlackEvent.MESSAGE, priority=0)
async def log_all_messages(event: Dict[str, Any]) -> None:
    """Log all messages (runs before other message handlers due to priority)."""
    event_id = event.get("event_ts", "unknown")
    logger.info(f"[Decorator-Enum] Message received with ID: {event_id} (PRIORITY HANDLER)")


# ===== PART 3: DECORATOR-STYLE HANDLERS WITH ATTRIBUTE ACCESS =====


@slack_event.member_joined_channel
async def handle_member_join(event: Dict[str, Any]) -> None:
    """Handle member_joined_channel events."""
    user = event.get("user")
    channel = event.get("channel")

    logger.info(f"[Decorator-Attr] User {user} joined channel {channel}")


@slack_event.member_left_channel
async def handle_member_leave(event: Dict[str, Any]) -> None:
    """Handle member_left_channel events."""
    user = event.get("user")
    channel = event.get("channel")

    logger.info(f"[Decorator-Attr] User {user} left channel {channel}")


@slack_event.pin_added
async def handle_pin_added(event: Dict[str, Any]) -> None:
    """Handle pin_added events."""
    user = event.get("user")
    item = event.get("item", {})
    channel = event.get("channel_id")
    item_type = item.get("type")

    logger.info(f"[Decorator-Attr] {user} pinned a {item_type} in channel {channel}")


@slack_event.message_app_home
async def handle_app_home_message(event: Dict[str, Any]) -> None:
    """Handle message.app_home events (messages in the app home)."""
    user = event.get("user")
    text = event.get("text", "")

    logger.info(f"[Decorator-Attr] App Home message from {user}: {text}")


# Wildcard handler for all events
@slack_event
async def track_all_events(event: Dict[str, Any]) -> None:
    """Example wildcard handler that receives all events."""
    event_type = event.get("type")
    event_id = event.get("event_ts", event.get("ts", "unknown"))

    # This would normally go to a metrics system or database
    logger.debug(f"[Decorator-Attr] Event tracked: {event_type} ({event_id})")


# ===== MAIN APPLICATION =====


async def main():
    """Set up and run the Slack event consumer with all handler types."""
    # Load backend based on environment variables (memory, redis, etc.)
    backend = load_backend()

    # Create OO-style handler instance
    oo_handler = AdvancedSlackEventHandler()

    # Create consumer with OO-style handler
    oo_consumer = SlackEventConsumer(backend, oo_handler, group="oo_handlers")

    # Create consumer with decorator-style handler
    decorator_consumer = SlackEventConsumer(backend, slack_event, group="decorator_handlers")

    try:
        logger.info("Starting Slack event consumers with advanced handlers...")
        logger.info("- OO-style handler consumer running in group 'oo_handlers'")
        logger.info("- Decorator-style handler consumer running in group 'decorator_handlers'")

        # Run both consumers concurrently
        await asyncio.gather(oo_consumer.run(), decorator_consumer.run())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        await asyncio.gather(oo_consumer.shutdown(), decorator_consumer.shutdown(), return_exceptions=True)
    except Exception as e:
        logger.exception(f"Error in consumer: {e}")
    finally:
        logger.info("All consumers stopped")


# Entry point
if __name__ == "__main__":
    asyncio.run(main())
