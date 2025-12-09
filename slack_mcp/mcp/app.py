"""MCP server factory for creating and managing FastMCP instances.

This module provides a factory pattern implementation for creating and managing
the FastMCP server instance. It handles singleton pattern enforcement and
provides methods for accessing different transport implementations.

Module Overview
===============
The MCPServerFactory is responsible for:
- Creating and managing the FastMCP server instance
- Providing access to different transport implementations (SSE, streamable-http, stdio)
- Managing the server lifecycle and session management
- Ensuring singleton pattern enforcement

Usage Examples
==============

**1. Create and get MCP server instance:**

    .. code-block:: python

        from slack_mcp.mcp.app import mcp_factory

        # Get the default instance (already created)
        mcp_server = mcp_factory.get()

        # Register a custom tool
        @mcp_server.tool("my_tool")
        async def my_tool(param: str) -> dict:
            return {"result": param}

**2. Get SSE app for HTTP transport:**

    .. code-block:: python

        from slack_mcp.mcp.app import mcp_factory

        mcp_server = mcp_factory.get()
        sse_app = mcp_server.sse_app(mount_path="/mcp")

        # Use with FastAPI
        from fastapi import FastAPI
        app = FastAPI()
        app.mount("/mcp", sse_app)

**3. Get streamable-http app:**

    .. code-block:: python

        mcp_server = mcp_factory.get()
        http_app = mcp_server.streamable_http_app()

        # Use with FastAPI
        app = FastAPI()
        app.mount("/mcp", http_app)

**4. Run stdio transport:**

    .. code-block:: python

        mcp_server = mcp_factory.get()
        mcp_server.run(transport="stdio")

**5. Using curl to test HTTP endpoints:**

    .. code-block:: bash

        # Test SSE transport
        curl http://localhost:8000/mcp/sse

        # Test streamable-http transport
        curl http://localhost:8000/mcp/

**6. Using Python to interact with MCP tools:**

    .. code-block:: python

        import asyncio
        from slack_mcp.mcp.server import send_slack_message
        from slack_mcp.mcp.model.input import SlackPostMessageInput

        async def main():
            input_params = SlackPostMessageInput(
                channel="C12345678",
                text="Hello from MCP!"
            )
            response = await send_slack_message(input_params)
            print(response)

        asyncio.run(main())

Transport Types
===============
- **stdio**: Standard input/output for local MCP clients
- **sse**: Server-Sent Events for HTTP-based clients
- **streamable-http**: Streamable HTTP transport for HTTP-based clients
"""

import contextlib
from collections.abc import Callable
from typing import Final, Type

from fastapi import FastAPI
from mcp.server import FastMCP

from slack_mcp._base import BaseServerFactory

SERVER_NAME: Final[str] = "SlackMCPServer"

_MCP_SERVER_INSTANCE: FastMCP | None = None


class MCPServerFactory(BaseServerFactory[FastMCP]):
    """Factory for creating and managing FastMCP server instances.

    This factory implements the singleton pattern to ensure only one MCP server
    instance exists per application. It provides methods for creating, accessing,
    and resetting the server instance.

    Examples
    --------
    **Create the MCP server:**

    .. code-block:: python

        from slack_mcp.mcp.app import mcp_factory

        # Create the server (usually done at module import)
        mcp_server = mcp_factory.create()

    **Get the existing server:**

    .. code-block:: python

        mcp_server = mcp_factory.get()

    **Reset for testing:**

    .. code-block:: python

        mcp_factory.reset()
        mcp_server = mcp_factory.create()
    """

    @staticmethod
    def create(**kwargs) -> FastMCP:
        """Create and configure the MCP server.

        Creates a new FastMCP instance with the server name "SlackMCPServer".
        This method enforces the singleton pattern - only one instance can be
        created per application lifecycle.

        Parameters
        ----------
        **kwargs : dict
            Additional arguments (unused, but included for base class compatibility)

        Returns
        -------
        FastMCP
            Configured FastMCP server instance

        Raises
        ------
        AssertionError
            If an instance has already been created

        Examples
        --------
        .. code-block:: python

            from slack_mcp.mcp.app import mcp_factory

            mcp_server = mcp_factory.create()
            print(mcp_server.name)  # "SlackMCPServer"
        """
        # Create a new FastMCP instance
        global _MCP_SERVER_INSTANCE
        assert _MCP_SERVER_INSTANCE is None, "It is not allowed to create more than one instance of FastMCP."
        _MCP_SERVER_INSTANCE = FastMCP(name=SERVER_NAME)
        return _MCP_SERVER_INSTANCE

    @staticmethod
    def get() -> FastMCP:
        """Get the MCP server instance.

        Retrieves the singleton FastMCP instance. The instance must have been
        created previously using the create() method.

        Returns
        -------
        FastMCP
            The configured FastMCP server instance

        Raises
        ------
        AssertionError
            If the server instance has not been created yet

        Examples
        --------
        .. code-block:: python

            from slack_mcp.mcp.app import mcp_factory

            mcp_server = mcp_factory.get()

            # Register a tool
            @mcp_server.tool("my_tool")
            async def my_tool(param: str) -> dict:
                return {"result": param}
        """
        assert _MCP_SERVER_INSTANCE is not None, "It must be created FastMCP first."
        return _MCP_SERVER_INSTANCE

    @staticmethod
    def reset() -> None:
        """Reset the singleton instance (for testing purposes).

        Clears the global MCP server instance, allowing a new one to be created.
        This is primarily used in test suites to ensure clean state between tests.

        Returns
        -------
        None

        Examples
        --------
        .. code-block:: python

            from slack_mcp.mcp.app import mcp_factory

            # In test setup
            mcp_factory.reset()
            mcp_server = mcp_factory.create()

            # ... run tests ...

            # In test teardown
            mcp_factory.reset()
        """
        global _MCP_SERVER_INSTANCE
        _MCP_SERVER_INSTANCE = None

    @staticmethod
    def lifespan() -> Callable[..., contextlib._AsyncGeneratorContextManager]:
        """Get the lifespan context manager for FastAPI integration.

        This method returns an async context manager that handles the lifecycle
        of the MCP server when integrated with FastAPI. It initializes the
        transport apps and manages the session manager.

        Returns
        -------
        Callable
            An async context manager function for FastAPI lifespan

        Raises
        ------
        AssertionError
            If the MCP server instance has not been created

        Notes
        -----
        This is typically used when creating a FastAPI app with MCP integration:

        .. code-block:: python

            from fastapi import FastAPI
            from slack_mcp.mcp.app import mcp_factory

            mcp_factory.create()
            app = FastAPI(lifespan=mcp_factory.lifespan())
        """
        try:
            _mcp_server = MCPServerFactory.get()
        except AssertionError:
            raise AssertionError("Please create a FastMCP instance first by calling *MCPServerFactory.create()*.")

        @contextlib.asynccontextmanager
        async def lifespan(_: FastAPI):
            # Initialize transport apps before accessing session_manager
            # This ensures the session manager is properly created
            _mcp_server.sse_app()
            _mcp_server.streamable_http_app()

            # Now we can safely access session_manager
            async with _mcp_server.session_manager.run():
                yield  # FastAPI would start to handle requests after yield

        return lifespan


# Create a default MCP server instance for backward compatibility
mcp_factory: Final[Type[MCPServerFactory]] = MCPServerFactory
mcp: Final[FastMCP] = mcp_factory.create()
