"""Integrated server implementation for both MCP and webhook servers.

This module provides functionality to run both the MCP server and the Slack webhook server
in a single FastAPI application. It follows PEP 484/585 typing conventions.
"""

from __future__ import annotations

import logging
from typing import Final, Optional

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from .mcp.server import mcp as _server_instance
from .webhook.server import (
    create_slack_app,
    get_queue_backend,
    initialize_slack_client,
    slack_client,
)

__all__: list[str] = [
    "create_integrated_app",
]

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.integrated_server")


def create_integrated_app(
    token: Optional[str] = None,
    mcp_transport: str = "sse",
    mcp_mount_path: Optional[str] = "/mcp",
    retry: int = 3,
) -> FastAPI:
    """Create an integrated FastAPI app with both MCP and webhook functionalities.

    This function creates a FastAPI application that serves both as a Slack webhook server
    and an MCP server, allowing both functionalities to be served from a single endpoint.

    Parameters
    ----------
    token : Optional[str]
        The Slack bot token to use. If None, will use environment variables.
    mcp_transport : str
        The transport to use for the MCP server. Either "sse" or "streamable-http".
    mcp_mount_path : Optional[str]
        The path to mount the MCP server on. Only relevant for "sse" transport.
    retry : int
        Number of retry attempts for network operations (default: 3).

    Returns
    -------
    FastAPI
        The FastAPI app with both MCP and webhook functionalities.

    Raises
    ------
    ValueError
        If an invalid transport type is provided.
    """
    # Validate transport type first before any other operations
    if mcp_transport not in ["sse", "streamable-http"]:
        raise ValueError(
            f"Invalid transport type for integrated server: {mcp_transport}. " "Must be 'sse' or 'streamable-http'."
        )

    # Create the webhook app first
    app = create_slack_app()

    # Initialize the global Slack client with the provided token and retry settings
    initialize_slack_client(token, retry=retry)

    # Add integrated health check endpoint
    @app.get("/health")
    async def integrated_health_check() -> JSONResponse:
        """Health check endpoint for the integrated server.

        Returns
        -------
        JSONResponse
            Status information about both MCP and webhook components
        """
        try:
            # Check queue backend functionality
            backend = get_queue_backend()

            # Test if backend is actually functional by attempting a test operation
            try:
                # Try a lightweight test - attempt to publish a health check message
                test_payload = {"type": "health_check", "timestamp": "test"}
                await backend.publish("_health_check", test_payload)
                backend_status = "healthy"
            except Exception as backend_error:
                _LOG.warning(f"Queue backend health check failed: {backend_error}")
                backend_status = f"unhealthy: {str(backend_error)}"

            # Check Slack client status
            slack_status = "not_initialized" if slack_client is None else "initialized"

            # Check MCP server status
            mcp_status = "healthy"  # MCP server is healthy if we can access the instance
            _ = _server_instance  # Access the server instance to verify it's available

            # Determine overall health status
            is_healthy = backend_status == "healthy"
            overall_status = "healthy" if is_healthy else "unhealthy"
            status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

            return JSONResponse(
                status_code=status_code,
                content={
                    "status": overall_status,
                    "service": "integrated-server",
                    "transport": mcp_transport,
                    "components": {
                        "mcp_server": mcp_status,
                        "webhook_server": "healthy",
                        "queue_backend": backend_status,
                        "slack_client": slack_status,
                    },
                },
            )
        except Exception as e:
            _LOG.error(f"Integrated health check failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unhealthy", "service": "integrated-server", "error": str(e)},
            )

    # Get the appropriate MCP app based on the transport
    if mcp_transport == "sse":
        # For SSE transport, we can mount at a specified path
        mcp_app = _server_instance.sse_app(mount_path=mcp_mount_path)

        # Mount the MCP app on the webhook app
        _LOG.info(f"Mounting MCP server with SSE transport at path: {mcp_mount_path}")
        app.mount(mcp_mount_path or "/mcp", mcp_app)
    elif mcp_transport == "streamable-http":
        # For streamable-http transport, get the app
        mcp_app = _server_instance.streamable_http_app()

        # The streamable-http app doesn't use a mount_path so we mount it at root level
        # but on a different route pattern than the webhook endpoints
        _LOG.info("Integrating MCP server with streamable-http transport")

        # Get all routes from the MCP app and add them to the main app
        for route in mcp_app.routes:
            app.routes.append(route)

    _LOG.info("Successfully created integrated server with both MCP and webhook functionalities")
    return app
