"""Slack app implementation for handling Slack events.

This module defines a Flask application that serves as an endpoint for Slack events API.
It follows PEP 484/585 typing conventions.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Final, cast

import flask
from flask import Flask, Request, Response, request
from slack_sdk.signature import SignatureVerifier
from slack_sdk.web.async_client import AsyncWebClient

from .event_handler import SlackEvent, register_handlers

__all__: list[str] = [
    "create_slack_app",
    "verify_slack_request",
    "handle_slack_event",
]

_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.slack_app")


def verify_slack_request(request: Request, signing_secret: str | None = None) -> bool:
    """Verify that the request is coming from Slack.

    Parameters
    ----------
    request : Request
        The Flask request object
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
    body = request.get_data().decode("utf-8")

    # Verify the request
    return verifier.is_valid(signature=signature, timestamp=timestamp, body=body)


async def handle_slack_event(event_data: SlackEvent, client: AsyncWebClient) -> dict[str, Any] | None:
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


def create_slack_app(token: str | None = None) -> Flask:
    """Create a Flask app for handling Slack events.

    Parameters
    ----------
    token : str | None
        The Slack bot token to use. If None, will use SLACK_BOT_TOKEN env var.

    Returns
    -------
    Flask
        The Flask app
    """
    app = Flask(__name__)

    # Resolve token
    resolved_token = token or os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_TOKEN")
    if not resolved_token:
        raise ValueError(
            "Slack token not found. Provide one via the 'token' parameter or set "
            "the SLACK_BOT_TOKEN/SLACK_TOKEN environment variable."
        )

    # Create Slack client
    client = AsyncWebClient(token=resolved_token)

    @app.route("/slack/events", methods=["POST"])
    async def slack_events() -> Response:
        """Handle Slack events."""
        # Verify the request is from Slack
        if not verify_slack_request(request):
            _LOG.warning("Invalid Slack request signature")
            return flask.jsonify({"error": "Invalid request signature"}), 401

        # Parse the request body
        slack_event = json.loads(request.data)

        # Handle URL verification challenge
        if "challenge" in slack_event:
            _LOG.info("Handling URL verification challenge")
            return flask.jsonify({"challenge": slack_event["challenge"]})

        # Handle the event
        _LOG.info(f"Received Slack event: {slack_event.get('event', {}).get('type')}")
        await handle_slack_event(cast(SlackEvent, slack_event), client)

        # Return 200 OK to acknowledge receipt of the event
        return flask.jsonify({"status": "ok"}), 200

    return app
