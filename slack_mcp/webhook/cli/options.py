from __future__ import annotations

import argparse

from .models import WebhookServerCliOptions


def _parse_args(argv: list[str] | None = None) -> WebhookServerCliOptions:
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
    parser.add_argument(
        "--slack-token",
        default=None,
        help="Slack bot token to use (overrides SLACK_BOT_TOKEN environment variable)",
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
        "--integrated",
        action="store_true",
        help="Run the integrated server with both MCP and webhook functionalities",
    )
    parser.add_argument(
        "--mcp-transport",
        choices=["sse", "streamable-http"],
        default="sse",
        help="Transport to use for MCP server when running in integrated mode (default: sse)",
    )
    parser.add_argument(
        "--mcp-mount-path",
        default="/mcp",
        help="Mount path for MCP server when using sse transport (default: /mcp)",
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=3,
        help="Number of retry attempts for network operations (default: 3)",
    )
    args = WebhookServerCliOptions.deserialize(parser.parse_args(argv))
    return args
