"""Command-line entry point to launch the Slack MCP server."""

from __future__ import annotations

import logging
import os
import pathlib
from typing import Final

import uvicorn
from dotenv import load_dotenv

from slack_mcp.integrated_server import create_integrated_app

from .cli import _parse_args
from .server import mcp as _server_instance
from .server import set_slack_client_retry_count

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.entry")


def main(argv: list[str] | None = None) -> None:  # noqa: D401 – CLI entry
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

    # Set Slack token from command line argument if provided
    if args.slack_token:
        os.environ["SLACK_BOT_TOKEN"] = args.slack_token
        _LOG.info("Using Slack token from command line argument")

    # Determine if we should run the integrated server
    if args.integrated:
        if args.transport == "stdio":
            _LOG.error("Integrated mode is not supported with stdio transport")
            return

        _LOG.info(f"Starting integrated Slack server (MCP + Webhook) on {args.host}:{args.port}")

        # Create integrated app with both MCP and webhook functionality
        app = create_integrated_app(
            token=args.slack_token, mcp_transport=args.transport, mcp_mount_path=args.mount_path, retry=args.retry
        )
        from slack_mcp.mcp.server import update_slack_client
        from slack_mcp.webhook.server import slack_client

        update_slack_client(token=args.slack_token, client=slack_client)

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
                app = _server_instance.sse_app(mount_path=args.mount_path)
            else:  # streamable-http
                # streamable_http_app doesn't accept mount_path parameter
                app = _server_instance.streamable_http_app()
                if args.mount_path:
                    _LOG.warning("mount-path is not supported for streamable-http transport and will be ignored")

            # Use uvicorn to run the FastAPI app
            uvicorn.run(app, host=args.host, port=args.port)
        else:
            # For stdio transport, use the run method directly
            _LOG.info("Running stdio transport")
            _server_instance.run(transport=args.transport)


if __name__ == "__main__":  # pragma: no cover
    main()
