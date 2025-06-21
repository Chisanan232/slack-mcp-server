"""End-to-end tests for the Slack bot event handling features."""

import json
import os
import pytest
from unittest.mock import AsyncMock, patch

from slack_sdk.web.async_client import AsyncWebClient
from slack_mcp.slack_app import create_slack_app


@pytest.fixture
def mock_client():
    """Create a mock Slack client that returns appropriate responses."""
    client = AsyncMock(spec=AsyncWebClient)
    client.chat_postMessage.return_value = AsyncMock(data={"ok": True, "ts": "1234567890.123456"})
    client.conversations_history.return_value = AsyncMock(
        data={"ok": True, "messages": [{"text": "Hello", "bot_id": "B12345678", "ts": "1234567890.123456"}]}
    )
    return client


def test_e2e_app_mention():
    """Test the end-to-end flow for an app_mention event."""
    with patch("slack_mcp.slack_app.AsyncWebClient") as mock_client_cls, \
         patch("slack_mcp.slack_app.verify_slack_request", return_value=True), \
         patch("slack_mcp.slack_app.handle_slack_event") as mock_handle_event, \
         patch.dict("os.environ", {"SLACK_BOT_TOKEN": "test_token"}):
        
        # Create a mock client
        mock_client = AsyncMock()
        mock_client.chat_postMessage.return_value = AsyncMock(data={"ok": True, "ts": "1234567890.123456"})
        mock_client_cls.return_value = mock_client
        
        # Create the Flask app
        app = create_slack_app()
        app.config['TESTING'] = True
        client = app.test_client()
        
        # Create an app_mention event
        event_data = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U12345678",
                "text": "<@U87654321> Hello bot!",
                "ts": "1234567890.123456",
                "channel": "C12345678",
            }
        }
        
        # Send the event to the endpoint
        response = client.post(
            "/slack/events",
            data=json.dumps(event_data),
            content_type="application/json"
        )
        
        # Verify the response
        assert response.status_code == 200
        assert json.loads(response.data)["status"] == "ok"
        
        # Verify handle_slack_event was called with the right arguments
        mock_handle_event.assert_called_once()
        # Extract the event and client arguments
        args, _ = mock_handle_event.call_args
        assert args[0]["event"]["type"] == "app_mention"
        assert args[0]["event"]["text"] == "<@U87654321> Hello bot!"


def test_e2e_reaction_added():
    """Test the end-to-end flow for a reaction_added event."""
    with patch("slack_mcp.slack_app.AsyncWebClient") as mock_client_cls, \
         patch("slack_mcp.slack_app.verify_slack_request", return_value=True), \
         patch("slack_mcp.slack_app.handle_slack_event") as mock_handle_event, \
         patch.dict("os.environ", {
             "SLACK_BOT_TOKEN": "test_token",
             "SLACK_BOT_ID": "B12345678"
         }):
        
        # Create a mock client
        mock_client = AsyncMock()
        mock_client.chat_postMessage.return_value = AsyncMock(data={"ok": True, "ts": "1234567890.123457"})
        mock_client.conversations_history.return_value = AsyncMock(
            data={"ok": True, "messages": [{"text": "Hello", "bot_id": "B12345678", "ts": "1234567890.123456"}]}
        )
        mock_client_cls.return_value = mock_client
        
        # Create the Flask app
        app = create_slack_app()
        app.config['TESTING'] = True
        client = app.test_client()
        
        # Create a reaction_added event
        event_data = {
            "type": "event_callback",
            "event": {
                "type": "reaction_added",
                "user": "U12345678",
                "reaction": "thumbsup",
                "item": {
                    "type": "message",
                    "channel": "C12345678",
                    "ts": "1234567890.123456",
                },
                "event_ts": "1234567890.123457",
            }
        }
        
        # Send the event to the endpoint
        response = client.post(
            "/slack/events",
            data=json.dumps(event_data),
            content_type="application/json"
        )
        
        # Verify the response
        assert response.status_code == 200
        assert json.loads(response.data)["status"] == "ok"
        
        # Verify handle_slack_event was called with the right arguments
        mock_handle_event.assert_called_once()
        # Extract the event and client arguments
        args, _ = mock_handle_event.call_args
        assert args[0]["event"]["type"] == "reaction_added"
        assert args[0]["event"]["reaction"] == "thumbsup"


def test_e2e_url_verification():
    """Test the end-to-end flow for URL verification."""
    with patch("slack_mcp.slack_app.AsyncWebClient"), \
         patch("slack_mcp.slack_app.verify_slack_request", return_value=True), \
         patch.dict("os.environ", {"SLACK_BOT_TOKEN": "test_token"}):
        
        # Create the Flask app
        app = create_slack_app()
        app.config['TESTING'] = True
        client = app.test_client()
        
        # Create a URL verification event
        event_data = {
            "type": "url_verification",
            "challenge": "test_challenge"
        }
        
        # Send the event to the endpoint
        response = client.post(
            "/slack/events",
            data=json.dumps(event_data),
            content_type="application/json"
        )
        
        # Verify the response
        assert response.status_code == 200
        assert json.loads(response.data)["challenge"] == "test_challenge"
