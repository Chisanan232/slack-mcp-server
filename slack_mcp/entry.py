"""Command-line entry point to launch the Slack MCP server."""

from __future__ import annotations

import argparse
import logging
from typing import Final

from .server import mcp as _server_instance

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.entry")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:  # noqa: D401 – helper
    parser = argparse.ArgumentParser(description="Run the Slack MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport mode for FastMCP server (default: stdio)",
    )
    parser.add_argument(
        "--mount-path",
        default=None,
        help="Mount path for HTTP transports (unused for stdio)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level (e.g., DEBUG, INFO)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:  # noqa: D401 – CLI entry
    args = _parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s [%(levelname)8s] %(message)s")

    _LOG.info("Starting Slack MCP server: transport=%s", args.transport)
    _server_instance.run(transport=args.transport, mount_path=args.mount_path)


if __name__ == "__main__":  # pragma: no cover
    main()
