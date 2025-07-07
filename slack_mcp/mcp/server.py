"""Slack MCP server implementation using FastMCP.

This module defines the :pydata:`FastMCP` server instance as well as the first
MCP *tool* for sending a message to a Slack channel.  The implementation follows
PEP 484/585 typing conventions and can be imported directly so that external
applications or test-suites may interact with the exported ``mcp`` instance.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Final, Optional

from mcp.server.fastmcp import FastMCP
from slack_sdk.web.async_client import AsyncWebClient

from slack_mcp.client.manager import get_client_manager

from .model.input import (
    SlackAddReactionsInput,
    SlackPostMessageInput,
    SlackReadChannelMessagesInput,
    SlackReadEmojisInput,
    SlackReadThreadMessagesInput,
    SlackThreadReplyInput,
)

__all__: list[str] = [
    "mcp",
    "send_slack_message",
    "read_thread_messages",
    "read_slack_channel_messages",
    "send_slack_thread_reply",
    "read_slack_emojis",
    "add_slack_reactions",
    "set_slack_client_retry_count",
    "get_slack_client",
    "clear_slack_clients",
    "update_slack_client",
]

# A single FastMCP server instance to be discovered by the MCP runtime.
SERVER_NAME: Final[str] = "SlackMCPServer"

# Logger for this module
_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.server")

# Default token from environment
_DEFAULT_TOKEN = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_TOKEN")

mcp: Final[FastMCP] = FastMCP(name=SERVER_NAME)


def set_slack_client_retry_count(retry: int) -> None:
    """Set the retry count for Slack web client operations.

    This only affects the Slack API client's built-in retry mechanism
    and does not alter the core MCP server logic.

    Parameters
    ----------
    retry : int
        Number of retry attempts for Slack API operations
    """
    if retry < 0:
        raise ValueError("Retry count must be non-negative")

    # Get the client manager and update its retry count
    client_manager = get_client_manager()
    client_manager.update_retry_count(retry)
    _LOG.info(f"Slack client retry count set to {retry} and client cache cleared")


def get_slack_client(token: Optional[str] = None) -> AsyncWebClient:
    """Get a Slack client with the given token.

    Parameters
    ----------
    token : Optional[str], optional
        The Slack token to use. If None, will use environment variables.

    Returns
    -------
    AsyncWebClient
        The Slack client

    Raises
    ------
    ValueError
        If no token is found or provided
    """
    client_manager = get_client_manager()
    return client_manager.get_async_client(token=token)


def update_slack_client(token: Optional[str] = None, client: Optional[AsyncWebClient] = None) -> AsyncWebClient:
    """Update the token used by a Slack client.

    Parameters
    ----------
    token : Optional[str], optional
        The Slack token to use. If None, will use environment variables.
    client : Optional[AsyncWebClient], optional
        The client to update. If None, a new client will be created.

    Returns
    -------
    AsyncWebClient
        The updated client

    Raises
    ------
    ValueError
        If token is None or empty and not in a test environment
    """
    # Get the client manager
    client_manager = get_client_manager()

    # Check if we're in a test environment (indicated by PYTEST_CURRENT_TEST env var)
    in_test_env = "PYTEST_CURRENT_TEST" in os.environ

    if not token:
        if in_test_env:
            # In test environment, use a dummy token if none provided
            token = "xoxb-test-token-for-pytest"
            _LOG.debug("Using dummy token in test environment")
        else:
            raise ValueError("Token cannot be empty or None")

    if client:
        # Update the existing client's token
        client.token = token
        # Update the client in the manager's cache
        client_manager.update_client(token, client)
        return client

    # If no client provided, get or create one with the specified token
    return client_manager.get_async_client(token)


def clear_slack_clients() -> None:
    """Clear the Slack client cache.

    This forces new clients to be created on the next request.
    """
    # Get the client manager and clear its caches
    client_manager = get_client_manager()
    client_manager.clear_clients()
    _LOG.info("Slack client cache cleared")


def _get_default_client() -> AsyncWebClient:
    """Get a Slack client using the default token from environment variables.

    This function doesn't require a token parameter and relies on the
    SlackClientManager's default token resolution logic.

    Returns
    -------
    AsyncWebClient
        Initialized Slack AsyncWebClient instance.

    Raises
    ------
    ValueError
        If no token is found in the environment variables.
    """
    client_manager = get_client_manager()

    # Check if a token is available in the environment
    default_token = client_manager._default_token
    if not default_token:
        raise ValueError(
            "Slack token not found. Please provide a token or set "
            "SLACK_BOT_TOKEN or SLACK_TOKEN environment variables."
        )

    return client_manager.get_async_client()


@mcp.tool("slack_post_message")
async def send_slack_message(
    input_params: SlackPostMessageInput,
) -> dict[str, Any]:
    """Send *text* to the given Slack *channel*.

    Parameters
    ----------
    input_params
        SlackPostMessageInput object containing channel and text.

    Returns
    -------
    dict[str, Any]
        The raw JSON response returned by Slack.  This is intentionally kept
        flexible so FastMCP can serialise it to the client as-is.

    Raises
    ------
    ValueError
        If the relevant environment variables for Slack token are missing.
    """
    client = _get_default_client()

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
        SlackReadThreadMessagesInput object containing channel, thread_ts, and limit.

    Returns
    -------
    dict[str, Any]
        The raw JSON response returned by Slack.  This is intentionally kept
        flexible so FastMCP can serialise it to the client as-is.

    Raises
    ------
    ValueError
        If the relevant environment variables for Slack token are missing.
    """
    client = _get_default_client()

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
        If the relevant environment variables for Slack token are missing.
    """
    client = _get_default_client()

    # Build kwargs for the API call
    kwargs = {
        "channel": input_params.channel,
        "limit": input_params.limit,
    }

    # Add optional parameters if they are set
    if input_params.oldest:
        kwargs["oldest"] = input_params.oldest
    if input_params.latest:
        kwargs["latest"] = input_params.latest
    if input_params.inclusive:
        kwargs["inclusive"] = input_params.inclusive

    response = await client.conversations_history(**kwargs)

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
        SlackThreadReplyInput object containing channel, thread_ts, and texts.

    Returns
    -------
    dict[str, Any]
        A dictionary containing a list of responses under the 'responses' key.
        Each response is the raw JSON returned by Slack for each message posted.

    Raises
    ------
    ValueError
        If the relevant environment variables for Slack token are missing.
    """
    client = _get_default_client()

    responses = []
    for text in input_params.texts:
        response = await client.chat_postMessage(
            channel=input_params.channel,
            text=text,
            thread_ts=input_params.thread_ts,
        )
        responses.append(response.data)

    # Return a dictionary with a list of responses
    return {"responses": responses}


@mcp.tool("slack_read_emojis")
async def read_slack_emojis(
    input_params: SlackReadEmojisInput,
) -> dict[str, Any]:
    """Get all emojis (both built-in and custom) available in the Slack workspace.

    Parameters
    ----------
    input_params
        SlackReadEmojisInput object.

    Returns
    -------
    dict[str, Any]
        The raw JSON response returned by Slack. This contains a mapping of emoji
        names to their URLs or aliases.

    Raises
    ------
    ValueError
        If the relevant environment variables for Slack token are missing.
    """
    client = _get_default_client()

    response = await client.emoji_list()

    # Slack SDK returns a SlackResponse object whose ``data`` attr is JSON-serialisable.
    return response.data


@mcp.tool("slack_add_reactions")
async def add_slack_reactions(
    input_params: SlackAddReactionsInput,
) -> dict[str, Any]:
    """Add one or more emoji reactions to a specific message in a Slack channel.

    Parameters
    ----------
    input_params
        SlackAddReactionsInput object containing channel, timestamp, and emojis.

    Returns
    -------
    dict[str, Any]
        A dictionary containing a list of responses under the 'responses' key.
        Each response is the raw JSON returned by Slack for each emoji reaction added.

    Raises
    ------
    ValueError
        If the relevant environment variables for Slack token are missing.
    """
    client = _get_default_client()

    responses = []
    for emoji in input_params.emojis:
        response = await client.reactions_add(
            channel=input_params.channel,
            timestamp=input_params.timestamp,
            name=emoji,
        )
        responses.append(response.data)

    # Return a dictionary with a list of responses
    return {"responses": responses}


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
        " • **text**    — The plain-text message to post (up to 40 kB).\n\n"
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
        " • **inclusive** — *Optional.* Include messages with timestamps exactly matching oldest/latest.\n\n"
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
        " • **limit**     — *Optional.* Maximum number of messages to retrieve (default: 100).\n\n"
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
        " • **texts** — A list of text messages to send as separate replies to the thread.\n\n"
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
        "The tool returns the raw JSON response from Slack. If the response's `ok` field is `false`, "
        "consider the operation failed and surface the `error` field to the user. The response will "
        "include a mapping of emoji names to either URLs (for custom emojis) or alias strings (for "
        "standard emojis that are aliased to other emojis) in the `emoji` field."
    )


@mcp.prompt("slack_add_reactions_usage")
def _slack_add_reactions_usage() -> str:  # noqa: D401 – imperative style acceptable for prompt
    """Explain when and how to invoke the ``slack_add_reactions`` tool."""

    return (
        "Use `slack_add_reactions` when you need to add one or more emoji reactions to a specific message in a Slack channel. "
        "This allows adding emoji reactions to any message, including those in threads.\n\n"
        "Input guidelines:\n"
        " • **channel** — Slack channel ID (e.g., `C12345678`) or name with `#`.\n"
        " • **timestamp** — Timestamp ID of the message to react to.\n"
        " • **emojis** — A list of emoji names to add as reactions.\n\n"
        "The tool returns a dictionary containing a list of raw JSON responses from Slack (one for each emoji). "
        "If any response's `ok` field is `false`, consider that particular emoji failed "
        "and surface the corresponding `error` field to the user."
    )


def usage_prompt() -> str:
    """Report the overall consolidated usage prompt for this server."""

    return f"""
    # Slack Operations MCP Server

    This server exposes tools to interact with Slack from an MCP client.

    ## Available Tools

    ### slack_post_message

    {_slack_post_message_usage()}

    ### slack_read_channel_messages

    {_slack_read_channel_messages_usage()}

    ### slack_read_thread_messages

    {_slack_read_thread_messages_usage()}

    ### slack_thread_reply

    {_slack_thread_reply_usage()}

    ### slack_read_emojis

    {_slack_read_emojis_usage()}

    ### slack_add_reactions

    {_slack_add_reactions_usage()}
    """
