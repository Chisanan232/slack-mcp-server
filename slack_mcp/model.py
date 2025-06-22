from __future__ import annotations

from dataclasses import dataclass

__all__: list[str] = [
    "SlackPostMessageInput",
    "SlackReadThreadMessagesInput",
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
class SlackReadThreadMessagesInput:
    """
    Structured input for :pydata:`read_thread_messages`.

    :param channel: the channel ID (e.g. C12345678) or name with ``#`` prefix (e.g. ``#general``)
    :param thread_ts: the timestamp of the thread's parent message
    :param token: the Slack bot token to use (optional, default to ``None``)
        If not provided, it will attempt to get one from environment variable
        ``SLACK_BOT_TOKEN`` or ``SLACK_TOKEN``.
    :param limit: maximum number of messages to return (optional, default is 100)
    """

    channel: str
    thread_ts: str
    token: str | None = None
    limit: int = 100
