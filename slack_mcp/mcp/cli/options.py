"""Command-line of Slack MCP server."""

from __future__ import annotations

import argparse

from .models import MCPServerCliOptions


def _parse_args(argv: list[str] | None = None) -> MCPServerCliOptions:  # noqa: D401 – helper
    parser = argparse.ArgumentParser(description="Run the Slack MCP server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to when using HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to when using HTTP transport (default: 8000)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="sse",
        help="Transport to use for MCP server (default: stdio)",
    )
    parser.add_argument(
        "--mount-path",
        default=None,
        help="Mount path for HTTP transports (unused for streamable-http transport)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level (e.g., DEBUG, INFO)",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file (default: .env in current directory)",
    )
    parser.add_argument(
        "--no-env-file",
        action="store_true",
        help="Disable loading from .env file",
    )
    parser.add_argument(
        "--slack-token",
        default=None,
        help="Slack bot token (overrides SLACK_BOT_TOKEN environment variable)",
    )
    parser.add_argument(
        "--integrated",
        action="store_true",
        help="Run MCP server integrated with webhook server in a single FastAPI application",
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=3,
        help="Number of retry attempts for network operations (default: 3)",
    )
    return MCPServerCliOptions.deserialize(parser.parse_args(argv))
