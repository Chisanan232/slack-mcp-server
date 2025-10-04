"""
FastAPI Web Server for ClickUp MCP.

This module provides a FastAPI web server that mounts the MCP server
for exposing ClickUp functionality through a RESTful API.
"""

from __future__ import annotations

import logging
from typing import Final, Optional, Type

from fastapi import FastAPI

from slack_mcp._base import BaseServerFactory
from slack_mcp.mcp.app import mcp_factory
from slack_mcp.mcp.cli.models import MCPTransportType
from slack_mcp.webhook.app import web_factory
from slack_mcp.webhook.server import (
    create_slack_app,
    initialize_slack_client,
)

from .server import health_check_router

_LOG: Final[logging.Logger] = logging.getLogger(__name__)

_INTEGRATED_SERVER_INSTANCE: Optional[FastAPI] = None


class IntegratedServerFactory(BaseServerFactory[FastAPI]):
    @staticmethod
    def create(**kwargs) -> FastAPI:
        """
        Create and configure the web API server.

        Args:
            **kwargs: Additional arguments (unused, but included for base class compatibility)

        Returns:
            Configured FastAPI server instance
        """
        token: Optional[str] = kwargs.get("token", None)
        mcp_transport: str = kwargs.get("mcp_transport", "sse")
        mcp_mount_path: str = kwargs.get("mcp_mount_path", "/mcp")
        retry: int = kwargs.get("retry", 3)

        # Validate transport type first before any other operations
        if mcp_transport not in ["sse", "streamable-http"]:
            raise ValueError(
                f"Invalid transport type for integrated server: {mcp_transport}. " "Must be 'sse' or 'streamable-http'."
            )

        # Create the webhook app first - this will be returned for both transports
        # Initialize web factory and MCP factory before creating the app
        from slack_mcp.mcp.app import mcp_factory
        from slack_mcp.webhook.app import web_factory

        # Only create factories if they don't exist yet (avoid re-creation during tests)
        try:
            mcp_factory.get()
        except AssertionError:
            mcp_factory.create()

        try:
            web_factory.get()
        except AssertionError:
            web_factory.create()

        global _INTEGRATED_SERVER_INSTANCE
        _INTEGRATED_SERVER_INSTANCE = create_slack_app()

        IntegratedServerFactory._prepare(token=token, retry=retry)

        # mount the necessary routers
        IntegratedServerFactory._mount(mcp_transport=mcp_transport, mcp_mount_path=mcp_mount_path)

        _LOG.info("Successfully created integrated server with both MCP and webhook functionalities")
        return _INTEGRATED_SERVER_INSTANCE

    @classmethod
    def _prepare(cls, token: Optional[str] = None, retry: int = 3) -> None:
        # Initialize the global Slack client with the provided token and retry settings
        # Allow token to be None during app creation - it will be set later in entry.py
        if token:
            initialize_slack_client(token, retry=retry)
        else:
            _LOG.info("Deferring Slack client initialization - token will be set later")

    @classmethod
    def _mount(cls, mcp_transport: str = "sse", mcp_mount_path: str = "/mcp") -> None:
        # mount the health check router
        IntegratedServerFactory.get().include_router(health_check_router(mcp_transport=mcp_transport))

        # Get and mount the appropriate MCP app based on the transport
        IntegratedServerFactory._mount_mcp_service(transport=mcp_transport, mount_path=mcp_mount_path)

    @classmethod
    def _mount_mcp_service(
        cls, transport: str = MCPTransportType.SSE, mount_path: str = "", sse_mount_path: str | None = None
    ) -> None:
        """
        Mount an MCP (Model Context Protocol) service into the web server.

        This function provides a centralized way to mount MCP services with different transport
        protocols into the FastAPI web application. It handles both SSE (Server-Sent Events)
        and streamable HTTP transports, automatically creating the appropriate MCP app and
        mounting it at the specified path.

        Args:
            transport: The transport protocol to use for MCP. Must be either
                MCPTransportType.SSE ("sse") or MCPTransportType.STREAMABLE_HTTP ("streamable-http").
                Defaults to MCPTransportType.SSE.
            mount_path: The path where the MCP service should be mounted in the web server.
                If empty string, defaults to "/mcp" for both transport types.
            sse_mount_path: The mount path parameter to pass to the SSE app creation.
                Only used for SSE transport. Can be empty string or None.

        Raises:
            ValueError: If an unknown transport protocol is provided.

        Note:
            - For SSE transport: Creates an SSE app with the specified sse_mount_path and mounts it
            - For streamable-HTTP transport: Creates a streamable HTTP app and mounts it
            - Both transport types default to mounting at "/mcp" if mount_path is not specified
        """
        match transport:
            case MCPTransportType.SSE:
                _LOG.info(f"Mounting MCP server with SSE transport at path: {sse_mount_path}")
                web_factory.get().mount(
                    path=mount_path or "/mcp", app=mcp_factory.get().sse_app(mount_path=sse_mount_path)
                )
            case MCPTransportType.STREAMABLE_HTTP:
                # Mount streamable-HTTP at /mcp path to avoid conflicts with webhook routes
                # The streamable-HTTP app has internal /mcp routes, so it will be accessible at /mcp/mcp
                web_factory.get().mount(path=mount_path or "/mcp", app=mcp_factory.get().streamable_http_app())
                _LOG.info("Integrating MCP server with streamable-http transport")
            case _:
                raise ValueError(f"Unknown transport protocol: {transport}")

    @staticmethod
    def get() -> FastAPI:
        """
        Get the web API server instance

        Returns:
            Configured FastAPI server instance
        """
        assert _INTEGRATED_SERVER_INSTANCE is not None, "It must be created web server first."
        return _INTEGRATED_SERVER_INSTANCE

    @staticmethod
    def reset() -> None:
        """
        Reset the singleton instance (for testing purposes).
        """
        global _INTEGRATED_SERVER_INSTANCE
        _INTEGRATED_SERVER_INSTANCE = None


integrated_factory: Final[Type[IntegratedServerFactory]] = IntegratedServerFactory

# IMPORTANT: DO NOT CREATE MODULE-LEVEL integrated_app INSTANCE HERE
#
# Previous implementation had:
#   integrated_app: FastAPI = IntegratedServerFactory.create()
#
# This was removed to fix critical E2E test failures in streamable-HTTP integrated mode.
#
# ROOT CAUSES FOR REMOVAL:
# 1. **Singleton Conflicts**: Module-level instance creation caused route duplication
#    when multiple test cases or applications tried to create integrated server instances
#
# 2. **Route Mounting Issues**: Streamable-HTTP transport uses different integration
#    approach than SSE, and automatic instance creation caused conflicts between:
#    - MCP routes (mounted at /mcp)
#    - Webhook routes (at /slack/*)
#    - Health check routes (at /health)
#
# 3. **Test Environment Issues**: E2E tests require clean server instances per test,
#    but module-level creation prevented proper test isolation
#
# CURRENT ARCHITECTURE (DO NOT CHANGE):
# - Outside code must explicitly call IntegratedServerFactory.create()
# - Each call creates a fresh instance (no singleton pattern at module level)
# - Tests can properly reset and recreate instances via IntegratedServerFactory.reset()
# - Prevents route conflicts between SSE and streamable-HTTP transports
#
# REFERENCE: See test fixes in test/e2e_test/mcp/test_streamable_http_integrated_e2e.py
# If you need an integrated_app instance, create it explicitly in your code:
#   from slack_mcp.integrate.app import IntegratedServerFactory
#   app = IntegratedServerFactory.create(mcp_transport="sse")  # or "streamable-http"
