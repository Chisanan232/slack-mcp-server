"""Integrated FastAPI app factory for Slack MCP + Webhook server.

This module creates a FastAPI application that integrates both the MCP server
and the Slack webhook server into a single process. It mounts transport-specific
MCP apps and exposes a health check router.

Highlights
==========
- Integrated mode runs both MCP and webhook servers together
- Supports SSE and streamable-HTTP transports for MCP
- Uses centralized Slack client initialization with configurable retries
- Includes a health check router for operational monitoring

Quick Start
===========

.. code-block:: python

    from slack_mcp.integrate.app import IntegratedServerFactory

    # Create app (SSE transport, mounted at /mcp)
    app = IntegratedServerFactory.create(mcp_transport="sse", mcp_mount_path="/mcp", retry=3)

    # Or create with streamable-HTTP transport
    app = IntegratedServerFactory.create(mcp_transport="streamable-http", retry=3)

Notes
=====
- When retry > 0, Slack SDK retry handlers are enabled for rate limits, server
  errors, and connection issues.
- Token can be deferred at creation time and initialized later by the entrypoint
  (useful for CLI-driven configuration).
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
    """Factory for building the integrated Slack MCP + webhook FastAPI app.

    Responsibilities
    ----------------
    - Create a FastAPI app with Slack webhook routes
    - Initialize Slack client lazily with optional retries
    - Mount MCP sub-app depending on transport (SSE or streamable-HTTP)
    - Include health check routes

    Examples
    --------
    .. code-block:: python

        from slack_mcp.integrate.app import IntegratedServerFactory

        # Create default integrated app (SSE transport)
        app = IntegratedServerFactory.create(mcp_transport="sse", mcp_mount_path="/mcp")

        # Access the instance later
        app2 = IntegratedServerFactory.get()
    """
    @staticmethod
    def create(**kwargs) -> FastAPI:
        """Create and configure the integrated FastAPI server.

        Parameters
        ----------
        **kwargs
            token : Optional[str]
                Slack bot token to initialize the global Slack client. If None,
                initialization is deferred until the entrypoint provides it.
            mcp_transport : str
                Transport for MCP server. One of "sse" or "streamable-http".
            mcp_mount_path : str
                Mount path for MCP sub-app (only applicable to SSE transport).
            retry : int
                Retry count for Slack client operations (0 disables retries).

        Returns
        -------
        FastAPI
            Configured FastAPI server instance that serves both webhook and MCP features.

        Raises
        ------
        ValueError
            If an invalid MCP transport is provided.

        Examples
        --------
        .. code-block:: python

            app = IntegratedServerFactory.create(
                token=None,
                mcp_transport="sse",
                mcp_mount_path="/mcp",
                retry=3,
            )
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
        """Prepare Slack client initialization.

        Initializes the global Slack client if a token is provided. If not,
        defers initialization until later (e.g., in the CLI entry).

        Parameters
        ----------
        token : Optional[str]
            Slack bot token. If None, initialization is deferred.
        retry : int
            Retry count for Slack client operations (0 disables retries).
        """
        if token:
            initialize_slack_client(token, retry=retry)
        else:
            _LOG.info("Deferring Slack client initialization - token will be set later")

    @classmethod
    def _mount(cls, mcp_transport: str = "sse", mcp_mount_path: str = "/mcp") -> None:
        """Mount health and MCP routes into the integrated app.

        Parameters
        ----------
        mcp_transport : str
            MCP transport ("sse" or "streamable-http").
        mcp_mount_path : str
            Base mount path for MCP sub-app (for SSE transport).
        """
        IntegratedServerFactory.get().include_router(health_check_router(mcp_transport=mcp_transport))

        # Get and mount the appropriate MCP app based on the transport
        IntegratedServerFactory._mount_mcp_service(transport=mcp_transport, mount_path=mcp_mount_path)

    @classmethod
    def _mount_mcp_service(
        cls, transport: str = MCPTransportType.SSE, mount_path: str = "", sse_mount_path: str | None = None
    ) -> None:
        """Mount an MCP sub-application into the integrated FastAPI app.

        This centralizes mounting logic for both supported MCP transports.

        Parameters
        ----------
        transport : str
            MCP transport protocol. "sse" or "streamable-http".
        mount_path : str
            Path where the MCP service should be mounted. If empty, defaults to "/mcp".
        sse_mount_path : str | None
            Path passed to the SSE sub-app for its internal routes. Only used for SSE.

        Raises
        ------
        ValueError
            If an unknown transport is provided.

        Notes
        -----
        - SSE: Creates `mcp_factory.get().sse_app(mount_path=sse_mount_path)` and mounts at `mount_path or "/mcp"`.
        - Streamable-HTTP: Creates `mcp_factory.get().streamable_http_app()` and mounts at `mount_path or "/mcp"`.
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
