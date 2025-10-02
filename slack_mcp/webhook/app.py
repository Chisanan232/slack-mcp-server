"""
FastAPI Web Server for ClickUp MCP.

This module provides a FastAPI web server that mounts the MCP server
for exposing ClickUp functionality through a RESTful API.
"""

from __future__ import annotations

import logging
from typing import Optional, Final, Type

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slack_mcp._base import BaseServerFactory
# from slack_mcp.client import ClickUpAPIClientFactory, get_api_token
from slack_mcp.mcp.app import mcp_factory
from slack_mcp.mcp.cli.models import MCPTransportType
# from slack_mcp.models.cli import MCPTransportType, ServerConfig
# from slack_mcp.models.dto.health_check import HealthyCheckResponseDto
# from slack_mcp.utils import load_environment_from_file

_LOG: Final[logging.Logger] = logging.getLogger(__name__)

_WEB_SERVER_INSTANCE: Optional[FastAPI] = None


class WebServerFactory(BaseServerFactory[FastAPI]):
    @staticmethod
    def create(**kwargs) -> FastAPI:
        """
        Create and configure the web API server.

        Args:
            **kwargs: Additional arguments (unused, but included for base class compatibility)

        Returns:
            Configured FastAPI server instance
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
        _WEB_SERVER_INSTANCE.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, replace with specific origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        return _WEB_SERVER_INSTANCE

    @staticmethod
    def get() -> FastAPI:
        """
        Get the web API server instance

        Returns:
            Configured FastAPI server instance
        """
        assert _WEB_SERVER_INSTANCE is not None, "It must be created web server first."
        return _WEB_SERVER_INSTANCE

    @staticmethod
    def reset() -> None:
        """
        Reset the singleton instance (for testing purposes).
        """
        global _WEB_SERVER_INSTANCE
        _WEB_SERVER_INSTANCE = None


web_factory: Final[Type[WebServerFactory]] = WebServerFactory
web: Final[FastAPI] = web_factory.create()


def mount_service(transport: str = MCPTransportType.SSE, mount_path: str = "", sse_mount_path: str = "") -> None:
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
            web_factory.get().mount(path=mount_path or "/mcp", app=mcp_factory.get().sse_app(mount_path=sse_mount_path))
        case MCPTransportType.STREAMABLE_HTTP:
            web_factory.get().mount(path=mount_path or "/mcp", app=mcp_factory.get().streamable_http_app())
            _LOG.info(f"Integrating MCP server with streamable-http transport")
        case _:
            raise ValueError(f"Unknown transport protocol: {transport}")


# def create_app(
#     server_config: ServerConfig | None = None,
# ) -> FastAPI:
#     """
#     Create and configure the FastAPI application with MCP server mounted.
#
#     Args:
#         server_config: Optional server configuration.
#
#     Returns:
#         Configured FastAPI application
#     """
#     # Load environment variables from file if provided
#     load_environment_from_file(server_config.env_file if server_config else None)
#
#     # Create client with the token from configuration or environment
#     ClickUpAPIClientFactory.create(api_token=get_api_token(server_config))
#
#     # Use default server type if no configuration is provided
#     transport = server_config.transport if server_config else MCPTransportType.SSE
#
#     # Mount MCP routes
#     mount_service(transport=transport)
#
#     # Root endpoint for health checks
#     @web.get("/health", response_class=JSONResponse)
#     async def root() -> HealthyCheckResponseDto:
#         """
#         Root endpoint providing basic health check.
#
#         Returns:
#             JSON response with server status
#         """
#         return HealthyCheckResponseDto()
#
#     return web
