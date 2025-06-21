"""Slack event server implementation.

This module provides a standalone server that integrates with the Slack Events API
and handles events like mentions and emoji reactions.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Final

from .slack_app import create_slack_app
from .server import mcp, FastMCP
from .event_handler import EventCallback

__all__: list[str] = [
    "run_slack_server",
    "register_mcp_tools",
]

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.slack_server")


def register_mcp_tools(mcp_instance: FastMCP) -> None:
    """Register MCP tools related to Slack events.
    
    Parameters
    ----------
    mcp_instance : FastMCP
        The MCP instance to register tools with
    """
    
    @mcp_instance.tool("slack_listen_events")
    async def start_listening(
        port: int = 3000,
        token: str | None = None,
    ) -> dict[str, Any]:
        """Start listening for Slack events.
        
        Parameters
        ----------
        port : int
            The port to listen on
        token : str | None
            The Slack bot token to use. If None, will use environment variables.
            
        Returns
        -------
        dict[str, Any]
            Information about the server
        """
        # This isn't actually starting the server, just informing that it should be started separately
        _LOG.info(f"To start listening for Slack events, run the 'slack-events-server' script on port {port}")
        
        return {
            "status": "info",
            "message": f"To start listening for Slack events, run the 'slack-events-server' script on port {port}",
            "port": port,
        }
    
    @mcp_instance.prompt("slack_listen_events_usage")
    def _slack_listen_events_usage() -> str:
        """Explain when and how to invoke the ``slack_listen_events`` tool."""
        return (
            "Use `slack_listen_events` to get information about how to start the Slack events server.\n\n"
            "This tool returns information on how to start the server that will listen for Slack events like:\n"
            " • Someone mentioning the bot in a channel or thread\n"
            " • Someone adding an emoji reaction to a message sent by the bot\n\n"
            "Input guidelines:\n"
            " • **port** — *Optional.* The port to listen on (default: 3000)\n"
            " • **token** — *Optional.* Provide if the default bot token env var is unavailable.\n\n"
            "Note that this tool doesn't actually start the server; it just provides instructions on how to do so."
        )


async def run_slack_server(
    host: str = "0.0.0.0",
    port: int = 3000,
    token: str | None = None,
) -> None:
    """Run the Slack events server.
    
    Parameters
    ----------
    host : str
        The host to listen on
    port : int
        The port to listen on
    token : str | None
        The Slack bot token to use. If None, will use environment variables.
    """
    app = create_slack_app(token)
    
    _LOG.info(f"Starting Slack events server on {host}:{port}")
    
    # Using hypercorn for ASGI support
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    
    config = Config()
    config.bind = [f"{host}:{port}"]
    
    await serve(app, config)


def main() -> None:
    """Run the Slack events server as a standalone application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the Slack events server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to listen on (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to listen on (default: 3000)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level (e.g., DEBUG, INFO)",
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)8s] %(message)s"
    )
    
    # Register MCP tools
    register_mcp_tools(mcp)
    
    # Run the server
    asyncio.run(run_slack_server(host=args.host, port=args.port))


if __name__ == "__main__":
    main()
