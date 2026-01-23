"""FastAPI web server factory for Slack webhook integration.

This module provides a FastAPI web server factory that creates and manages
the webhook server instance. The webhook server handles Slack events and
can optionally mount the MCP server for integrated functionality.

Module Overview
===============
The WebServerFactory is responsible for:
- Creating and managing the FastAPI webhook server instance
- Configuring CORS middleware for cross-origin requests
- Managing the server lifecycle
- Ensuring singleton pattern enforcement

Usage Examples
==============

**1. Create and get webhook server instance:**

    .. code-block:: python

        from slack_mcp.webhook.app import web_factory

        # Get the default instance (already created)
        web_server = web_factory.get()

        # Add custom routes
        @web_server.get("/custom")
        async def custom_endpoint():
            return {"message": "Hello"}

**2. Run the webhook server:**

    .. code-block:: python

        import uvicorn
        from slack_mcp.webhook.app import web_factory

        web_server = web_factory.get()
        uvicorn.run(web_server, host="0.0.0.0", port=3000)

**3. Using curl to test endpoints:**

    .. code-block:: bash

        # Health check
        curl http://localhost:3000/health

        # Slack events endpoint
        curl -X POST http://localhost:3000/slack/events \\
             -H "Content-Type: application/json" \\
             -H "X-Slack-Request-Timestamp: ..." \\
             -H "X-Slack-Signature: ..." \\
             -d '{"type":"url_verification","challenge":"..."}'

**4. Using Python to interact with the server:**

    .. code-block:: python

        import asyncio
        from slack_mcp.webhook.entry import run_slack_server

        asyncio.run(run_slack_server(host="0.0.0.0", port=3000))

**5. Using wget to check server health:**

    .. code-block:: bash

        wget -q -O- http://localhost:3000/health | jq .

Server Features
===============
- **CORS Support**: Configured to accept requests from any origin
- **Slack Integration**: Handles Slack webhook events
- **Health Checks**: Built-in health check endpoint
- **Event Publishing**: Publishes events to message queue backends
- **MCP Integration**: Can optionally mount MCP server
"""

from __future__ import annotations

import logging
from typing import Final, Optional, Type

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slack_mcp._base import BaseServerFactory
from slack_mcp.mcp.app import mcp_factory

_LOG: Final[logging.Logger] = logging.getLogger(__name__)

_WEB_SERVER_INSTANCE: Optional[FastAPI] = None


class WebServerFactory(BaseServerFactory[FastAPI]):
    """Factory for creating and managing FastAPI webhook server instances.

    This factory implements the singleton pattern to ensure only one webhook server
    instance exists per application. It provides methods for creating, accessing,
    and resetting the server instance.

    The webhook server is configured with:
    - CORS middleware for cross-origin requests
    - MCP server lifespan management
    - Slack event handling endpoints
    - Health check endpoints

    Examples
    --------
    **Create the webhook server:**

    .. code-block:: python

        from slack_mcp.webhook.app import web_factory

        # Create the server (usually done at module import)
        web_server = web_factory.create()

    **Get the existing server:**

    .. code-block:: python

        web_server = web_factory.get()

    **Run the server:**

    .. code-block:: python

        import uvicorn
        web_server = web_factory.get()
        uvicorn.run(web_server, host="0.0.0.0", port=3000)
    """

    @staticmethod
    def create(**kwargs) -> FastAPI:
        """Create and configure the webhook server.

        Creates a new FastAPI instance configured for Slack webhook integration.
        This method enforces the singleton pattern - only one instance can be
        created per application lifecycle.

        The server is configured with:
        - Title: "Slack MCP Server"
        - CORS middleware (allows all origins)
        - MCP server lifespan management
        - Slack event handling

        Parameters
        ----------
        **kwargs : dict
            Additional arguments (unused, but included for base class compatibility)

        Returns
        -------
        FastAPI
            Configured FastAPI webhook server instance

        Raises
        ------
        AssertionError
            If an instance has already been created

        Examples
        --------
        .. code-block:: python

            from slack_mcp.webhook.app import web_factory

            web_server = web_factory.create()
            print(web_server.title)  # "Slack MCP Server"

        Notes
        -----
        - CORS is configured to allow requests from any origin
        - In production, consider restricting CORS origins
        - The server includes the MCP server lifespan for proper initialization
        """
        # Create a new FastAPI instance
        global _WEB_SERVER_INSTANCE
        assert _WEB_SERVER_INSTANCE is None, "It is not allowed to create more than one instance of web server."
        # Create FastAPI app
        _WEB_SERVER_INSTANCE = FastAPI(
            title="Slack MCP Server",
            description="A FastAPI web server that hosts a Slack MCP server for interacting with Slack API",
            version="0.1.0",
            lifespan=mcp_factory.lifespan(),
        )

        # Configure CORS
        from slack_mcp.settings import get_settings

        settings = get_settings()

        # Parse comma-separated strings into lists
        origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]
        methods = [method.strip() for method in settings.cors_allow_methods.split(",") if method.strip()]
        headers = [header.strip() for header in settings.cors_allow_headers.split(",") if header.strip()]

        _WEB_SERVER_INSTANCE.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=methods,
            allow_headers=headers,
        )
        return _WEB_SERVER_INSTANCE

    @staticmethod
    def get() -> FastAPI:
        """Get the webhook server instance.

        Retrieves the singleton FastAPI instance. The instance must have been
        created previously using the create() method.

        Returns
        -------
        FastAPI
            The configured FastAPI webhook server instance

        Raises
        ------
        AssertionError
            If the server instance has not been created yet

        Examples
        --------
        .. code-block:: python

            from slack_mcp.webhook.app import web_factory

            web_server = web_factory.get()

            # Add custom routes
            @web_server.get("/custom")
            async def custom_endpoint():
                return {"message": "Hello"}
        """
        assert _WEB_SERVER_INSTANCE is not None, "It must be created web server first."
        return _WEB_SERVER_INSTANCE

    @staticmethod
    def reset() -> None:
        """Reset the singleton instance (for testing purposes).

        Clears the global webhook server instance, allowing a new one to be created.
        This is primarily used in test suites to ensure clean state between tests.

        Returns
        -------
        None

        Examples
        --------
        .. code-block:: python

            from slack_mcp.webhook.app import web_factory

            # In test setup
            web_factory.reset()
            web_server = web_factory.create()

            # ... run tests ...

            # In test teardown
            web_factory.reset()
        """
        global _WEB_SERVER_INSTANCE
        _WEB_SERVER_INSTANCE = None


web_factory: Final[Type[WebServerFactory]] = WebServerFactory
web: Final[FastAPI] = web_factory.create()
