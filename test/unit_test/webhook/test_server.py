"""Unit tests for the Slack app module."""

from typing import Any, AsyncIterator, Dict, Generator
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from abe.backends.message_queue.base.protocol import MessageQueueBackend
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slack_sdk.web.async_client import AsyncWebClient

from slack_mcp.mcp.app import MCPServerFactory
from slack_mcp.webhook.app import WebServerFactory
from slack_mcp.webhook.models import SlackEventModel, UrlVerificationModel
from slack_mcp.webhook.server import (
    create_slack_app,
    verify_slack_request,
)


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Reset the settings singleton before each test."""
    from slack_mcp import settings as settings_mod

    settings_mod._settings = None
    monkeypatch.setenv("MCP_NO_ENV_FILE", "true")
    yield
    settings_mod._settings = None


class MockMessageQueueBackend(MessageQueueBackend):
    """Mock implementation of MessageQueueBackend for testing."""

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
    def from_env(cls) -> "MockMessageQueueBackend":
        """Mock implementation of from_env classmethod."""
        return cls()


@pytest.fixture
def mock_queue_backend():
    """Create a mock queue backend."""
    return MockMessageQueueBackend()


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


@pytest.fixture(autouse=True)
def setup_web_server():
    """Ensure both MCPServerFactory and WebServerFactory have instances for tests."""
    # Reset any existing state
    MCPServerFactory.reset()
    WebServerFactory.reset()

    # Create MCP factory instance first (required by WebServerFactory)
    MCPServerFactory.create()

    # Create a fresh web server instance for the test
    WebServerFactory.create()

    yield

    # Clean up after the test
    WebServerFactory.reset()
    MCPServerFactory.reset()


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
        patch("slack_mcp.webhook.server.get_settings") as mock_get_settings,
    ):
        # Mock settings to return the signing secret
        mock_settings = mock.MagicMock()
        mock_settings.slack_signing_secret.get_secret_value.return_value = "env_secret"
        mock_get_settings.return_value = mock_settings

        mock_sv.return_value.is_valid.return_value = True

        result = await verify_slack_request(mock_request)

        assert result is True
        mock_sv.assert_called_once_with("env_secret")


def test_create_slack_app_with_routes():
    """Test creating a Slack app with proper routes."""
    app = create_slack_app()

    # Verify the app has the expected routes (filter out Mount objects which don't have methods)
    routes = {route.path: route.methods for route in app.routes if hasattr(route, "methods")}
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
async def test_slack_events_endpoint_event(mock_verify_slack_request: MagicMock, mock_deserialize: MagicMock):
    """Test the /slack/events endpoint with a standard event."""
    # Setup mocks
    mock_verify_slack_request.return_value = True
    mock_deserialize.return_value = {"event": {"type": "app_mention", "text": "Hello"}}

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


@pytest.mark.asyncio
async def test_slack_events_endpoint_with_pydantic_model(
    mock_verify_slack_request: MagicMock, mock_deserialize: MagicMock
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


@pytest.mark.asyncio
async def test_slack_events_endpoint_with_queue_backend(
    mock_verify_slack_request: MagicMock, mock_deserialize: MagicMock
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

    # Create app first
    app = create_slack_app()
    client = TestClient(app)

    # Get the backend instance and patch its publish method
    from slack_mcp.webhook.server import get_queue_backend

    backend = get_queue_backend()
    mock_publish = AsyncMock()

    with patch.object(backend, "publish", mock_publish):
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
        from slack_mcp.settings import get_settings

        expected_topic = get_settings().slack_events_topic
        mock_publish.assert_awaited_once_with(expected_topic, event_model.model_dump())


@pytest.mark.asyncio
async def test_slack_events_endpoint_with_queue_backend_publish_error(
    mock_verify_slack_request: MagicMock, mock_deserialize: MagicMock
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

    # Create app first
    app = create_slack_app()
    client = TestClient(app)

    # Get the backend instance and patch its publish method to raise an exception
    from slack_mcp.webhook.server import get_queue_backend

    backend = get_queue_backend()
    mock_publish = AsyncMock(side_effect=Exception("Test publish error"))

    with patch.object(backend, "publish", mock_publish):
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
        from slack_mcp.settings import get_settings

        expected_topic = get_settings().slack_events_topic
        mock_publish.assert_awaited_once_with(expected_topic, event_model.model_dump())


@pytest.mark.asyncio
async def test_slack_events_endpoint_with_queue_backend_publish_error_logging(
    mock_verify_slack_request: MagicMock, mock_deserialize: MagicMock
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

    # Set the environment variable for the topic name
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    mp.setenv("SLACK_EVENTS_TOPIC", "test_slack_events")

    # Ensure settings are reloaded with the new env var
    from slack_mcp import settings as settings_mod

    settings_mod.get_settings(force_reload=True)

    # Create app first
    with patch("slack_mcp.webhook.server._LOG") as mock_logger:
        app = create_slack_app()
        client = TestClient(app)

        # Get the backend instance and patch its publish method to raise the exception
        from slack_mcp.webhook.server import get_queue_backend

        backend = get_queue_backend()
        mock_publish = AsyncMock(side_effect=test_exception)

        with patch.object(backend, "publish", mock_publish):
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
            mock_publish.assert_awaited_once_with("test_slack_events", event_data)

    mp.undo()


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

    # Create app first
    app = create_slack_app()
    client = TestClient(app)

    # Get the backend instance and patch its publish method
    from slack_mcp.webhook.server import get_queue_backend

    backend = get_queue_backend()
    mock_publish = AsyncMock()

    with patch.object(backend, "publish", mock_publish):
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

        # For event_callback types that aren't URL verification, verify queue publish was called
        if event_data.get("type") == "event_callback":
            mock_publish.assert_awaited_once()


class TestHealthCheckEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check_success_with_initialized_client(self, mock_queue_backend):
        """Test health check returns 200 when all components are healthy."""
        with patch("slack_mcp.webhook.server.get_queue_backend", return_value=mock_queue_backend):
            with patch("slack_mcp.webhook.server.slack_client", AsyncWebClient(token="test")):
                app = create_slack_app()
                client = TestClient(app)

                response = client.get("/health")

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["status"] == "healthy"
                assert response_data["service"] == "slack-webhook-server"
                assert response_data["components"]["queue_backend"] == "healthy"
                assert response_data["components"]["slack_client"] == "initialized"

                # Verify that the backend publish was called with health check message
                assert len(mock_queue_backend.published_events) == 1
                published_event = mock_queue_backend.published_events[0]
                assert published_event["type"] == "health_check"

    def test_health_check_success_without_slack_client(self, mock_queue_backend):
        """Test health check returns 200 even when Slack client is not initialized."""
        with patch("slack_mcp.webhook.server.get_queue_backend", return_value=mock_queue_backend):
            with patch("slack_mcp.webhook.server.slack_client", None):
                app = create_slack_app()
                client = TestClient(app)

                response = client.get("/health")

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["status"] == "healthy"
                assert response_data["service"] == "slack-webhook-server"
                assert response_data["components"]["queue_backend"] == "healthy"
                assert response_data["components"]["slack_client"] == "not_initialized"

                # Verify that the backend publish was called with health check message
                assert len(mock_queue_backend.published_events) == 1

    def test_health_check_failure_queue_backend_error(self, mock_queue_backend):
        """Test health check returns 503 when queue backend fails."""
        # Create a mock backend that fails on publish
        failing_backend = MockMessageQueueBackend()
        failing_backend.publish = AsyncMock(side_effect=Exception("Connection failed"))

        # First create the app with a working queue backend
        with patch("slack_mcp.webhook.server.get_queue_backend", return_value=mock_queue_backend):
            with patch("slack_mcp.webhook.server.slack_client", None):
                app = create_slack_app()

        # Now patch to use the failing backend for health check
        with patch("slack_mcp.webhook.server.get_queue_backend", return_value=failing_backend):
            with patch(
                "slack_mcp.webhook.server.slack_client", None
            ):  # Ensure slack_client is None during health check
                client = TestClient(app)
                response = client.get("/health")

                assert response.status_code == 503
                response_data = response.json()
                assert response_data["status"] == "unhealthy"
                assert response_data["service"] == "slack-webhook-server"
                assert response_data["components"]["queue_backend"] == "unhealthy: Connection failed"
                assert response_data["components"]["slack_client"] == "not_initialized"

    def test_health_check_failure_get_queue_backend_error(self, mock_queue_backend):
        """Test health check when get_queue_backend itself raises an exception."""
        # First create the app with a working queue backend
        with patch("slack_mcp.webhook.server.get_queue_backend", return_value=mock_queue_backend):
            with patch("slack_mcp.webhook.server.slack_client", None):
                app = create_slack_app()

        # Now patch get_queue_backend to raise an exception (triggers outer exception handler)
        with patch("slack_mcp.webhook.server.get_queue_backend", side_effect=Exception("Backend service unavailable")):
            with patch("slack_mcp.webhook.server.slack_client", None):
                client = TestClient(app)
                response = client.get("/health")

                assert response.status_code == 503
                response_data = response.json()
                assert response_data["status"] == "unhealthy"
                assert response_data["service"] == "slack-webhook-server"
                assert response_data["error"] == "Backend service unavailable"

    def test_health_check_failure_str_conversion_error(self, mock_queue_backend):
        """Test health check when string conversion fails during error handling."""
        # First create the app with a working queue backend
        with patch("slack_mcp.webhook.server.get_queue_backend", return_value=mock_queue_backend):
            with patch("slack_mcp.webhook.server.slack_client", None):
                app = create_slack_app()

        # Create a backend that raises an exception with unprintable object
        class UnprintableError(Exception):
            def __str__(self):
                raise RuntimeError("Cannot convert error to string")

        failing_backend = MockMessageQueueBackend()
        failing_backend.publish = AsyncMock(side_effect=UnprintableError("Original error"))

        # This should trigger outer exception handler when trying to format the error message
        with patch("slack_mcp.webhook.server.get_queue_backend", return_value=failing_backend):
            with patch("slack_mcp.webhook.server.slack_client", None):
                client = TestClient(app)
                response = client.get("/health")

                assert response.status_code == 503
                response_data = response.json()
                assert response_data["status"] == "unhealthy"
                assert response_data["service"] == "slack-webhook-server"
                assert "Cannot convert error to string" in response_data["error"]
