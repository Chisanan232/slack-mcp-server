"""Data models for Slack MCP server functions."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import List

__all__: list[str] = [
    "SlackPostMessageInput",
    "SlackReadThreadMessagesInput",
    "SlackReadChannelMessagesInput",
    "SlackThreadReplyInput",
    "SlackReadEmojisInput",
    "SlackAddReactionsInput",
]


@dataclass(slots=True, kw_only=True)
class _BaseInput(ABC):
    """
    Base abstract class for Slack input models.

    All Slack tokens are now managed centrally by the SlackClientManager.
    Tokens are resolved from environment variables (SLACK_BOT_TOKEN or SLACK_TOKEN).
    """


@dataclass(slots=True, kw_only=True)
class SlackPostMessageInput(_BaseInput):
    """
    Structured input for :pydata:`send_slack_message`.

    :param channel: the channel ID (e.g. C12345678) or name with ``#`` prefix (e.g. ``#general``)
    :param text: the text content of the message
    """

    channel: str
    text: str


@dataclass(slots=True, kw_only=True)
class SlackReadThreadMessagesInput(_BaseInput):
    """
    Structured input for :pydata:`read_thread_messages`.

    :param channel: the channel ID (e.g. C12345678) or name with ``#`` prefix (e.g. ``#general``)
    :param thread_ts: the timestamp of the thread's parent message
    :param limit: maximum number of messages to return (optional, default is 100)
    """

    channel: str
    thread_ts: str
    limit: int = 100


@dataclass(slots=True, kw_only=True)
class SlackReadChannelMessagesInput(_BaseInput):
    """
    Structured input for :pydata:`read_slack_channel_messages`.

    :param channel: the channel ID (e.g. C12345678) or name with ``#`` prefix (e.g. ``#general``)
    :param limit: the maximum number of messages to return (optional, default to 100)
    :param oldest: the oldest message timestamp to include (optional, default to None)
    :param latest: the latest message timestamp to include (optional, default to None)
    :param inclusive: include messages with timestamps matching oldest or latest (optional, default to False)
    """

    channel: str
    limit: int = 100
    oldest: str | None = None
    latest: str | None = None
    inclusive: bool = False


@dataclass(slots=True, kw_only=True)
class SlackThreadReplyInput(_BaseInput):
    """
    Structured input for :pydata:`send_slack_thread_reply`.

    :param channel: the channel ID (e.g. C12345678) or name with ``#`` prefix (e.g. ``#general``)
    :param thread_ts: the timestamp of the thread parent message to reply to
    :param texts: a list of text messages to send as replies to the thread
    """

    channel: str
    thread_ts: str
    texts: List[str]


@dataclass(slots=True, kw_only=True)
class SlackReadEmojisInput(_BaseInput):
    """
    Structured input for :pydata:`read_slack_emojis`.
    """


@dataclass(slots=True, kw_only=True)
class SlackAddReactionsInput(_BaseInput):
    """
    Structured input for :pydata:`add_slack_reactions`.

    :param channel: the channel ID (e.g. C12345678) or name with ``#`` prefix (e.g. ``#general``)
    :param timestamp: the timestamp of the message to react to
    :param emojis: a list of emoji names to add as reactions
    """

    channel: str
    timestamp: str
    emojis: List[str]
