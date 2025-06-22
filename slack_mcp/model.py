from __future__ import annotations

from dataclasses import dataclass
from typing import List

__all__: list[str] = [
    "SlackPostMessageInput",
    "SlackThreadReplyInput",
]


@dataclass(slots=True, kw_only=True)
class SlackPostMessageInput:
    """
    Structured input for :pydata:`send_slack_message`.

    :param channel: the channel ID (e.g. C12345678) or name with ``#`` prefix (e.g. ``#general``)
    :param text: the text content of the message
    :param token: the Slack bot token to use (optional, default to ``None``)
        If not provided, it will attempt to get one from environment variable
        ``SLACK_BOT_TOKEN`` or ``SLACK_TOKEN``.
    """

    channel: str
    text: str
    token: str | None = None


@dataclass(slots=True, kw_only=True)
class SlackThreadReplyInput:
    """
    Structured input for :pydata:`send_slack_thread_reply`.

    :param channel: the channel ID (e.g. C12345678) or name with ``#`` prefix (e.g. ``#general``)
    :param thread_ts: the timestamp of the thread parent message to reply to
    :param texts: a list of text messages to send as replies to the thread
    :param token: the Slack bot token to use (optional, default to ``None``)
        If not provided, it will attempt to get one from environment variable
        ``SLACK_BOT_TOKEN`` or ``SLACK_TOKEN``.
    """

    channel: str
    thread_ts: str
    texts: List[str]
    token: str | None = None
