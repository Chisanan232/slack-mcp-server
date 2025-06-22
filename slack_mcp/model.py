from __future__ import annotations

from dataclasses import dataclass

__all__: list[str] = [
    "SlackPostMessageInput",
    "SlackReadChannelMessagesInput",
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
class SlackReadChannelMessagesInput:
    """
    Structured input for :pydata:`read_slack_channel_messages`.

    :param channel: the channel ID (e.g. C12345678) or name with ``#`` prefix (e.g. ``#general``)
    :param limit: the maximum number of messages to return (optional, default to 100)
    :param oldest: the oldest message timestamp to include (optional, default to None)
    :param latest: the latest message timestamp to include (optional, default to None)
    :param inclusive: include messages with timestamps matching oldest or latest (optional, default to False)
    :param token: the Slack bot token to use (optional, default to ``None``)
        If not provided, it will attempt to get one from environment variable
        ``SLACK_BOT_TOKEN`` or ``SLACK_TOKEN``.
    """

    channel: str
    limit: int = 100
    oldest: str | None = None
    latest: str | None = None
    inclusive: bool = False
    token: str | None = None
