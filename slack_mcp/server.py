"""Slack MCP server implementation using FastMCP.

This module defines the :pydata:`FastMCP` server instance as well as the first
MCP *tool* for sending a message to a Slack channel.  The implementation follows
PEP 484/585 typing conventions and can be imported directly so that external
applications or test-suites may interact with the exported ``mcp`` instance.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Final, List

from mcp.server.fastmcp import FastMCP
from slack_sdk.web.async_client import AsyncWebClient

__all__: list[str] = [
    "mcp",
    "send_slack_message",
    "read_thread_messages",
    "read_slack_channel_messages",
    "send_slack_thread_reply",
    "read_slack_emojis",
]

from slack_mcp.model import (
    SlackPostMessageInput,
    SlackReadChannelMessagesInput,
    SlackReadEmojisInput,
    SlackReadThreadMessagesInput,
    SlackThreadReplyInput,
    _BaseInput,
)

# A single FastMCP server instance to be discovered by the MCP runtime.
SERVER_NAME: Final[str] = "SlackMCPServer"

mcp: Final[FastMCP] = FastMCP(name=SERVER_NAME)


def _verify_slack_token_exist(input_params: _BaseInput) -> str:
    resolved_token: str | None = input_params.token or os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_TOKEN")
    if resolved_token is None:
        raise ValueError(
            "Slack token not found. Provide one via the 'token' argument or set "
            "the SLACK_BOT_TOKEN/SLACK_TOKEN environment variable."
        )
    return resolved_token


@mcp.tool("slack_post_message")
async def send_slack_message(
    input_params: SlackPostMessageInput,
) -> dict[str, Any]:
    """Send *text* to the given Slack *channel*.

    Parameters
    ----------
    input_params
        SlackPostMessageInput object containing channel, text, and token.

    Returns
    -------
    dict[str, Any]
        The raw JSON response returned by Slack.  This is intentionally kept
        flexible so FastMCP can serialise it to the client as-is.

    Raises
    ------
    ValueError
        If no *token* is supplied and the relevant environment variables are
        missing as well.
    """

    resolved_token = _verify_slack_token_exist(input_params)

    client: AsyncWebClient = AsyncWebClient(token=resolved_token)

    response = await client.chat_postMessage(channel=input_params.channel, text=input_params.text)

    # Slack SDK returns a SlackResponse object whose ``data`` attr is JSON-serialisable.
    return response.data


@mcp.tool("slack_read_thread_messages")
async def read_thread_messages(
    input_params: SlackReadThreadMessagesInput,
) -> dict[str, Any]:
    """Read messages from a specific thread in a given Slack channel.

    Parameters
    ----------
    input_params
        SlackReadThreadMessagesInput object containing channel, thread_ts, token, and limit.

    Returns
    -------
    dict[str, Any]
        The raw JSON response returned by Slack.  This is intentionally kept
        flexible so FastMCP can serialise it to the client as-is.

    Raises
    ------
    ValueError
        If no *token* is supplied and the relevant environment variables are
        missing as well.
    """

    resolved_token = _verify_slack_token_exist(input_params)

    client: AsyncWebClient = AsyncWebClient(token=resolved_token)

    response = await client.conversations_replies(
        channel=input_params.channel,
        ts=input_params.thread_ts,
        limit=input_params.limit,
    )

    # Slack SDK returns a SlackResponse object whose ``data`` attr is JSON-serialisable.
    return response.data


@mcp.tool("slack_read_channel_messages")
async def read_slack_channel_messages(
    input_params: SlackReadChannelMessagesInput,
) -> dict[str, Any]:
    """Read messages from the given Slack *channel*.

    Parameters
    ----------
    input_params
        SlackReadChannelMessagesInput object containing channel and optional parameters.

    Returns
    -------
    dict[str, Any]
        The raw JSON response returned by Slack.  This is intentionally kept
        flexible so FastMCP can serialise it to the client as-is.

    Raises
    ------
    ValueError
        If no *token* is supplied and the relevant environment variables are
        missing as well.
    """

    resolved_token = _verify_slack_token_exist(input_params)

    client: AsyncWebClient = AsyncWebClient(token=resolved_token)

    response = await client.conversations_history(
        channel=input_params.channel,
        limit=input_params.limit,
        oldest=input_params.oldest,
        latest=input_params.latest,
        inclusive=input_params.inclusive,
    )

    # Slack SDK returns a SlackResponse object whose ``data`` attr is JSON-serialisable.
    return response.data


@mcp.tool("slack_thread_reply")
async def send_slack_thread_reply(
    input_params: SlackThreadReplyInput,
) -> dict[str, Any]:
    """Send one or more messages as replies to a specific thread in a Slack channel.

    Parameters
    ----------
    input_params
        SlackThreadReplyInput object containing channel, thread_ts, texts, and token.

    Returns
    -------
    dict[str, Any]
        A dictionary containing a list of responses under the 'responses' key.
        Each response is the raw JSON returned by Slack for each message posted.

    Raises
    ------
    ValueError
        If no *token* is supplied and the relevant environment variables are
        missing as well.
    """

    resolved_token = _verify_slack_token_exist(input_params)

    client: AsyncWebClient = AsyncWebClient(token=resolved_token)

    responses: List[Dict[str, Any]] = []

    # Send each text message as a separate reply to the thread
    for text in input_params.texts:
        response = await client.chat_postMessage(
            channel=input_params.channel, text=text, thread_ts=input_params.thread_ts
        )
        responses.append(response.data)

    # Return a dictionary with the responses list to ensure proper serialization
    return {"responses": responses}


@mcp.tool("slack_read_emojis")
async def read_slack_emojis(
    input_params: SlackReadEmojisInput,
) -> dict[str, Any]:
    """Get all emojis (both built-in and custom) available in the Slack workspace.

    Parameters
    ----------
    input_params
        SlackReadEmojisInput object containing token.

    Returns
    -------
    dict[str, Any]
        The raw JSON response returned by Slack. This contains a mapping of emoji
        names to their URLs or aliases.

    Raises
    ------
    ValueError
        If no *token* is supplied and the relevant environment variables are
        missing as well.
    """

    resolved_token = _verify_slack_token_exist(input_params)

    client: AsyncWebClient = AsyncWebClient(token=resolved_token)

    response = await client.emoji_list(include_categories=True)

    # Slack SDK returns a SlackResponse object whose ``data`` attr is JSON-serialisable.
    return response.data


# ---------------------------------------------------------------------------
# Guidance prompt for LLMs
# ---------------------------------------------------------------------------


@mcp.prompt("slack_post_message_usage")
def _slack_post_message_usage() -> str:  # noqa: D401 – imperative style acceptable for prompt
    """Explain when and how to invoke the ``slack_post_message`` tool."""

    return (
        "Use `slack_post_message` whenever you need to deliver a textual "
        "notification to a Slack channel on behalf of the user. Typical "
        "scenarios include:\n"
        " • Alerting a team channel about build/deployment status.\n"
        " • Sending reminders or summaries after completing an automated task.\n"
        " • Broadcasting important events (e.g., incident reports, new blog post).\n\n"
        "Input guidelines:\n"
        " • **channel** — Slack channel ID (e.g., `C12345678`) or name with `#`.\n"
        " • **text**    — The plain-text message to post (up to 40 kB).\n"
        " • **token**   — *Optional.* Provide if the default bot token env var is unavailable.\n\n"
        "The tool returns the raw JSON response from Slack. If the response's `ok` field is `false`, "
        "consider the operation failed and surface the `error` field to the user."
    )


@mcp.prompt("slack_read_channel_messages_usage")
def _slack_read_channel_messages_usage() -> str:  # noqa: D401 – imperative style acceptable for prompt
    """Explain when and how to invoke the ``slack_read_channel_messages`` tool."""

    return (
        "Use `slack_read_channel_messages` whenever you need to retrieve message history from a "
        "Slack channel. Typical scenarios include:\n"
        " • Analyzing conversation context or recent discussions.\n"
        " • Monitoring channel activity.\n"
        " • Retrieving important information that was previously shared.\n\n"
        "Input guidelines:\n"
        " • **channel** — Slack channel ID (e.g., `C12345678`) or name with `#`.\n"
        " • **limit**   — *Optional.* Maximum number of messages to return (default: 100, max: 1000).\n"
        " • **oldest**  — *Optional.* Start of time range; Unix timestamp (e.g., `1234567890.123456`).\n"
        " • **latest**  — *Optional.* End of time range; Unix timestamp (e.g., `1234567890.123456`).\n"
        " • **inclusive** — *Optional.* Include messages with timestamps exactly matching oldest/latest.\n"
        " • **token**   — *Optional.* Provide if the default bot token env var is unavailable.\n\n"
        "The tool returns the raw JSON response from Slack. If the response's `ok` field is `false`, "
        "consider the operation failed and surface the `error` field to the user. The response will "
        "include an array of messages in the `messages` field."
    )


@mcp.prompt("slack_read_thread_messages_usage")
def _slack_read_thread_messages_usage() -> str:  # noqa: D401 – imperative style acceptable for prompt
    """Explain when and how to invoke the ``slack_read_thread_messages`` tool."""

    return (
        "Use `slack_read_thread_messages` whenever you need to retrieve messages from a "
        "specific thread in a Slack channel. Typical scenarios include:\n"
        " • Accessing conversation history for analysis or summarization.\n"
        " • Following up on previous discussions or retrieving context.\n"
        " • Monitoring responses to important announcements.\n\n"
        "Input guidelines:\n"
        " • **channel**   — Slack channel ID (e.g., `C12345678`) or name with `#`.\n"
        " • **thread_ts** — Timestamp ID of the parent message that started the thread.\n"
        " • **limit**     — *Optional.* Maximum number of messages to retrieve (default: 100).\n"
        " • **token**     — *Optional.* Provide if the default bot token env var is unavailable.\n\n"
        "The tool returns the raw JSON response from Slack, containing thread messages under "
        "the `messages` field. If the response's `ok` field is `false`, consider the operation "
        "failed and surface the `error` field to the user."
    )


@mcp.prompt("slack_thread_reply_usage")
def _slack_thread_reply_usage() -> str:  # noqa: D401 – imperative style acceptable for prompt
    """Explain when and how to invoke the ``slack_thread_reply`` tool."""

    return (
        "Use `slack_thread_reply` when you need to send one or more follow-up messages "
        "as replies to an existing thread in a Slack channel. This is particularly useful for:\n"
        " • Continuing a conversation in a structured thread.\n"
        " • Breaking down a complex response into multiple messages.\n"
        " • Sending updates to a previously initiated conversation.\n"
        " • Keeping related messages organized in a single thread.\n\n"
        "Input guidelines:\n"
        " • **channel** — Slack channel ID (e.g., `C12345678`) or name with `#`.\n"
        " • **thread_ts** — The timestamp ID of the parent message to reply to.\n"
        " • **texts** — A list of text messages to send as separate replies to the thread.\n"
        " • **token** — *Optional.* Provide if the default bot token env var is unavailable.\n\n"
        "The tool returns a dictionary containing a list of raw JSON responses from Slack (one for each message). "
        "If any response's `ok` field is `false`, consider that particular message failed "
        "and surface the corresponding `error` field to the user."
    )


@mcp.prompt("slack_read_emojis_usage")
def _slack_read_emojis_usage() -> str:  # noqa: D401 – imperative style acceptable for prompt
    """Explain when and how to invoke the ``slack_read_emojis`` tool."""

    return (
        "Use `slack_read_emojis` when you need to retrieve all emojis available in the Slack workspace. "
        "This includes both standard (built-in) Slack emojis and any custom emojis that have been "
        "added to the workspace. Typical scenarios include:\n"
        " • Providing a list of available emojis for users to reference.\n"
        " • Determining which emojis (especially custom ones) are available for use in messages.\n"
        " • Analyzing emoji usage and availability in a workspace.\n\n"
        "Input guidelines:\n"
        " • **token** — *Optional.* Provide if the default bot token env var is unavailable.\n\n"
        "The tool returns the raw JSON response from Slack. If the response's `ok` field is `false`, "
        "consider the operation failed and surface the `error` field to the user. The response will "
        "include a mapping of emoji names to either URLs (for custom emojis) or alias strings (for "
        "standard emojis that are aliased to other emojis) in the `emoji` field."
    )
