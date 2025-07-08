"""Slack event server implementation.

This module provides a standalone server that integrates with the Slack Events API
and handles events like mentions and emoji reactions.
"""

from __future__ import annotations

import asyncio
import logging
import pathlib
from typing import Any, Final

from dotenv import load_dotenv

from slack_mcp.integrated_server import create_integrated_app
from slack_mcp.mcp.server import FastMCP, mcp

from .cli.options import _parse_args
from .server import create_slack_app, initialize_slack_client

__all__: list[str] = [
    "run_slack_server",
    "register_mcp_tools",
    "run_integrated_server",
]

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.webhook.entry")


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
    retry: int = 3,
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
    retry : int
        Number of retry attempts for network operations (default: 3)
    """
    _LOG.info(f"Starting Slack events server on {host}:{port}")

    # Create the Slack app
    app = create_slack_app()

    # Initialize the global Slack client with the provided token and retry settings
    initialize_slack_client(token, retry=retry)

    # Using uvicorn for ASGI support with FastAPI
    import uvicorn

    config = uvicorn.Config(app=app, host=host, port=port)
    server = uvicorn.Server(config=config)
    await server.serve()


async def run_integrated_server(
    host: str = "0.0.0.0",
    port: int = 3000,
    token: str | None = None,
    mcp_transport: str = "sse",
    mcp_mount_path: str | None = "/mcp",
    retry: int = 3,
) -> None:
    """Run the integrated server with both MCP and webhook functionalities.

    Parameters
    ----------
    host : str
        The host to listen on
    port : int
        The port to listen on
    token : str | None
        The Slack bot token to use. If None, will use environment variables.
    mcp_transport : str
        The transport to use for the MCP server. Either "sse" or "streamable-http".
    mcp_mount_path : str | None
        The mount path for the MCP server. Only used for sse transport.
    retry : int
        Number of retry attempts for network operations (default: 3)
    """
    _LOG.info(f"Starting integrated Slack server (MCP + Webhook) on {host}:{port}")

    # Create the integrated app with both MCP and webhook functionalities
    app = create_integrated_app(
        token=token,
        mcp_transport=mcp_transport,
        mcp_mount_path=mcp_mount_path,
        retry=retry,
    )

    _LOG.info(f"Starting integrated Slack server (MCP + Webhook) on {host}:{port}")

    # Using uvicorn for ASGI support with FastAPI
    import uvicorn

    config = uvicorn.Config(app=app, host=host, port=port)
    server = uvicorn.Server(config=config)
    await server.serve()


def main(argv: list[str] | None = None) -> None:
    """Run the Slack events server as a standalone application."""
    args = _parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s [%(levelname)8s] %(message)s")

    # Load environment variables from .env file if not disabled
    if not args.no_env_file:
        env_path = pathlib.Path(args.env_file)
        if env_path.exists():
            _LOG.info(f"Loading environment variables from {env_path.resolve()}")
            load_dotenv(dotenv_path=env_path)
        else:
            _LOG.warning(f"Environment file not found: {env_path.resolve()}")

    # Register MCP tools
    register_mcp_tools(mcp)

    # Determine whether to run in integrated mode or standalone mode
    if args.integrated:
        # Run the integrated server
        asyncio.run(
            run_integrated_server(
                host=args.host,
                port=args.port,
                token=args.slack_token,
                mcp_transport=args.mcp_transport,
                mcp_mount_path=args.mcp_mount_path,
                retry=args.retry,
            )
        )
    else:
        # Run the standalone webhook server
        asyncio.run(run_slack_server(host=args.host, port=args.port, token=args.slack_token, retry=args.retry))


if __name__ == "__main__":
    main()
