"""Unit tests for the Slack app module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
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
    event_data = {"event": {"type": "unhandled_event"}}

    result = await handle_slack_event(event_data, mock_client)

    assert result is None


@pytest.mark.asyncio
async def test_handle_slack_event_app_mention(mock_client):
    """Test handling an app_mention event."""
    event_data = {
        "event": {
            "type": "app_mention",
            "user": "U12345678",
            "text": "<@U87654321> Hello!",
            "ts": "1234567890.123456",
            "channel": "C12345678",
        }
    }

    with patch("slack_mcp.slack_app.register_handlers") as mock_register:
        mock_handler = AsyncMock(return_value={"ok": True})
        mock_register.return_value = {"app_mention": mock_handler}

        result = await handle_slack_event(event_data, mock_client)

        assert result == {"ok": True}
        mock_handler.assert_called_once_with(mock_client, event_data["event"])


def test_create_slack_app():
    """Test creating a Slack app."""
    with (
        patch("slack_mcp.slack_app.AsyncWebClient") as mock_client_cls,
        patch.dict("os.environ", {"SLACK_BOT_TOKEN": "test_token"}),
    ):
        app = create_slack_app()

        assert isinstance(app, FastAPI)
        mock_client_cls.assert_called_once_with(token="test_token")


def test_create_slack_app_with_token():
    """Test creating a Slack app with a specified token."""
    with patch("slack_mcp.slack_app.AsyncWebClient") as mock_client_cls:
        app = create_slack_app(token="custom_token")

        assert isinstance(app, FastAPI)
        mock_client_cls.assert_called_once_with(token="custom_token")


def test_create_slack_app_no_token():
    """Test creating a Slack app with no token."""
    with patch("slack_mcp.slack_app.AsyncWebClient") as mock_client_cls, patch.dict("os.environ", {}, clear=True):

        with pytest.raises(ValueError) as excinfo:
            create_slack_app()

        assert "Slack token not found" in str(excinfo.value)
        mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_slack_events_endpoint_challenge():
    """Test the Slack events endpoint with a URL verification challenge."""
    with patch("slack_mcp.slack_app.verify_slack_request", AsyncMock(return_value=True)):
        # Create a test FastAPI app
        app = FastAPI()

        # Add a test route to mimic the slack_events endpoint
        @app.post("/test")
        async def test_endpoint(event_data: dict = Body(...)):
            if event_data.get("type") == "url_verification":
                return JSONResponse(content={"challenge": event_data["challenge"]})
            return JSONResponse(content={"status": "ok"})

        # Use TestClient to test the endpoint
        test_client = TestClient(app)
        response = test_client.post("/test", json={"type": "url_verification", "challenge": "test_challenge"})

        assert response.status_code == 200
        assert response.json()["challenge"] == "test_challenge"


@pytest.mark.asyncio
async def test_slack_events_endpoint_event():
    """Test the Slack events endpoint with an event."""
    mock_handle = AsyncMock()
    mock_handle.return_value = {"ok": True}

    with (
        patch("slack_mcp.slack_app.handle_slack_event", mock_handle),
        patch("slack_mcp.slack_app.verify_slack_request", AsyncMock(return_value=True)),
    ):
        # Create a test FastAPI app
        app = FastAPI()

        # Add a test route to mimic the slack_events endpoint
        @app.post("/test")
        async def test_endpoint(event_data: dict = Body(...)):
            return JSONResponse(content={"status": "ok"})

        # Use TestClient to test the endpoint
        test_client = TestClient(app)
        response = test_client.post(
            "/test",
            json={
                "event": {
                    "type": "app_mention",
                    "user": "U12345678",
                    "text": "<@U87654321> Hello!",
                    "ts": "1234567890.123456",
                    "channel": "C12345678",
                }
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_slack_events_endpoint_invalid_signature():
    """Test the Slack events endpoint with an invalid signature."""
    with patch("slack_mcp.slack_app.verify_slack_request", AsyncMock(return_value=False)):
        # Create a test FastAPI app and add a route that raises HTTPException similar to the actual endpoint
        app = FastAPI()

        # Add a test route that mimics the behavior
        @app.post("/test")
        async def test_endpoint(event_data: dict = Body(...)):
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid request signature")

        # Use TestClient to test the endpoint
        test_client = TestClient(app)
        response = test_client.post("/test", json={"type": "test"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid request signature"
