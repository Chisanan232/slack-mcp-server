"""Slack app implementation for handling Slack events.

This module defines a FastAPI application that serves as an endpoint for Slack events API.
It follows PEP 484/585 typing conventions.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Final, Optional, cast

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from slack_sdk.signature import SignatureVerifier
from slack_sdk.web.async_client import AsyncWebClient

from .client_factory import RetryableSlackClientFactory
from .event_handler import SlackEvent, register_handlers
from .slack_models import SlackEventModel, UrlVerificationModel, deserialize

__all__: list[str] = [
    "create_slack_app",
    "verify_slack_request",
    "handle_slack_event",
    "slack_client",
    "get_slack_client",
    "initialize_slack_client",
]

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.slack_app")

# Global Slack client for common usage outside of this module
slack_client: Optional[AsyncWebClient] = None


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

    # Resolve token
    resolved_token = token or os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_TOKEN")
    if not resolved_token:
        raise ValueError(
            "Slack token not found. Provide one via the 'token' parameter or set "
            "the SLACK_BOT_TOKEN/SLACK_TOKEN environment variable."
        )

    # Create Slack client
    if retry < 0:
        raise ValueError("Retry count must be non-negative")

    if retry == 0:
        slack_client = AsyncWebClient(token=resolved_token)
    else:
        # Create Slack client with retry capability using the RetryableSlackClientFactory
        # This uses Slack SDK's built-in retry handlers for rate limits, server errors, etc.
        client_factory = RetryableSlackClientFactory(max_retry_count=retry)
        slack_client = client_factory.create_async_client(resolved_token)

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


async def handle_slack_event(event_data: SlackEvent, client: AsyncWebClient) -> Dict[str, Any] | None:
    """Handle Slack events.

    Parameters
    ----------
    event_data : SlackEvent
        The event data from Slack
    client : AsyncWebClient
        The Slack client to use for API calls

    Returns
    -------
    dict[str, Any] | None
        The response from the event handler, or None if no handler was found
    """
    if "event" not in event_data:
        _LOG.warning("No event in event data")
        return None

    event = event_data["event"]
    event_type = event.get("type")

    if not event_type:
        _LOG.warning("No event type in event")
        return None

    # Get handlers for registered event types
    handlers = register_handlers()

    if event_type in handlers:
        _LOG.info(f"Handling event type: {event_type}")
        handler = handlers[event_type]
        return await handler(client, event)

    _LOG.warning(f"No handler for event type: {event_type}")
    return None


def create_slack_app(token: str | None = None, retry: int = 0) -> FastAPI:
    """Create a FastAPI app for handling Slack events.

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
    FastAPI
        The FastAPI app

    Raises
    ------
    ValueError
        If no token is found (either from parameter or environment variables)
        or if retry count is negative.
    """
    app = FastAPI(title="Slack MCP Server")

    # Initialize the global Slack client
    client = initialize_slack_client(token, retry)

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

        # Handle the event
        if isinstance(slack_event_model, SlackEventModel):
            # Use the Pydantic model for logging and processing
            _LOG.info(
                f"Received Slack event: {slack_event_model.event.type if hasattr(slack_event_model.event, 'type') else 'unknown'}"
            )
            # Convert model to dict for backward compatibility with handle_slack_event
            event_dict = slack_event_model.model_dump()
            await handle_slack_event(cast(SlackEvent, event_dict), client)
        else:
            # Fallback to original dictionary approach
            _LOG.info(f"Received Slack event: {slack_event_dict.get('event', {}).get('type')}")
            await handle_slack_event(cast(SlackEvent, slack_event_dict), client)

        # Return 200 OK to acknowledge receipt of the event
        return JSONResponse(content={"status": "ok"})

    return app
