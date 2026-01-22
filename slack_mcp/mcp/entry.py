"""Command-line entry point to launch the Slack MCP server.

This module provides the main entry point for running the Slack MCP (Model Context Protocol) server.
It supports multiple transport modes (stdio, SSE, streamable-http) and can run in standalone or
integrated mode (with webhook server).

Module Overview
===============
The Slack MCP server enables AI assistants and other tools to interact with Slack workspaces
through a standardized MCP interface. It provides tools for:
- Sending messages to channels
- Reading channel and thread messages
- Adding emoji reactions
- Managing Slack events

Transport Modes
===============
1. **stdio** (default): Standard input/output transport for local MCP clients
2. **sse**: Server-Sent Events transport for HTTP-based clients
3. **streamable-http**: Streamable HTTP transport for HTTP-based clients

Server Modes
============
1. **Standalone**: Runs only the MCP server
2. **Integrated**: Runs both MCP server and webhook server for Slack event handling

Quick Start Examples
====================

**1. Run with default stdio transport:**

    .. code-block:: bash

        python -m slack_mcp.mcp.entry

**2. Run with SSE transport on port 8000:**

    .. code-block:: bash

        python -m slack_mcp.mcp.entry --transport sse --host 0.0.0.0 --port 8000

**3. Run with streamable-http transport:**

    .. code-block:: bash

        python -m slack_mcp.mcp.entry --transport streamable-http --host 0.0.0.0 --port 8000

**4. Run in integrated mode (MCP + Webhook):**

    .. code-block:: bash

        python -m slack_mcp.mcp.entry --integrated --transport sse --host 0.0.0.0 --port 8000

**5. Using curl to test HTTP endpoints (SSE/Streamable-HTTP):**

    .. code-block:: bash

        # Health check
        curl http://localhost:8000/health

        # MCP SSE endpoint
        curl http://localhost:8000/mcp/sse

**6. Using Python to interact with the server:**

    .. code-block:: python

        import asyncio
        from slack_mcp.mcp.server import send_slack_message
        from slack_mcp.mcp.model.input import SlackPostMessageInput

        async def main():
            input_params = SlackPostMessageInput(
                channel="C12345678",
                text="Hello from MCP!"
            )
            response = await send_slack_message(input_params)
            print(response)

        asyncio.run(main())

Environment Variables
======================
- **SLACK_BOT_TOKEN**: Slack bot token (required, xoxb-...)
- **SLACK_USER_TOKEN**: Slack user token (optional, xoxp-...)
- **SLACK_SIGNING_SECRET**: Slack signing secret for webhooks (required for integrated mode)
- **SLACK_TEST_CHANNEL**: Test channel name (optional, #channel)
- **SLACK_TEST_CHANNEL_ID**: Test channel ID (optional, C1234567890)
- **QUEUE_BACKEND**: Queue backend type (optional, memory/redis/kafka, defaults to memory)
- **REDIS_URL**: Redis connection URL (when using redis backend)
- **KAFKA_BOOTSTRAP**: Kafka bootstrap servers (when using kafka backend)

Configuration Files
===================
The server supports loading environment variables from a .env file:

    .. code-block:: bash

        # Load from custom .env file
        python -m slack_mcp.mcp.entry --env-file /path/to/.env

        # Skip loading .env file
        python -m slack_mcp.mcp.entry --no-env-file

Logging
=======
Control logging verbosity with the --log-level option:

    .. code-block:: bash

        # Debug logging
        python -m slack_mcp.mcp.entry --log-level DEBUG

        # Info logging (default)
        python -m slack_mcp.mcp.entry --log-level INFO

        # Warning logging
        python -m slack_mcp.mcp.entry --log-level WARNING

Docker Usage
============
The server is designed to run in Docker containers. See README_DOCKERHUB.md for detailed
Docker deployment instructions.

    .. code-block:: bash

        # Build Docker image
        docker build -t slack-mcp-server .

        # Run with SSE transport
        docker run -e SLACK_BOT_TOKEN=xoxb-... \\
                   -e MCP_TRANSPORT=sse \\
                   -e MCP_HOST=0.0.0.0 \\
                   -e MCP_PORT=8000 \\
                   -p 8000:8000 \\
                   slack-mcp-server

        # Run in integrated mode
        docker run -e SLACK_BOT_TOKEN=xoxb-... \\
                   -e SLACK_SIGNING_SECRET=... \\
                   -e SERVICE_TYPE=integrated \\
                   -e MCP_TRANSPORT=sse \\
                   -p 8000:8000 \\
                   slack-mcp-server
"""

import logging
import os
import pathlib
from typing import Final, Optional

import uvicorn

from slack_mcp.integrate.app import integrated_factory
from slack_mcp.logging.config import setup_logging_from_args
from slack_mcp.settings import get_settings

from .app import mcp_factory
from .cli import _parse_args
from .server import set_slack_client_retry_count

_LOG: Final[logging.Logger] = logging.getLogger(__name__)


def main(argv: Optional[list[str]] = None) -> None:
    """Launch the Slack MCP server with specified configuration.

    This is the main entry point for the Slack MCP server. It handles:
    1. Parsing command-line arguments
    2. Setting up logging
    3. Loading environment variables from .env file
    4. Initializing Slack client with retry settings
    5. Starting the server in standalone or integrated mode

    Parameters
    ----------
    argv : Optional[list[str]], optional
        Command-line arguments to parse. If None, uses sys.argv.
        Useful for testing and programmatic invocation.

    Returns
    -------
    None

    Raises
    ------
    SystemExit
        If integrated mode is requested with stdio transport (not supported)

    Examples
    --------
    **Run with default settings (stdio transport):**

    .. code-block:: python

        from slack_mcp.mcp.entry import main
        main()

    **Run with SSE transport on custom port:**

    .. code-block:: python

        main(["--transport", "sse", "--port", "8000"])

    **Run in integrated mode:**

    .. code-block:: python

        main(["--integrated", "--transport", "sse", "--port", "8000"])

    **Command-line usage:**

    .. code-block:: bash

        # Show help
        python -m slack_mcp.mcp.entry --help

        # Run with SSE transport
        python -m slack_mcp.mcp.entry --transport sse --host 0.0.0.0 --port 8000

        # Run in integrated mode with streamable-http
        python -m slack_mcp.mcp.entry --integrated --transport streamable-http --port 8000

        # Run with custom .env file
        python -m slack_mcp.mcp.entry --env-file /etc/slack-mcp/.env

        # Run with debug logging
        python -m slack_mcp.mcp.entry --log-level DEBUG

    Notes
    -----
    - The Slack bot token is required and can be provided via:
      1. SLACK_BOT_TOKEN environment variable
      2. --slack-token command-line argument
      3. .env file (takes precedence over CLI argument)

    - Integrated mode requires:
      1. SLACK_SIGNING_SECRET environment variable
      2. HTTP transport (sse or streamable-http)
      3. Both MCP and webhook servers will run on the same port

    - Retry count affects Slack API client behavior:
      - 0: No retries
      - >0: Automatic retry on rate limits and server errors
    """
    args = _parse_args(argv)

    # Use centralized logging configuration
    setup_logging_from_args(args)

    # Initialize settings using SettingModel (pydantic-settings)
    # 1. Prepare kwargs for settings with CLI token as fallback
    settings_kwargs = {}
    if args.slack_token:
        settings_kwargs["slack_bot_token"] = args.slack_token

    # 2. Initialize SettingModel which will pick up values from .env file, 
    # environment variables, and CLI fallbacks
    # Note: pydantic-settings handles .env file loading automatically
    try:
        # Check if .env file exists and warn if it doesn't (for user feedback)
        if not args.no_env_file and args.env_file:
            env_path = pathlib.Path(args.env_file)
            if not env_path.exists():
                _LOG.warning(f"Environment file not found: {env_path.resolve()}")
        
        settings = get_settings(env_file=args.env_file, no_env_file=args.no_env_file, force_reload=True, **settings_kwargs)
    except Exception as e:
        _LOG.error(f"Failed to load configuration: {e}")
        return

    # Determine if we should run the integrated server
    if args.integrated:
        if args.transport == "stdio":
            _LOG.error("Integrated mode is not supported with stdio transport")
            return

        _LOG.info(f"Starting integrated Slack server (MCP + Webhook) on {args.host}:{args.port}")

        # Get effective token from settings
        assert settings.slack_bot_token
        effective_token = settings.slack_bot_token.get_secret_value()

        # Create integrated app with both MCP and webhook functionality
        app = integrated_factory.create(
            token=effective_token, mcp_transport=args.transport, mcp_mount_path=args.mount_path, retry=args.retry
        )
        from slack_mcp.mcp.server import update_slack_client
        from slack_mcp.webhook.server import slack_client

        update_slack_client(token=effective_token, client=slack_client)

        # Run the integrated FastAPI app
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        if args.retry:
            set_slack_client_retry_count(retry=args.retry)

        _LOG.info("Starting Slack MCP server: transport=%s", args.transport)

        if args.transport in ["sse", "streamable-http"]:
            # For HTTP-based transports, get the appropriate app using the transport-specific method
            _LOG.info(f"Running FastAPI server on {args.host}:{args.port}")

            # Get the FastAPI app for the specific HTTP transport
            if args.transport == "sse":
                # sse_app is a method that takes mount_path as a parameter
                app = mcp_factory.get().sse_app(mount_path=args.mount_path)
            else:  # streamable-http
                # streamable_http_app doesn't accept mount_path parameter
                app = mcp_factory.get().streamable_http_app()
                if args.mount_path:
                    _LOG.warning("mount-path is not supported for streamable-http transport and will be ignored")

            # Use uvicorn to run the FastAPI app
            uvicorn.run(app, host=args.host, port=args.port)
        else:
            # For stdio transport, use the run method directly
            _LOG.info("Running stdio transport")
            mcp_factory.get().run(transport=args.transport)


if __name__ == "__main__":  # pragma: no cover
    main()
