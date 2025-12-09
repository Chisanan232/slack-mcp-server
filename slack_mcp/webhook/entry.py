"""Slack event server implementation.

This module provides a standalone server that integrates with the Slack Events API
and handles events like mentions and emoji reactions.

Module Overview
===============
The Slack webhook server listens for events from Slack and publishes them to a message queue
backend (memory, Redis, or Kafka). This allows decoupled processing of Slack events through
custom consumers.

Key Features
============
- **Event Listening**: Receives Slack events via HTTP webhooks
- **Event Publishing**: Publishes events to configurable message queue backends
- **Health Checks**: Built-in health check endpoint for monitoring
- **Signature Verification**: Validates all incoming requests are from Slack
- **Integrated Mode**: Can run alongside MCP server in integrated mode

Server Modes
============
1. **Standalone**: Runs only the webhook server
2. **Integrated**: Runs both webhook server and MCP server

Quick Start Examples
====================

**1. Run webhook server standalone:**

    .. code-block:: bash

        python -m slack_mcp.webhook.entry --host 0.0.0.0 --port 3000

**2. Run in integrated mode with MCP:**

    .. code-block:: bash

        python -m slack_mcp.webhook.entry --integrated --mcp-transport sse --port 3000

**3. Using curl to test endpoints:**

    .. code-block:: bash

        # Health check
        curl http://localhost:3000/health

        # Slack event endpoint (requires valid Slack signature)
        curl -X POST http://localhost:3000/slack/events \\
             -H "Content-Type: application/json" \\
             -H "X-Slack-Request-Timestamp: $(date +%s)" \\
             -H "X-Slack-Signature: v0=..." \\
             -d '{"type":"url_verification","challenge":"..."}'

**4. Using Python to interact with the server:**

    .. code-block:: python

        import asyncio
        from slack_mcp.webhook.entry import run_slack_server

        async def main():
            await run_slack_server(
                host="0.0.0.0",
                port=3000,
                token="xoxb-...",
                retry=3
            )

        asyncio.run(main())

**5. Using wget to check server health:**

    .. code-block:: bash

        wget -q -O- http://localhost:3000/health | jq .

Environment Variables
======================
- **SLACK_BOT_TOKEN**: Slack bot token (required, xoxb-...)
- **SLACK_SIGNING_SECRET**: Slack signing secret for webhook verification (required)
- **SLACK_EVENTS_TOPIC**: Message queue topic for events (default: slack_events)
- **QUEUE_BACKEND**: Queue backend type (memory/redis/kafka, defaults to memory)
- **REDIS_URL**: Redis connection URL (when using redis backend)
- **KAFKA_BOOTSTRAP**: Kafka bootstrap servers (when using kafka backend)

Configuration Files
===================
The server supports loading environment variables from a .env file:

    .. code-block:: bash

        # Load from default .env file
        python -m slack_mcp.webhook.entry

        # Load from custom .env file
        python -m slack_mcp.webhook.entry --env-file /path/to/.env

        # Skip loading .env file
        python -m slack_mcp.webhook.entry --no-env-file

Docker Usage
============
The server is designed to run in Docker containers:

    .. code-block:: bash

        # Build Docker image
        docker build -t slack-webhook-server .

        # Run webhook server
        docker run -e SLACK_BOT_TOKEN=xoxb-... \\
                   -e SLACK_SIGNING_SECRET=... \\
                   -e QUEUE_BACKEND=memory \\
                   -p 3000:3000 \\
                   slack-webhook-server

        # Run in integrated mode
        docker run -e SLACK_BOT_TOKEN=xoxb-... \\
                   -e SLACK_SIGNING_SECRET=... \\
                   -e SERVICE_TYPE=integrated \\
                   -e MCP_TRANSPORT=sse \\
                   -p 3000:3000 \\
                   slack-webhook-server

Event Processing
================
Events are processed as follows:
1. Slack sends event to /slack/events endpoint
2. Server verifies request signature using SLACK_SIGNING_SECRET
3. Event is deserialized and validated
4. Event is published to message queue backend
5. Custom consumers can process events from the queue

Supported Events
================
The server supports all Slack event types including:
- message events
- reaction_added / reaction_removed
- app_mention
- member_joined_channel
- And many more...

See https://api.slack.com/events for the complete list of Slack events.
"""

import asyncio
import logging
import os
import pathlib
from typing import Any, Dict, Final, Optional

from dotenv import load_dotenv
from mcp.server import FastMCP

from slack_mcp.integrate.app import integrated_factory
from slack_mcp.logging.config import setup_logging_from_args
from slack_mcp.mcp.app import mcp_factory

from .cli.options import _parse_args
from .server import create_slack_app, initialize_slack_client

__all__: list[str] = [
    "run_slack_server",
    "register_mcp_tools",
    "run_integrated_server",
]

_LOG: Final[logging.Logger] = logging.getLogger(__name__)


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
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start listening for Slack events.

        Parameters
        ----------
        port : int
            The port to listen on
        token : Optional[str]
            The Slack bot token to use. If None, will use environment variables.

        Returns
        -------
        Dict[str, Any]
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
    token: Optional[str] = None,
    retry: int = 3,
) -> None:
    """Run the Slack events server.

    This function starts an async Slack webhook server that listens for events from Slack
    and publishes them to a message queue backend. It's designed to be run in a separate
    process or coroutine from the MCP server.

    Parameters
    ----------
    host : str, optional
        The host interface to listen on. Default is "0.0.0.0" (all interfaces).
        Use "127.0.0.1" for localhost-only access.
    port : int, optional
        The port number to listen on. Default is 3000.
    token : Optional[str], optional
        The Slack bot token to use. If None, will use SLACK_BOT_TOKEN environment variable.
    retry : int, optional
        Number of retry attempts for Slack API operations. Default is 3.
        Set to 0 to disable retries.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If no token is provided and SLACK_BOT_TOKEN environment variable is not set.

    Examples
    --------
    **Run webhook server on default port:**

    .. code-block:: python

        import asyncio
        from slack_mcp.webhook.entry import run_slack_server

        asyncio.run(run_slack_server())

    **Run on custom host and port:**

    .. code-block:: python

        asyncio.run(run_slack_server(host="127.0.0.1", port=8080))

    **Run with explicit token:**

    .. code-block:: python

        asyncio.run(run_slack_server(
            token="xoxb-your-token-here",
            retry=5
        ))

    **Command-line usage:**

    .. code-block:: bash

        python -m slack_mcp.webhook.entry --host 0.0.0.0 --port 3000

    Notes
    -----
    - The server requires SLACK_SIGNING_SECRET to verify incoming Slack requests
    - Events are published to the message queue backend specified by QUEUE_BACKEND env var
    - The health check endpoint is available at /health
    - The Slack events endpoint is available at /slack/events
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
    token: Optional[str] = None,
    mcp_transport: str = "sse",
    mcp_mount_path: Optional[str] = "/mcp",
    retry: int = 3,
) -> None:
    """Run the integrated server with both MCP and webhook functionalities.

    This function starts an async server that combines both the Slack webhook server
    (for event listening) and the MCP server (for Slack tool access) in a single
    process. Both services run on the same port with different URL paths.

    Parameters
    ----------
    host : str, optional
        The host interface to listen on. Default is "0.0.0.0" (all interfaces).
        Use "127.0.0.1" for localhost-only access.
    port : int, optional
        The port number to listen on. Default is 3000.
    token : Optional[str], optional
        The Slack bot token to use. If None, will use SLACK_BOT_TOKEN environment variable.
    mcp_transport : str, optional
        The transport protocol for the MCP server. Must be "sse" or "streamable-http".
        Default is "sse".
    mcp_mount_path : Optional[str], optional
        The URL path where the MCP server is mounted. Default is "/mcp".
        Only used for SSE transport. Ignored for streamable-http.
    retry : int, optional
        Number of retry attempts for Slack API operations. Default is 3.
        Set to 0 to disable retries.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If an invalid transport is specified or if required environment variables are missing.

    Examples
    --------
    **Run integrated server with SSE transport:**

    .. code-block:: python

        import asyncio
        from slack_mcp.webhook.entry import run_integrated_server

        asyncio.run(run_integrated_server(
            token="xoxb-your-token-here",
            mcp_transport="sse"
        ))

    **Run with streamable-http transport:**

    .. code-block:: python

        asyncio.run(run_integrated_server(
            token="xoxb-your-token-here",
            mcp_transport="streamable-http"
        ))

    **Command-line usage:**

    .. code-block:: bash

        # Run integrated server
        python -m slack_mcp.webhook.entry --integrated --mcp-transport sse --port 3000

        # Run with streamable-http
        python -m slack_mcp.webhook.entry --integrated --mcp-transport streamable-http --port 3000

    **Using curl to access endpoints:**

    .. code-block:: bash

        # Health check
        curl http://localhost:3000/health

        # MCP SSE endpoint (for SSE transport)
        curl http://localhost:3000/mcp/sse

        # Slack events endpoint
        curl -X POST http://localhost:3000/slack/events \\
             -H "X-Slack-Request-Timestamp: ..." \\
             -H "X-Slack-Signature: ..."

    Notes
    -----
    - Both MCP and webhook services run on the same port
    - Webhook events are published to the message queue backend
    - MCP tools are available at the specified mount path
    - Health check endpoint is available at /health
    - Requires SLACK_SIGNING_SECRET for webhook verification
    """
    _LOG.info(f"Starting integrated Slack server (MCP + Webhook) on {host}:{port}")

    # Create the integrated app with both MCP and webhook functionalities
    app = integrated_factory.create(
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


def main(argv: Optional[list[str]] = None) -> None:
    """Run the Slack events server as a standalone application.

    This is the main entry point for the Slack webhook server. It handles:
    1. Parsing command-line arguments
    2. Setting up logging
    3. Loading environment variables from .env file
    4. Registering MCP tools
    5. Starting the server in standalone or integrated mode

    Parameters
    ----------
    argv : Optional[list[str]], optional
        Command-line arguments to parse. If None, uses sys.argv.
        Useful for testing and programmatic invocation.

    Returns
    -------
    None

    Examples
    --------
    **Run webhook server with default settings:**

    .. code-block:: python

        from slack_mcp.webhook.entry import main
        main()

    **Run with custom port:**

    .. code-block:: python

        main(["--port", "8080"])

    **Run in integrated mode:**

    .. code-block:: python

        main(["--integrated", "--mcp-transport", "sse"])

    **Command-line usage:**

    .. code-block:: bash

        # Show help
        python -m slack_mcp.webhook.entry --help

        # Run webhook server
        python -m slack_mcp.webhook.entry --host 0.0.0.0 --port 3000

        # Run in integrated mode
        python -m slack_mcp.webhook.entry --integrated --mcp-transport sse --port 3000

        # Run with custom .env file
        python -m slack_mcp.webhook.entry --env-file /etc/slack-mcp/.env

        # Run with debug logging
        python -m slack_mcp.webhook.entry --log-level DEBUG

    Notes
    -----
    - The Slack bot token is required and can be provided via:
      1. SLACK_BOT_TOKEN environment variable
      2. --slack-token command-line argument
      3. .env file (takes precedence over CLI argument)

    - Webhook mode requires:
      1. SLACK_SIGNING_SECRET environment variable
      2. Proper Slack app configuration with event subscriptions

    - Integrated mode requires:
      1. Both SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET
      2. HTTP transport (sse or streamable-http)
      3. Both services run on the same port
    """
    args = _parse_args(argv)

    # Use centralized logging configuration
    setup_logging_from_args(args)

    # Set Slack token from command line argument first (as fallback)
    if args.slack_token:
        os.environ["SLACK_BOT_TOKEN"] = args.slack_token
        _LOG.info("Using Slack token from command line argument (fallback)")

    # Load environment variables from .env file if not disabled
    # This will override CLI arguments, giving .env file priority
    if not args.no_env_file:
        env_path = pathlib.Path(args.env_file)
        if env_path.exists():
            _LOG.info(f"Loading environment variables from {env_path.resolve()}")
            load_dotenv(dotenv_path=env_path, override=True)
        else:
            _LOG.warning(f"Environment file not found: {env_path.resolve()}")

    # Register MCP tools
    register_mcp_tools(mcp_factory.get())

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
