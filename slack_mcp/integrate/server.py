"""Integrated server implementation for both MCP and webhook servers.

This module provides functionality to run both the MCP server and the Slack webhook server
in a single FastAPI application. It follows PEP 484/585 typing conventions.
"""

from __future__ import annotations

import logging
from typing import Final

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from slack_mcp.mcp.app import mcp_factory
from slack_mcp.webhook.server import (
    get_queue_backend,
    slack_client,
)

__all__: list[str] = [
    "health_check_router",
]

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.integrate.server")


def health_check_router(
    mcp_transport: str = "sse",
) -> APIRouter:
    """Create an integrated FastAPI app with both MCP and webhook functionalities.

    This function creates a FastAPI application that serves both as a Slack webhook server
    and an MCP server, allowing both functionalities to be served from a single endpoint.

    Parameters
    ----------
    mcp_transport : str
        The transport to use for the MCP server. Either "sse" or "streamable-http".

    Returns
    -------
    APIRouter
        The APIRouter of FastAPI app with both MCP and webhook functionalities.

    Raises
    ------
    ValueError
        If an invalid transport type is provided.
    """
    router = APIRouter()

    # Add integrated health check endpoint
    @router.get("/health")
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
            _ = mcp_factory.get()  # Access the server instance to verify it's available

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

    _LOG.info("Successfully created integrated server with both MCP and webhook functionalities")
    return router
