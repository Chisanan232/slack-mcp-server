"""Command-line entry point to launch the Slack MCP server."""

import logging
import os
import pathlib
from typing import Final, Optional

import uvicorn
from dotenv import load_dotenv

from slack_mcp.integrate.app import integrated_factory
from slack_mcp.logging.config import setup_logging_from_args

from .app import mcp_factory
from .cli import _parse_args
from .server import set_slack_client_retry_count

_LOG: Final[logging.Logger] = logging.getLogger(__name__)


def main(argv: Optional[list[str]] = None) -> None:  # noqa: D401 – CLI entry
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

    # Determine if we should run the integrated server
    if args.integrated:
        if args.transport == "stdio":
            _LOG.error("Integrated mode is not supported with stdio transport")
            return

        _LOG.info(f"Starting integrated Slack server (MCP + Webhook) on {args.host}:{args.port}")

        # Get effective token (CLI argument or environment variable)
        effective_token = args.slack_token or os.environ.get("SLACK_BOT_TOKEN")

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
