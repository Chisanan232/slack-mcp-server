"""Slack app implementation for handling Slack events.

This module defines a FastAPI application that serves as an endpoint for Slack events API.
It follows PEP 484/585 typing conventions.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Final, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from slack_sdk.signature import SignatureVerifier
from slack_sdk.web.async_client import AsyncWebClient

from slack_mcp.backends.base.protocol import QueueBackend
from slack_mcp.backends.loader import load_backend
from slack_mcp.client.manager import get_client_manager

from .models import SlackEventModel, UrlVerificationModel, deserialize

__all__: list[str] = [
    "create_slack_app",
    "verify_slack_request",
    "slack_client",
    "get_slack_client",
    "initialize_slack_client",
    "get_queue_backend",
]

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.webhook.server")

# Global Slack client for common usage outside of this module
slack_client: Optional[AsyncWebClient] = None

# Global queue backend for publishing Slack events
_queue_backend: Optional[QueueBackend] = None

# Default topic/key for Slack events in the queue
DEFAULT_SLACK_EVENTS_TOPIC: Final[str] = "slack_events"


def get_queue_backend() -> QueueBackend:
    """Get or initialize the global queue backend.

    Returns
    -------
    QueueBackend
        The global queue backend instance
    """
    global _queue_backend

    if _queue_backend is None:
        _LOG.info("Initializing queue backend")
        _queue_backend = load_backend()

    return _queue_backend


def initialize_slack_client(token: str | None = None, retry: int = 0) -> AsyncWebClient:
    """Initialize the global Slack client.

    Parameters
    ----------
    token : str | None
        The Slack bot token to use. If None, will use SLACK_BOT_TOKEN env var.
    retry : int
        Number of retry attempts for Slack API operations (default: 0).
        If set to 0, no retry mechanism is used.
        If set to a positive value, uses Slack SDK's built-in retry handlers
        for rate limits, server errors, and connection issues.

    Returns
    -------
    AsyncWebClient
        The initialized Slack client

    Raises
    ------
    ValueError
        If no token is found (either from parameter or environment variables)
        or if retry count is negative.
    """
    global slack_client

    # Validate retry count
    if retry < 0:
        raise ValueError("Retry count must be non-negative")

    # Get the client manager and configure it with the retry count if needed
    client_manager = get_client_manager()
    if retry != client_manager._default_retry_count:
        client_manager.update_retry_count(retry)

    # Get the client with or without retries based on the retry parameter
    use_retries = retry > 0
    slack_client = client_manager.get_async_client(token, use_retries)

    return slack_client


def get_slack_client() -> AsyncWebClient:
    """Get the global Slack client.

    Returns
    -------
    AsyncWebClient
        The global Slack client

    Raises
    ------
    ValueError
        If the client has not been initialized
    """
    if slack_client is None:
        raise ValueError("Slack client not initialized. Call initialize_slack_client first.")
    return slack_client


async def verify_slack_request(request: Request, signing_secret: str | None = None) -> bool:
    """Verify that the request is coming from Slack.

    Parameters
    ----------
    request : Request
        The FastAPI request object
    signing_secret : str | None
        The Slack signing secret to use for verification. If None, will use SLACK_SIGNING_SECRET env var.

    Returns
    -------
    bool
        True if the request is valid, False otherwise
    """
    if signing_secret is None:
        signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
        if not signing_secret:
            _LOG.error("SLACK_SIGNING_SECRET not set in environment")
            return False

    verifier = SignatureVerifier(signing_secret)

    # Get request headers and body
    signature = request.headers.get("X-Slack-Signature", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")

    # Read the body
    body = await request.body()
    body_str = body.decode("utf-8")

    # Verify the request
    return verifier.is_valid(signature=signature, timestamp=timestamp, body=body_str)


def create_slack_app() -> FastAPI:
    """Create a FastAPI app for handling Slack events.

    Returns
    -------
    FastAPI
        The FastAPI app
    """
    app = FastAPI(title="Slack MCP Server")

    # Initialize the queue backend
    backend = get_queue_backend()

    # Get the topic for Slack events from environment or use default
    slack_events_topic = os.environ.get("SLACK_EVENTS_TOPIC", DEFAULT_SLACK_EVENTS_TOPIC)

    @app.get("/health")
    async def health_check() -> JSONResponse:
        """Health check endpoint for monitoring and load balancers.

        Returns
        -------
        JSONResponse
            Status information about the webhook server
        """
        try:
            # Check if the queue backend is accessible and functional
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

            # If we have a slack client, check its status
            slack_status = "not_initialized"
            if slack_client is not None:
                slack_status = "initialized"

            # Determine overall health status
            is_healthy = backend_status == "healthy"
            overall_status = "healthy" if is_healthy else "unhealthy"
            status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

            return JSONResponse(
                status_code=status_code,
                content={
                    "status": overall_status,
                    "service": "slack-webhook-server",
                    "components": {
                        "queue_backend": backend_status,
                        "slack_client": slack_status,
                    },
                },
            )
        except Exception as e:
            _LOG.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unhealthy", "service": "slack-webhook-server", "error": str(e)},
            )

    @app.post("/slack/events")
    async def slack_events(request: Request) -> Response:
        """Handle Slack events."""
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
            # Continue with the original dictionary approach as fallback
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
            # Use the Pydantic model for logging
            event_type = slack_event_model.event.type if hasattr(slack_event_model.event, "type") else "unknown"
            _LOG.info(f"Received Slack event: {event_type}")

            # Convert model to dict for publishing to queue
            event_dict = slack_event_model.model_dump()

            # Publish event to queue
            try:
                await backend.publish(slack_events_topic, event_dict)
                _LOG.info(f"Published event of type '{event_type}' to queue topic '{slack_events_topic}'")
            except Exception as e:
                _LOG.error(f"Error publishing event to queue: {e}")
        else:
            # Fallback to original dictionary approach
            event_type = slack_event_dict.get("event", {}).get("type", "unknown")
            _LOG.info(f"Received Slack event: {event_type}")

            # Publish event to queue
            try:
                await backend.publish(slack_events_topic, slack_event_dict)
                _LOG.info(f"Published event of type '{event_type}' to queue topic '{slack_events_topic}'")
            except Exception as e:
                _LOG.error(f"Error publishing event to queue: {e}")

        # Return 200 OK to acknowledge receipt of the event
        return JSONResponse(content={"status": "ok"})

    return app
