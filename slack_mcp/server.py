"""Slack MCP server implementation using FastMCP.

This module defines the :pydata:`FastMCP` server instance as well as the first
MCP *tool* for sending a message to a Slack channel.  The implementation follows
PEP 484/585 typing conventions and can be imported directly so that external
applications or test-suites may interact with the exported ``mcp`` instance.
"""
from __future__ import annotations

from typing import Any, Final
import os

from slack_sdk.web.async_client import AsyncWebClient
from mcp.server.fastmcp import FastMCP

__all__: list[str] = [
    "mcp",
    "send_slack_message",
]

# A single FastMCP server instance to be discovered by the MCP runtime.
SERVER_NAME: Final[str] = "SlackMCPServer"

mcp: Final[FastMCP] = FastMCP(name=SERVER_NAME)


@mcp.tool()  # type: ignore[misc] – decorator runtime typing provided by FastMCP
async def send_slack_message(
    channel: str,
    text: str,
    *,
    token: str | None = None,
) -> dict[str, Any]:
    """Send *text* to the given Slack *channel*.

    Parameters
    ----------
    channel
        Channel ID (e.g. ``"C1234567890"``) or channel name with leading ``"#"``.
    text
        The message text to post.
    token
        Optional Slack *Bot* OAuth token.  If *None*, the function falls back to
        the value of :pydata:`os.environ["SLACK_BOT_TOKEN"]` – and then
        ``"SLACK_TOKEN"`` – if present.

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

    resolved_token: str | None = token or os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_TOKEN")
    if resolved_token is None:
        raise ValueError(
            "Slack token not found. Provide one via the 'token' argument or set "
            "the SLACK_BOT_TOKEN/SLACK_TOKEN environment variable."
        )

    client: AsyncWebClient = AsyncWebClient(token=resolved_token)

    response = await client.chat_postMessage(channel=channel, text=text)

    # Slack SDK returns a SlackResponse object whose ``data`` attr is JSON-serialisable.
    return response.data
