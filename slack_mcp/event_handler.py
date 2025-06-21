"""Slack event handler implementation for processing Slack events.

This module defines handlers for specific Slack events like mentions and emoji reactions.
It follows PEP 484/585 typing conventions.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Final, Protocol, TypedDict, cast

from slack_sdk.web.async_client import AsyncWebClient

__all__: list[str] = [
    "SlackEventHandler",
    "handle_app_mention",
    "handle_reaction_added",
    "register_handlers",
]

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.event_handler")


class EventCallback(TypedDict, total=False):
    """Type for Slack event callback data structure."""

    type: str
    user: str
    text: str
    ts: str
    channel: str
    item: dict[str, Any]
    reaction: str
    event_ts: str
    thread_ts: str | None


class SlackEvent(TypedDict, total=False):
    """Type for Slack event data structure."""

    token: str
    team_id: str
    api_app_id: str
    event: EventCallback
    type: str
    event_id: str
    event_time: int
    authorizations: list[dict[str, Any]]
    is_ext_shared_channel: bool


class EventHandler(Protocol):
    """Protocol for event handlers."""

    async def __call__(self, client: AsyncWebClient, event: EventCallback) -> dict[str, Any]: ...


async def handle_app_mention(client: AsyncWebClient, event: EventCallback) -> dict[str, Any]:
    """Handle app_mention event when someone mentions the bot in a channel or thread.

    Parameters
    ----------
    client : AsyncWebClient
        The Slack client to use for API calls
    event : EventCallback
        The event data from Slack

    Returns
    -------
    dict[str, Any]
        The response from the Slack API
    """
    channel = event["channel"]
    text = event["text"]
    thread_ts = event.get("thread_ts", event["ts"])

    # Remove the bot mention from the text
    clean_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    if not clean_text:
        response_text = "Hello! I'm your Slack bot. How can I help you today?"
    else:
        response_text = f"You said: {clean_text}"

    _LOG.info(f"Responding to mention in channel {channel} with text: {response_text}")

    return await client.chat_postMessage(channel=channel, text=response_text, thread_ts=thread_ts)


async def handle_reaction_added(client: AsyncWebClient, event: EventCallback) -> dict[str, Any]:
    """Handle reaction_added event when someone adds an emoji reaction to a bot message.

    Parameters
    ----------
    client : AsyncWebClient
        The Slack client to use for API calls
    event : EventCallback
        The event data from Slack

    Returns
    -------
    dict[str, Any]
        The response from the Slack API
    """
    item = event["item"]
    channel = item["channel"]
    ts = item["ts"]
    reaction = event["reaction"]
    user = event["user"]

    # Get the message that was reacted to
    message_response = await client.conversations_history(channel=channel, latest=ts, inclusive=True, limit=1)

    messages = cast(list[dict[str, Any]], message_response.get("messages", []))
    if not messages:
        _LOG.warning(f"Could not find message {ts} in channel {channel}")
        return {"ok": False, "error": "Message not found"}

    # Check if the message was sent by this bot
    message = messages[0]
    bot_id = os.environ.get("SLACK_BOT_ID")

    if not bot_id:
        _LOG.warning("SLACK_BOT_ID not set in environment")
        # Try to get bot information from the message
        if message.get("bot_id") or message.get("app_id"):
            _LOG.info(f"Reaction {reaction} added to bot message by user {user}")
            response_text = f"Thanks for reacting with :{reaction}: to my message!"
            return await client.chat_postMessage(channel=channel, text=response_text, thread_ts=ts)
        return {"ok": False, "error": "Not a bot message"}

    # If we have bot_id, check if the message was sent by this bot
    if message.get("bot_id") == bot_id or message.get("app_id") == bot_id:
        _LOG.info(f"Reaction {reaction} added to bot message by user {user}")
        response_text = f"Thanks for reacting with :{reaction}: to my message!"
        return await client.chat_postMessage(channel=channel, text=response_text, thread_ts=ts)

    return {"ok": True, "message": "Not a bot message"}


def register_handlers() -> dict[str, EventHandler]:
    """Register event handlers for Slack events.

    Returns
    -------
    dict[str, EventHandler]
        A dictionary mapping event types to their handlers
    """
    return {
        "app_mention": handle_app_mention,
        "reaction_added": handle_reaction_added,
    }
