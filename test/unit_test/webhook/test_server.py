"""Unit tests for the Slack app module."""

from typing import Any, AsyncIterator, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slack_sdk.web.async_client import AsyncWebClient

from slack_mcp.backends.protocol import QueueBackend
from slack_mcp.webhook.server import (
    create_slack_app,
    handle_slack_event,
    verify_slack_request,
)
from slack_mcp.slack_models import SlackEventModel, UrlVerificationModel


class MockQueueBackend(QueueBackend):
    """Mock implementation of QueueBackend for testing."""

    def __init__(self) -> None:
        """Initialize the mock backend with an empty list of published events."""
        self.published_events: list[Dict[str, Any]] = []
        self.published_topics: list[str] = []

    async def publish(self, topic: str, message: dict) -> None:
        """Publish a message to the mock backend."""
        self.published_topics.append(topic)
        self.published_events.append(message)

    async def consume(self, group: str | None = None) -> AsyncIterator[dict]:
        """Consume events from the mock backend."""
        for event in self.published_events:
            yield event

    @classmethod
    def from_env(cls) -> "MockQueueBackend":
        """Mock implementation of from_env classmethod."""
        return cls()


@pytest.fixture
def mock_queue_backend():
    """Create a mock queue backend."""
    return MockQueueBackend()


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


@pytest.fixture
def mock_verify_slack_request():
    """Mock the verify_slack_request function."""
    with patch("slack_mcp.webhook.server.verify_slack_request") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_deserialize():
    """Mock the deserialize function."""
    with patch("slack_mcp.webhook.server.deserialize") as mock:
        yield mock


@pytest.fixture
def mock_handle_slack_event():
    """Mock the handle_slack_event function."""
    with patch("slack_mcp.webhook.server.handle_slack_event") as mock:
        mock.return_value = None
        yield mock


@pytest.mark.asyncio
async def test_verify_slack_request_valid(mock_request):
    """Test verifying a valid Slack request."""
    with patch("slack_mcp.webhook.server.SignatureVerifier") as mock_sv:
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
    with patch("slack_mcp.webhook.server.SignatureVerifier") as mock_sv:
        mock_sv.return_value.is_valid.return_value = False

        result = await verify_slack_request(mock_request, signing_secret="test_secret")

        assert result is False
        mock_sv.assert_called_once_with("test_secret")


@pytest.mark.asyncio
async def test_verify_slack_request_env_var(mock_request):
    """Test verifying a Slack request using the environment variable."""
    with (
        patch("slack_mcp.webhook.server.SignatureVerifier") as mock_sv,
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


def test_create_slack_app_with_routes():
    """Test creating a Slack app with proper routes."""
    app = create_slack_app()

    # Verify the app has the expected routes
    routes = {route.path: route.methods for route in app.routes}
    assert "/slack/events" in routes
    assert "POST" in routes["/slack/events"]


@patch("slack_mcp.webhook.server.initialize_slack_client")
def test_create_slack_app_does_not_initialize_client(mock_initialize_client):
    """Test creating a Slack app doesn't initialize the client."""
    app = create_slack_app()

    assert isinstance(app, FastAPI)
    mock_initialize_client.assert_not_called()


@pytest.mark.asyncio
async def test_slack_events_endpoint_challenge():
    """Test the Slack events endpoint with a URL verification challenge."""
    with patch("slack_mcp.webhook.server.verify_slack_request", return_value=True):
        app = create_slack_app()
        client = TestClient(app)

        # Send request with challenge
        response = client.post("/slack/events", json={"challenge": "test_challenge"})

        assert response.status_code == 200
        assert response.json() == {"challenge": "test_challenge"}


@pytest.mark.asyncio
async def test_slack_events_endpoint_event(
    mock_verify_slack_request: MagicMock, mock_deserialize: MagicMock, mock_handle_slack_event: AsyncMock
):
    """Test the /slack/events endpoint with a standard event."""
    # Setup mocks
    mock_verify_slack_request.return_value = True
    mock_deserialize.return_value = {"event": {"type": "app_mention", "text": "Hello"}}
    mock_handle_slack_event.return_value = None

    # Create app and test client
    app = create_slack_app()
    client = TestClient(app)

    # Send request with event data
    response = client.post(
        "/slack/events",
        json={
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U12345",
                "text": "<@BOTID> Hello",
                "channel": "C12345",
                "ts": "1234567890.123456",
            },
            "team_id": "T12345",
            "api_app_id": "A12345",
            "event_id": "Ev12345",
            "event_time": 1234567890,
            "token": "test_token",
            "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
        },
        headers={"X-Slack-Signature": "valid_sig", "X-Slack-Request-Timestamp": "1234567890"},
    )

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify the deserialize function was called
    mock_deserialize.assert_called_once()

    # Verify event was published to the queue backend
    mock_handle_slack_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_slack_events_endpoint_with_pydantic_model(
    mock_verify_slack_request: MagicMock, mock_deserialize: MagicMock, mock_handle_slack_event: AsyncMock
):
    """Test the /slack/events endpoint with a Pydantic model."""
    # Mock the verify_slack_request to return True
    mock_verify_slack_request.return_value = True

    # Create a sample event model
    event_model = SlackEventModel(
        type="event_callback",
        event={
            "type": "app_mention",
            "user": "U12345",
            "text": "<@BOTID> Hello",
            "channel": "C12345",
            "ts": "1234567890.123456",
        },
        team_id="T12345",
        api_app_id="A12345",
        event_id="Ev12345",
        event_time=1234567890,
        token="test_token",
        authorizations=[{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
    )
    mock_deserialize.return_value = event_model
    mock_handle_slack_event.return_value = None

    # Create app and test client
    app = create_slack_app()
    client = TestClient(app)

    # Send request with event data
    response = client.post(
        "/slack/events",
        json={
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U12345",
                "text": "<@BOTID> Hello",
                "channel": "C12345",
                "ts": "1234567890.123456",
            },
            "team_id": "T12345",
            "api_app_id": "A12345",
            "event_id": "Ev12345",
            "event_time": 1234567890,
            "token": "test_token",
            "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
        },
        headers={"X-Slack-Signature": "valid_sig", "X-Slack-Request-Timestamp": "1234567890"},
    )

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify the deserialize function was called
    mock_deserialize.assert_called_once()

    # Verify event was published to the queue backend
    mock_handle_slack_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_slack_events_endpoint_with_queue_backend(
    mock_verify_slack_request: MagicMock, mock_deserialize: MagicMock, mock_handle_slack_event: AsyncMock
) -> None:
    """Test the Slack events endpoint with queue backend integration."""
    # Mock the verify_slack_request to return True
    mock_verify_slack_request.return_value = True

    # Create a sample event
    event_data = {
        "type": "event_callback",
        "event": {
            "type": "app_mention",
            "user": "U12345",
            "text": "<@BOTID> Hello",
            "channel": "C12345",
            "ts": "1234567890.123456",
        },
        "team_id": "T12345",
        "api_app_id": "A12345",
        "event_id": "Ev12345",
        "event_time": 1234567890,
        "token": "test_token",
        "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
    }

    # Mock the deserialize function to return a SlackEventModel
    event_model = SlackEventModel(
        type="event_callback",
        event={
            "type": "app_mention",
            "user": "U12345",
            "text": "<@BOTID> Hello",
            "channel": "C12345",
            "ts": "1234567890.123456",
        },
        team_id="T12345",
        api_app_id="A12345",
        event_id="Ev12345",
        event_time=1234567890,
        token="test_token",
        authorizations=[{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
    )
    mock_deserialize.return_value = event_model

    # Mock the queue backend
    mock_backend = AsyncMock()

    # Create app and test client
    with patch("slack_mcp.webhook.server._queue_backend", mock_backend):
        app = create_slack_app()
        client = TestClient(app)

        # Send request with event data
        response = client.post(
            "/slack/events",
            json=event_data,
            headers={"X-Slack-Signature": "valid_sig", "X-Slack-Request-Timestamp": "1234567890"},
        )

        # Verify response
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Verify the deserialize function was called
        mock_deserialize.assert_called_once()

        # Verify event was published to the queue backend
        mock_backend.publish.assert_awaited_once()

        # Verify handle_slack_event was not called since we're now publishing to queue
        mock_handle_slack_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_slack_events_endpoint_with_queue_backend_publish_error(
    mock_verify_slack_request: MagicMock, mock_deserialize: MagicMock, mock_handle_slack_event: AsyncMock
) -> None:
    """Test the Slack events endpoint with queue backend publish error."""
    # Mock the verify_slack_request to return True
    mock_verify_slack_request.return_value = True

    # Create a sample event
    event_data = {
        "type": "event_callback",
        "event": {
            "type": "app_mention",
            "user": "U12345",
            "text": "<@BOTID> Hello",
            "channel": "C12345",
            "ts": "1234567890.123456",
        },
        "team_id": "T12345",
        "api_app_id": "A12345",
        "event_id": "Ev12345",
        "event_time": 1234567890,
        "token": "test_token",
        "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
    }

    # Mock the deserialize function to return a SlackEventModel
    event_model = SlackEventModel(
        type="event_callback",
        event={
            "type": "app_mention",
            "user": "U12345",
            "text": "<@BOTID> Hello",
            "channel": "C12345",
            "ts": "1234567890.123456",
        },
        team_id="T12345",
        api_app_id="A12345",
        event_id="Ev12345",
        event_time=1234567890,
        token="test_token",
        authorizations=[{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
    )
    mock_deserialize.return_value = event_model

    # Mock the queue backend
    mock_backend = AsyncMock()
    mock_backend.publish.side_effect = Exception("Test publish error")

    # Create app and test client
    with patch("slack_mcp.webhook.server._queue_backend", mock_backend):
        app = create_slack_app()
        client = TestClient(app)

        # Send request with event data
        response = client.post(
            "/slack/events",
            json=event_data,
            headers={"X-Slack-Signature": "valid_sig", "X-Slack-Request-Timestamp": "1234567890"},
        )

        # Verify response
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Verify the deserialize function was called
        mock_deserialize.assert_called_once()

        # Verify event was published to the queue backend
        mock_backend.publish.assert_awaited_once()

        # Verify handle_slack_event was not called since we're now publishing to queue
        mock_handle_slack_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_slack_events_endpoint_with_queue_backend_publish_error_logging(
    mock_verify_slack_request: MagicMock, mock_deserialize: MagicMock, mock_handle_slack_event: AsyncMock
) -> None:
    """Test that errors during queue publishing are properly logged."""
    # Mock the verify_slack_request to return True
    mock_verify_slack_request.return_value = True

    # Create a sample event
    event_data = {
        "type": "event_callback",
        "event": {
            "type": "app_mention",
            "user": "U12345",
            "text": "<@BOTID> Hello",
            "channel": "C12345",
            "ts": "1234567890.123456",
        },
        "team_id": "T12345",
        "api_app_id": "A12345",
        "event_id": "Ev12345",
        "event_time": 1234567890,
        "token": "test_token",
    }

    # Mock the deserialize function to return None to test the dictionary fallback path
    mock_deserialize.return_value = None

    # Create a specific exception to test error logging
    test_exception = Exception("Test publish error")

    # Mock the queue backend to raise the exception
    mock_backend = AsyncMock()
    mock_backend.publish.side_effect = test_exception

    # Create app and test client
    with (
        patch("slack_mcp.webhook.server._queue_backend", mock_backend),
        patch("slack_mcp.webhook.server._LOG") as mock_logger,
        patch("slack_mcp.webhook.server.DEFAULT_SLACK_EVENTS_TOPIC", "test_slack_events"),  # Match the topic used in tests
    ):
        app = create_slack_app()
        client = TestClient(app)

        # Send request with event data
        response = client.post(
            "/slack/events",
            json=event_data,
            headers={"X-Slack-Signature": "valid_sig", "X-Slack-Request-Timestamp": "1234567890"},
        )

        # Verify response is still 200 OK despite the error
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Verify the error was logged with the correct message
        mock_logger.error.assert_called_once_with(f"Error publishing event to queue: {test_exception}")

        # Verify event publication was attempted with the test topic name
        mock_backend.publish.assert_awaited_once_with("test_slack_events", event_data)

        # Verify handle_slack_event was not called
        mock_handle_slack_event.assert_not_awaited()


@pytest.mark.parametrize(
    "event_data,expected_status,expected_response,should_handle",
    [
        # Test case 1: Standard event
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
                "team_id": "T12345",
                "api_app_id": "A12345",
                "event_id": "Ev12345",
                "event_time": 1234567890,
                "token": "test_token",
                "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
            },
            200,
            {"status": "ok"},
            False,  # Changed from True to False since we're publishing to queue
        ),
        # Test case 2: URL verification challenge
        (
            {"type": "url_verification", "challenge": "test_challenge", "token": "test_token"},
            200,
            {"challenge": "test_challenge"},
            False,
        ),
        # Test case 3: Message event
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
                "team_id": "T12345",
                "api_app_id": "A12345",
                "event_id": "Ev12345",
                "event_time": 1234567890,
                "token": "test_token",
                "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
            },
            200,
            {"status": "ok"},
            False,  # Changed from True to False since we're publishing to queue
        ),
        # Test case 4: Reaction added event
        (
            {
                "type": "event_callback",
                "event": {
                    "type": "reaction_added",
                    "user": "U12345",
                    "reaction": "thumbsup",
                    "item": {"type": "message", "channel": "C12345", "ts": "1234567890.123456"},
                },
                "team_id": "T12345",
                "api_app_id": "A12345",
                "event_id": "Ev12345",
                "event_time": 1234567890,
                "token": "test_token",
                "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
            },
            200,
            {"status": "ok"},
            False,  # Changed from True to False since we're publishing to queue
        ),
        # Test case 5: Unknown event type
        (
            {
                "type": "event_callback",
                "event": {
                    "type": "unknown_event_type",
                    "user": "U12345",
                },
                "team_id": "T12345",
                "api_app_id": "A12345",
                "event_id": "Ev12345",
                "event_time": 1234567890,
                "token": "test_token",
                "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
            },
            200,
            {"status": "ok"},
            False,  # Changed from True to False since we're publishing to queue
        ),
        # Test case 6: Invalid event (no event field)
        (
            {
                "type": "event_callback",
                "team_id": "T12345",
                "api_app_id": "A12345",
                "event_id": "Ev12345",
                "event_time": 1234567890,
                "token": "test_token",
                "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
            },
            200,
            {"status": "ok"},
            False,
        ),
    ],
)
@pytest.mark.asyncio
async def test_slack_events_endpoint_parametrized(
    event_data: Dict[str, Any],
    expected_status: int,
    expected_response: Dict[str, Any],
    should_handle: bool,
    mock_verify_slack_request: MagicMock,
    mock_deserialize: MagicMock,
    mock_handle_slack_event: AsyncMock,
) -> None:
    """Test the /slack/events endpoint with various event types."""
    # Mock the verify_slack_request to return True
    mock_verify_slack_request.return_value = True

    # Mock the deserialize function based on the event type
    if event_data.get("type") == "url_verification":
        mock_deserialize.return_value = UrlVerificationModel(
            type="url_verification", challenge=event_data["challenge"], token=event_data["token"]
        )
    elif event_data.get("type") == "event_callback" and "event" in event_data:
        mock_deserialize.return_value = SlackEventModel(
            type="event_callback",
            event=event_data["event"],
            team_id=event_data["team_id"],
            api_app_id=event_data["api_app_id"],
            event_id=event_data["event_id"],
            event_time=event_data["event_time"],
            token=event_data["token"],
            authorizations=event_data["authorizations"],
        )
    else:
        mock_deserialize.return_value = event_data

    # Mock the queue backend
    mock_backend = AsyncMock()

    # Create app and test client
    with patch("slack_mcp.webhook.server._queue_backend", mock_backend):
        app = create_slack_app()
        client = TestClient(app)

        # Send request with event data
        response = client.post(
            "/slack/events",
            json=event_data,
            headers={"X-Slack-Signature": "valid_sig", "X-Slack-Request-Timestamp": "1234567890"},
        )

        # Verify response
        assert response.status_code == expected_status
        assert response.json() == expected_response

        # Verify the deserialize function was called
        mock_deserialize.assert_called_once()

        # Verify handle_slack_event was called if should_handle is True
        if should_handle:
            mock_handle_slack_event.assert_awaited_once()
        else:
            mock_handle_slack_event.assert_not_awaited()

        # For event_callback types that aren't URL verification, verify queue publish was called
        if event_data.get("type") == "event_callback":
            mock_backend.publish.assert_awaited_once()
