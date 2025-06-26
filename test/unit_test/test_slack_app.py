"""Unit tests for the Slack app module."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slack_sdk.web.async_client import AsyncWebClient

from slack_mcp.slack_app import (
    create_slack_app,
    handle_slack_event,
    verify_slack_request,
)


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock()
    request.headers = {"X-Slack-Signature": "test_signature", "X-Slack-Request-Timestamp": "1234567890"}
    request.body = AsyncMock(return_value=b"test_body")
    return request


@pytest.fixture
def mock_verifier():
    """Create a mock SignatureVerifier."""
    verifier = MagicMock()
    verifier.is_valid.return_value = True
    return verifier


@pytest.fixture
def mock_client():
    """Create a mock Slack client."""
    client = AsyncMock(spec=AsyncWebClient)
    client.chat_postMessage.return_value = AsyncMock(data={"ok": True, "ts": "1234567890.123456"})
    return client


@pytest.mark.asyncio
async def test_verify_slack_request_valid(mock_request):
    """Test verifying a valid Slack request."""
    with patch("slack_mcp.slack_app.SignatureVerifier") as mock_sv:
        mock_sv.return_value.is_valid.return_value = True

        result = await verify_slack_request(mock_request, signing_secret="test_secret")

        assert result is True
        mock_sv.assert_called_once_with("test_secret")
        mock_sv.return_value.is_valid.assert_called_once_with(
            signature="test_signature",
            timestamp="1234567890",
            body="test_body",
        )


@pytest.mark.asyncio
async def test_verify_slack_request_invalid(mock_request):
    """Test verifying an invalid Slack request."""
    with patch("slack_mcp.slack_app.SignatureVerifier") as mock_sv:
        mock_sv.return_value.is_valid.return_value = False

        result = await verify_slack_request(mock_request, signing_secret="test_secret")

        assert result is False
        mock_sv.assert_called_once_with("test_secret")


@pytest.mark.asyncio
async def test_verify_slack_request_env_var(mock_request):
    """Test verifying a Slack request using the environment variable."""
    with (
        patch("slack_mcp.slack_app.SignatureVerifier") as mock_sv,
        patch.dict("os.environ", {"SLACK_SIGNING_SECRET": "env_secret"}),
    ):
        mock_sv.return_value.is_valid.return_value = True

        result = await verify_slack_request(mock_request)

        assert result is True
        mock_sv.assert_called_once_with("env_secret")


@pytest.mark.asyncio
async def test_handle_slack_event_no_event(mock_client):
    """Test handling a Slack event with no event data."""
    event_data = {"type": "event_callback"}

    result = await handle_slack_event(event_data, mock_client)

    assert result is None


@pytest.mark.asyncio
async def test_handle_slack_event_no_type(mock_client):
    """Test handling a Slack event with no event type."""
    event_data = {"event": {}}

    result = await handle_slack_event(event_data, mock_client)

    assert result is None


@pytest.mark.asyncio
async def test_handle_slack_event_unhandled_type(mock_client):
    """Test handling a Slack event with an unhandled event type."""
    event_data = {"event": {"type": "unknown_event_type"}}

    result = await handle_slack_event(event_data, mock_client)

    assert result is None


@pytest.mark.asyncio
async def test_handle_slack_event_app_mention(mock_client):
    """Test handling an app_mention event."""
    event_data = {
        "event": {
            "type": "app_mention",
            "user": "U12345",
            "text": "<@BOTID> Hello there!",
            "channel": "C12345",
            "ts": "1234567890.123456",
            "thread_ts": "1234567890.123456",
        }
    }

    result = await handle_slack_event(event_data, mock_client)

    assert result is not None
    mock_client.chat_postMessage.assert_called_once_with(
        channel="C12345",
        text="You said: Hello there!",
        thread_ts="1234567890.123456",
    )


def test_create_slack_app():
    """Test creating a Slack app."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "env_token"}):
        app = create_slack_app()

    assert isinstance(app, FastAPI)
    # Check routes were registered
    assert any(route.path == "/slack/events" for route in app.routes)


def test_create_slack_app_with_token():
    """Test creating a Slack app with a specified token."""
    app = create_slack_app(token="test_token")

    assert isinstance(app, FastAPI)
    assert any(route.path == "/slack/events" for route in app.routes)


def test_create_slack_app_no_token():
    """Test creating a Slack app with no token."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "", "SLACK_TOKEN": ""}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            create_slack_app()

        assert "Slack token not found" in str(excinfo.value)


def test_slack_events_endpoint_challenge():
    """Test the Slack events endpoint with a URL verification challenge."""
    with (
        patch("slack_mcp.slack_app.verify_slack_request") as mock_verify,
        patch.dict("os.environ", {"SLACK_BOT_TOKEN": "test_token"}),
    ):
        mock_verify.return_value = True

        # Create app and test client
        app = create_slack_app(token="test_token")
        client = TestClient(app)

        # Send request with challenge
        response = client.post("/slack/events", json={"challenge": "test_challenge"})

        assert response.status_code == 200
        assert response.json() == {"challenge": "test_challenge"}


def test_slack_events_endpoint_event():
    """Test the Slack events endpoint with an event."""
    with (
        patch("slack_mcp.slack_app.verify_slack_request") as mock_verify,
        patch("slack_mcp.slack_app.handle_slack_event") as mock_handle,
        patch.dict("os.environ", {"SLACK_BOT_TOKEN": "test_token"}),
    ):
        mock_verify.return_value = True
        mock_handle.return_value = None

        # Create app and test client
        app = create_slack_app(token="test_token")
        client = TestClient(app)

        # Send request with an event
        event_data = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U12345",
                "text": "<@BOTID> Hello",
                "channel": "C12345",
                "ts": "1234567890.123456",
            },
        }
        response = client.post("/slack/events", json=event_data)

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_handle.assert_awaited_once()


def test_slack_events_endpoint_invalid_signature():
    """Test the Slack events endpoint with an invalid signature."""
    with (
        patch("slack_mcp.slack_app.verify_slack_request") as mock_verify,
        patch.dict("os.environ", {"SLACK_BOT_TOKEN": "test_token"}),
    ):
        mock_verify.return_value = False

        # Create app and test client
        app = create_slack_app(token="test_token")
        client = TestClient(app)

        # Send request and check for 401 status code
        response = client.post("/slack/events", json={"type": "event_callback"})
        assert response.status_code == 401
        assert "Invalid request signature" in response.json()["detail"]


@pytest.mark.parametrize(
    "event_data, expected_status, expected_response, should_call_handle_event",
    [
        # Challenge verification
        ({"challenge": "verification_challenge"}, 200, {"challenge": "verification_challenge"}, False),
        # App mention event
        (
            {
                "type": "event_callback",
                "event": {
                    "type": "app_mention",
                    "user": "U12345",
                    "text": "<@BOTID> Hello",
                    "channel": "C12345",
                    "ts": "1234567890.123456",
                },
            },
            200,
            {"status": "ok"},
            True,
        ),
        # Message event
        (
            {
                "type": "event_callback",
                "event": {
                    "type": "message",
                    "user": "U12345",
                    "text": "Hello",
                    "channel": "C12345",
                    "ts": "1234567890.123456",
                },
            },
            200,
            {"status": "ok"},
            True,
        ),
        # Reaction added event
        (
            {
                "type": "event_callback",
                "event": {
                    "type": "reaction_added",
                    "user": "U12345",
                    "reaction": "thumbsup",
                    "item": {"type": "message", "channel": "C12345", "ts": "1234567890.123456"},
                },
            },
            200,
            {"status": "ok"},
            True,
        ),
        # Empty event (still processes but handle_slack_event will return None)
        ({"type": "event_callback"}, 200, {"status": "ok"}, True),
        # Malformed event (still returns 200 but logs a warning)
        ({"not_a_valid_event": True}, 200, {"status": "ok"}, True),
    ],
)
def test_slack_events_endpoint_parametrized(event_data, expected_status, expected_response, should_call_handle_event):
    """Test the slack_events endpoint with different event scenarios."""
    with (
        patch("slack_mcp.slack_app.verify_slack_request") as mock_verify,
        patch("slack_mcp.slack_app.handle_slack_event") as mock_handle,
        patch.dict("os.environ", {"SLACK_BOT_TOKEN": "test_token"}),
    ):
        mock_verify.return_value = True
        mock_handle.return_value = None

        # Create app and test client
        app = create_slack_app(token="test_token")
        client = TestClient(app)

        # Send request with the event data
        response = client.post("/slack/events", json=event_data)

        # Check the response
        assert response.status_code == expected_status
        assert response.json() == expected_response

        # Verify handle_slack_event was called appropriately
        if should_call_handle_event:
            mock_handle.assert_awaited_once()
        else:
            mock_handle.assert_not_awaited()


@pytest.mark.parametrize(
    "request_body, should_fail",
    [
        # Valid JSON
        (b'{"challenge": "test_challenge"}', False),
        # Invalid JSON (syntax error)
        (b'{"challenge": "test_challenge"', True),
        # Empty body
        (b"", True),
    ],
)
def test_slack_events_endpoint_json_parsing(request_body, should_fail):
    """Test the slack_events endpoint with different JSON inputs."""
    with (
        patch("slack_mcp.slack_app.verify_slack_request") as mock_verify,
        patch("fastapi.Request") as MockRequest,
        patch("slack_mcp.slack_app.handle_slack_event") as mock_handle,
        patch.dict("os.environ", {"SLACK_BOT_TOKEN": "test_token"}),
    ):
        mock_verify.return_value = True
        mock_handle.return_value = None

        # Create a mock request with the specified body
        mock_request = AsyncMock()
        mock_request.body = AsyncMock(return_value=request_body)
        mock_request.headers = {"X-Slack-Signature": "test_sig", "X-Slack-Request-Timestamp": "1234"}
        MockRequest.return_value = mock_request

        # Create app and get the slack_events endpoint function
        app = create_slack_app(token="test_token")
        slack_events_function = None
        for route in app.routes:
            if route.path == "/slack/events" and route.methods == {"POST"}:
                slack_events_function = route.endpoint
                break

        assert slack_events_function is not None

        # Test the function directly
        if should_fail:
            with pytest.raises(Exception):  # Could be JSONDecodeError or other exceptions
                response = asyncio.run(slack_events_function(mock_request))
        else:
            response = asyncio.run(slack_events_function(mock_request))
            if b'"challenge"' in request_body:
                expected_json = json.loads(request_body)
                actual_json = json.loads(response.body.decode("utf-8"))
                assert actual_json == expected_json
            else:
                assert response.body.decode("utf-8") == json.dumps({"status": "ok"})
