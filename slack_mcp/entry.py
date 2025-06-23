"""Command-line entry point to launch the Slack MCP server."""

from __future__ import annotations

import argparse
import logging
import uvicorn
from typing import Final

from .server import mcp as _server_instance

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.entry")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:  # noqa: D401 – helper
    parser = argparse.ArgumentParser(description="Run the Slack MCP server")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
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
        default="stdio",
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:  # noqa: D401 – CLI entry
    args = _parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s [%(levelname)8s] %(message)s")

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
