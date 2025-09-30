"""Integrated server implementation for both MCP and webhook servers.

This module provides functionality to run both the MCP server and the Slack webhook server
in a single FastAPI application. It follows PEP 484/585 typing conventions.
"""

from __future__ import annotations

import contextlib
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

    # For streamable-http transport, we need to create a new FastAPI app with proper lifespan
    # For SSE transport, we can use the existing webhook app structure
    if mcp_transport == "streamable-http":
        # Create lifespan context manager for streamable-http transport
        @contextlib.asynccontextmanager
        async def lifespan_streamable_http(_: FastAPI):
            """Lifespan context manager for streamable-http transport."""
            async with _server_instance.session_manager.run():
                yield
        
        # Create a new FastAPI app with lifespan for streamable-http
        app = FastAPI(
            title="Slack MCP Integrated Server",
            description="Integrated Slack webhook and MCP server",
            version="1.0.0",
            lifespan=lifespan_streamable_http,
            redirect_slashes=False,
        )
        
        # Add webhook routes manually to the new app for streamable-http
        # We need to replicate the webhook functionality from create_slack_app()
        
        # Initialize the queue backend
        backend = get_queue_backend()
        
        # Get the topic for Slack events from environment or use default  
        import os
        DEFAULT_SLACK_EVENTS_TOPIC = "slack_events"
        slack_events_topic = os.environ.get("SLACK_EVENTS_TOPIC", DEFAULT_SLACK_EVENTS_TOPIC)
        
        @app.post("/slack/events")
        async def slack_events(request) -> JSONResponse:
            """Handle Slack events for streamable-http integrated server."""
            from fastapi import HTTPException, Request, Response
            import json
            from .webhook.server import verify_slack_request
            from .webhook.models import SlackEventModel, UrlVerificationModel, deserialize
            
            # Verify the request is from Slack
            if not await verify_slack_request(request):
                _LOG.warning("Invalid Slack request signature")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid request signature")

            # Get request body as text
            body = await request.body()
            body_str = body.decode("utf-8")

            # Parse the request body
            slack_event_dict = json.loads(body_str)

            # Use Pydantic model for deserialization
            try:
                slack_event_model = deserialize(slack_event_dict)
            except Exception as e:
                _LOG.error(f"Error deserializing Slack event: {e}")
                slack_event_model = None

            # Handle URL verification challenge
            if isinstance(slack_event_model, UrlVerificationModel):
                _LOG.info("Handling URL verification challenge")
                return JSONResponse(content={"challenge": slack_event_model.challenge})
            elif "challenge" in slack_event_dict:
                _LOG.info("Handling URL verification challenge (fallback)")
                return JSONResponse(content={"challenge": slack_event_dict["challenge"]})

            # Process the event
            if isinstance(slack_event_model, SlackEventModel):
                event_type = slack_event_model.event.type if hasattr(slack_event_model.event, "type") else "unknown"
                _LOG.info(f"Received Slack event: {event_type}")
                event_dict = slack_event_model.model_dump()
                try:
                    await backend.publish(slack_events_topic, event_dict)
                    _LOG.info(f"Published event of type '{event_type}' to queue topic '{slack_events_topic}'")
                except Exception as e:
                    _LOG.error(f"Error publishing event to queue: {e}")
            else:
                event_type = slack_event_dict.get("event", {}).get("type", "unknown")
                _LOG.info(f"Received Slack event: {event_type}")
                try:
                    await backend.publish(slack_events_topic, slack_event_dict)
                    _LOG.info(f"Published event of type '{event_type}' to queue topic '{slack_events_topic}'")
                except Exception as e:
                    _LOG.error(f"Error publishing event to queue: {e}")

            return JSONResponse(content={"status": "ok"})
    else:
        # For SSE transport, use the existing webhook app structure
        app = create_slack_app()

    # Initialize the global Slack client with the provided token and retry settings
    # Allow token to be None during app creation - it will be set later in entry.py
    if token:
        initialize_slack_client(token, retry=retry)
    else:
        _LOG.info("Deferring Slack client initialization - token will be set later")

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
                    "service": "slack-webhook-server",
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
                content={"status": "unhealthy", "service": "slack-webhook-server", "error": str(e)},
            )

    # Get the appropriate MCP app based on the transport
    if mcp_transport == "sse":
        # For SSE transport, we can mount at a specified path
        mcp_app = _server_instance.sse_app(mount_path=mcp_mount_path)

        # Mount the MCP app on the webhook app
        _LOG.info(f"Mounting MCP server with SSE transport at path: {mcp_mount_path}")
        app.mount(mcp_mount_path or "/mcp", mcp_app)
    elif mcp_transport == "streamable-http":
        # For streamable-http transport, investigate and add MCP routes
        mcp_app = _server_instance.streamable_http_app()
        mount_path = mcp_mount_path or "/mcp"

        # Mount streamable-HTTP app at root level since it already has /mcp path
        _LOG.info(f"Integrating MCP server with streamable-http transport")
        app.mount(mount_path, mcp_app)

    _LOG.info("Successfully created integrated server with both MCP and webhook functionalities")
    return app
