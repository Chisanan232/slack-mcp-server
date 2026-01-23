"""End-to-end tests for the integrated server functionality."""

from __future__ import annotations

import asyncio
import socket
import warnings
from contextlib import asynccontextmanager, suppress
from typing import Any, AsyncGenerator, Dict, Generator, Optional
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
import pytest_asyncio
import uvicorn
from abe.backends.message_queue.base.protocol import MessageQueueBackend
from abe.backends.message_queue.service.memory import MemoryBackend
from fastapi import Request
from fastapi.testclient import TestClient
from mcp.server import FastMCP

from slack_mcp.integrate.app import integrated_factory
from slack_mcp.mcp.app import MCPServerFactory


def find_free_port() -> int:
    """Find a free port to use for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


class UvicornTestServer(uvicorn.Server):
    """Test server that allows programmatic control for testing."""

    def __init__(self, config: uvicorn.Config) -> None:
        """Initialize the test server."""
        super().__init__(config)
        self.config = config
        self._started = False
        self._startup_done = asyncio.Event()

    async def startup(self, sockets: Optional[list[socket.socket]] = None) -> None:
        """Start the server and set the startup event."""
        await super().startup(sockets)
        self._startup_done.set()
        self._started = True

    async def start_and_wait(self) -> None:
        """Start the server and wait for it to be ready."""
        self._startup_done.clear()
        self._started = False
        await asyncio.gather(self.serve(), self._wait_for_startup())

    async def _wait_for_startup(self) -> None:
        """Wait for the server to start."""
        await self._startup_done.wait()

    async def safe_shutdown(self) -> None:
        """Safely shut down the server, handling any event loop issues."""
        if not self.started:
            return

        self.should_exit = True

        with suppress(asyncio.TimeoutError):
            # Give the server a brief moment to start shutting down
            await asyncio.sleep(0.2)


@pytest.fixture
def fake_slack_credentials() -> Generator[Dict[str, str], None, None]:
    """Provide fake Slack credentials for testing and restore the originals after."""
    # Store original env vars
    from slack_mcp.settings import get_settings, get_test_environment

    original_test_env = get_test_environment()
    settings = get_settings()
    original_token = (
        original_test_env.e2e_test_api_token.get_secret_value() if original_test_env.e2e_test_api_token and hasattr(original_test_env.e2e_test_api_token, 'get_secret_value') else original_test_env.e2e_test_api_token
    )
    original_secret = (
        settings.slack_signing_secret.get_secret_value() if settings.slack_signing_secret else None
    )

    # Set fake values for testing by creating a new settings instance
    fake_token = "xoxb-fake-token-for-testing"
    fake_secret = "fake-signing-secret"

    # Temporarily update settings for testing
    from slack_mcp.settings import get_settings, get_test_environment

    settings = get_settings(force_reload=True, slack_signing_secret=fake_secret)

    # Update test environment for E2E token
    test_env = get_test_environment(force_reload=True)
    test_env.e2e_test_api_token = fake_token

    yield {"token": fake_token, "secret": fake_secret}

    # Restore originals by forcing reload
    if original_secret:
        get_settings(force_reload=True, slack_signing_secret=original_secret)
    else:
        get_settings(force_reload=True)


@pytest.fixture(autouse=True)
def mock_slack_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the Slack request verification to always return True."""

    async def mock_verify(request: Request, signing_secret: str | None = None) -> bool:
        return True

    # Patch the internal verify_slack_request function directly
    monkeypatch.setattr("slack_mcp.webhook.server.verify_slack_request", mock_verify)


async def safely_cancel_task(task: asyncio.Task) -> None:
    """Safely cancel a task without raising exceptions."""
    if task.done():
        return

    try:
        task.cancel()
        with suppress(asyncio.CancelledError, RuntimeError, asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=0.5)
    except Exception as e:
        warnings.warn(f"Error while cancelling task: {e}")


class MockMessageQueueBackend(MessageQueueBackend):
    """Mock queue backend for testing."""

    def __init__(self) -> None:
        """Initialize the mock queue backend."""
        self.published_events: list[Dict[str, Any]] = []
        self.published_topics: list[str] = []
        self.event_received = asyncio.Event()

    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish a message to the mock backend."""
        self.published_topics.append(topic)
        self.published_events.append(message)
        self.event_received.set()

    async def consume(self, group: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Consume events from the mock backend."""
        for event in self.published_events:
            yield event

    @classmethod
    def from_env(cls) -> "MockMessageQueueBackend":
        """Mock implementation of from_env classmethod."""
        return cls()


@pytest_asyncio.fixture
async def real_queue_backend() -> AsyncGenerator[MemoryBackend, None]:
    """Use real MemoryBackend for queue testing instead of mocking."""
    # Reset MCP factory to prevent singleton conflicts
    MCPServerFactory.reset()

    # Reset the global _queue_backend to None to ensure fresh initialization
    import slack_mcp.webhook.server

    original_backend = slack_mcp.webhook.server._queue_backend
    slack_mcp.webhook.server._queue_backend = None

    try:
        # Let the system create the real MemoryBackend naturally
        # The first call to get_queue_backend() will initialize it
        from slack_mcp.webhook.server import get_queue_backend

        real_backend = get_queue_backend()

        # Ensure we have a MemoryBackend and clear any existing messages in the queue to ensure test isolation
        assert isinstance(real_backend, MemoryBackend), f"Expected MemoryBackend, got {type(real_backend)}"
        while not real_backend._queue.empty():
            try:
                real_backend._queue.get_nowait()
                real_backend._queue.task_done()
            except:
                break

        yield real_backend
    finally:
        # Restore the original backend after the test
        slack_mcp.webhook.server._queue_backend = original_backend


@pytest_asyncio.fixture
async def sse_server(
    fake_slack_credentials: Dict[str, str], real_queue_backend: Any
) -> AsyncGenerator[Dict[str, Any], None]:
    """Test SSE integrated server configuration without starting real server."""
    # Set environment variables for the test using settings
    import os

    os.environ["SLACK_EVENTS_TOPIC"] = "test_slack_events"
    from slack_mcp.settings import get_test_environment

    test_env = get_test_environment(force_reload=True)

    # Reset MCP factory before creating integrated app to prevent singleton conflicts
    MCPServerFactory.reset()

    # Mock the MCP factory to return a mock FastMCP instance
    mock_mcp_instance = MagicMock(spec=FastMCP)

    # Mock the SSE app
    mock_sse_app = MagicMock()
    mock_mcp_instance.sse_app.return_value = mock_sse_app

    # Mock the streamable HTTP app
    mock_streamable_app = MagicMock()
    mock_mcp_instance.streamable_http_app.return_value = mock_streamable_app

    with (
        patch("slack_mcp.mcp.app.MCPServerFactory.get", return_value=mock_mcp_instance),
        patch("slack_mcp.integrate.app.mcp_factory.get", return_value=mock_mcp_instance),
    ):
        # Create the integrated app to test configuration
        app = integrated_factory.create(
            token=fake_slack_credentials["token"], mcp_transport="sse", mcp_mount_path="/mcp"
        )

        # Verify the app was configured correctly
        assert app is not None
        assert mock_mcp_instance.sse_app.called
        mock_mcp_instance.sse_app.assert_called_with(mount_path=None)

        # Yield the configured app and mock components for testing
        yield {
            "app": app,
            "base_url": "http://127.0.0.1:8000",
            "queue_backend": real_queue_backend,
            "mock_mcp_instance": mock_mcp_instance,
        }


@pytest_asyncio.fixture
async def http_server(
    fake_slack_credentials: Dict[str, str], real_queue_backend: Any
) -> AsyncGenerator[Dict[str, Any], None]:
    """Test streamable-HTTP integrated server configuration without starting real server."""
    # Set environment variables for the test using settings
    import os

    os.environ["SLACK_EVENTS_TOPIC"] = "test_slack_events"
    from slack_mcp.settings import get_test_environment

    test_env = get_test_environment(force_reload=True)

    # Reset MCP factory before creating integrated app to prevent singleton conflicts
    MCPServerFactory.reset()

    # Mock the MCP factory to return a mock FastMCP instance
    mock_mcp_instance = MagicMock(spec=FastMCP)

    # Mock the SSE app
    mock_sse_app = MagicMock()
    mock_mcp_instance.sse_app.return_value = mock_sse_app

    # Mock the streamable HTTP app
    mock_streamable_app = MagicMock()
    mock_mcp_instance.streamable_http_app.return_value = mock_streamable_app

    with (
        patch("slack_mcp.mcp.app.MCPServerFactory.get", return_value=mock_mcp_instance),
        patch("slack_mcp.integrate.app.mcp_factory.get", return_value=mock_mcp_instance),
    ):
        # Create the integrated app to test configuration
        app = integrated_factory.create(token=fake_slack_credentials["token"], mcp_transport="streamable-http")

        # Verify the app was configured correctly
        assert app is not None
        assert mock_mcp_instance.streamable_http_app.called
        mock_mcp_instance.streamable_http_app.assert_called_with()

        # Yield the configured app and mock components for testing
        yield {
            "app": app,
            "base_url": "http://127.0.0.1:8001",
            "queue_backend": real_queue_backend,
            "mock_mcp_instance": mock_mcp_instance,
        }


def test_sse_integrated_server_webhook(sse_server: Dict[str, Any]) -> None:
    """Test that the webhook endpoints for the integrated server work with SSE transport."""
    app = sse_server["app"]

    # Use FastAPI TestClient for non-blocking HTTP testing
    # Patch lifespan to avoid session manager conflicts
    @asynccontextmanager
    async def no_op_lifespan(app):
        yield  # Simple no-op lifespan

    app.router.lifespan_context = no_op_lifespan
    with TestClient(app) as client:
        # Test the webhook endpoint
        challenge_data = {"token": "verification_token", "challenge": "challenge_value", "type": "url_verification"}

        # Add required Slack verification headers
        headers = {
            "X-Slack-Signature": "v0=fake_signature",
            "X-Slack-Request-Timestamp": "1234567890",
            "Content-Type": "application/json",
        }

        # Test the Slack webhook endpoint
        response = client.post("/slack/events", json=challenge_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data == {"challenge": "challenge_value"}


def test_sse_integrated_server_mount_point(sse_server: Dict[str, Any]) -> None:
    """Test that the MCP mount point is properly set up with SSE transport."""
    app = sse_server["app"]

    # Use FastAPI TestClient for non-blocking HTTP testing
    # Patch lifespan to avoid session manager conflicts
    @asynccontextmanager
    async def no_op_lifespan(app):
        yield  # Simple no-op lifespan

    app.router.lifespan_context = no_op_lifespan
    with TestClient(app) as client:
        # Test the MCP mount point (should redirect to /mcp/)
        response = client.get("/mcp", follow_redirects=False)
        # We should get a redirect (307) when hitting the mount point
        assert response.status_code == 307
        # The location header should include the server address
        assert response.headers.get("location").endswith("/mcp/")


def test_sse_docs_endpoint(sse_server: Dict[str, Any]) -> None:
    """Test that the API docs are available in the integrated server with SSE transport."""
    app = sse_server["app"]

    # Use FastAPI TestClient for non-blocking HTTP testing
    # Patch lifespan to avoid session manager conflicts
    @asynccontextmanager
    async def no_op_lifespan(app):
        yield  # Simple no-op lifespan

    app.router.lifespan_context = no_op_lifespan
    with TestClient(app) as client:
        # FastAPI automatically adds docs endpoints
        response = client.get("/docs")
        assert response.status_code == 200
        # Just check that it returns HTML content for the docs
        content = response.text
        assert "swagger-ui" in content.lower()


def test_slack_webhook_message_events(sse_server: Dict[str, Any]) -> None:
    """Test the Slack webhook endpoint with message events."""
    app = sse_server["app"]

    # Use FastAPI TestClient for non-blocking HTTP testing
    # Patch lifespan to avoid session manager conflicts
    @asynccontextmanager
    async def no_op_lifespan(app):
        yield  # Simple no-op lifespan

    app.router.lifespan_context = no_op_lifespan
    with TestClient(app) as client:
        # Create a Slack message event
        message_event = {
            "token": "verification_token",
            "team_id": "T12345",
            "api_app_id": "A12345",
            "event": {
                "type": "message",
                "channel": "C12345",
                "user": "U12345",
                "text": "Hello, world!",
                "ts": "1234567890.123456",
            },
            "type": "event_callback",
            "event_id": "Ev12345",
            "event_time": 1234567890,
        }

        # Add required Slack verification headers
        headers = {
            "X-Slack-Signature": "v0=fake_signature",
            "X-Slack-Request-Timestamp": "1234567890",
            "Content-Type": "application/json",
        }

        # Test the Slack webhook endpoint with a message event
        response = client.post("/slack/events", json=message_event, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok"}


def test_http_integrated_server_webhook(http_server: Dict[str, Any]) -> None:
    """Test that the webhook endpoints for the integrated server work with HTTP transport."""
    app = http_server["app"]

    # Use FastAPI TestClient for non-blocking HTTP testing
    # Patch lifespan to avoid session manager conflicts
    @asynccontextmanager
    async def no_op_lifespan(app):
        yield  # Simple no-op lifespan

    app.router.lifespan_context = no_op_lifespan
    with TestClient(app) as client:
        # Test the webhook endpoint
        challenge_data = {"token": "verification_token", "challenge": "challenge_value", "type": "url_verification"}

        # Add required Slack verification headers
        headers = {
            "X-Slack-Signature": "v0=fake_signature",
            "X-Slack-Request-Timestamp": "1234567890",
            "Content-Type": "application/json",
        }

        # Test the Slack webhook endpoint
        response = client.post("/slack/events", json=challenge_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data == {"challenge": "challenge_value"}


def test_http_docs_endpoint(http_server: Dict[str, Any]) -> None:
    """Test that the API docs are available in the integrated server with HTTP transport."""
    app = http_server["app"]

    # Use FastAPI TestClient for non-blocking HTTP testing
    # Patch lifespan to avoid session manager conflicts
    @asynccontextmanager
    async def no_op_lifespan(app):
        yield  # Simple no-op lifespan

    app.router.lifespan_context = no_op_lifespan
    with TestClient(app) as client:
        # FastAPI automatically adds docs endpoints
        response = client.get("/docs")
        assert response.status_code == 200
        # Just check that it returns HTML content for the docs
        content = response.text
        assert "swagger-ui" in content.lower()


@pytest.mark.asyncio
async def test_http_webhook_server(fake_slack_credentials: Dict[str, str]) -> None:
    """Test just the webhook functionality of the integrated server with HTTP transport."""
    port = find_free_port()

    # Create a simple Slack app without MCP integration to test webhook functionality
    from slack_mcp.webhook.server import create_slack_app, initialize_slack_client

    # Create the webhook app (WebServerFactory creates singleton on module load)
    app = create_slack_app()

    # Initialize the Slack client with the fake token
    initialize_slack_client(token=fake_slack_credentials["token"])

    # Configure and start the server
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = UvicornTestServer(config)

    # Start the server in a separate task
    task = asyncio.create_task(server.start_and_wait())

    # Give it a moment to start up
    await asyncio.sleep(0.5)

    base_url = f"http://127.0.0.1:{port}"

    try:
        async with aiohttp.ClientSession() as session:
            # Test the webhook endpoint
            challenge_data = {"token": "verification_token", "challenge": "challenge_value", "type": "url_verification"}

            # Add required Slack verification headers
            headers = {
                "X-Slack-Signature": "v0=fake_signature",
                "X-Slack-Request-Timestamp": "1234567890",
                "Content-Type": "application/json",
            }

            # Test the Slack webhook endpoint
            async with session.post(f"{base_url}/slack/events", json=challenge_data, headers=headers) as response:
                assert response.status == 200
                data = await response.json()
                assert data == {"challenge": "challenge_value"}
    finally:
        # Stop the server
        await server.safe_shutdown()
        await safely_cancel_task(task)


@pytest.mark.asyncio
async def test_sse_integrated_server_webhook_queue_publishing(sse_server: Dict[str, Any]) -> None:
    """Test that the webhook endpoints publish events to the queue backend."""
    app = sse_server["app"]
    real_queue_backend = sse_server["queue_backend"]

    # Use FastAPI TestClient for non-blocking HTTP testing
    # Note: SLACK_EVENTS_TOPIC is already set to "test_slack_events" in the sse_server fixture
    # Patch lifespan to avoid session manager conflicts
    @asynccontextmanager
    async def no_op_lifespan(app):
        yield  # Simple no-op lifespan

    app.router.lifespan_context = no_op_lifespan
    with TestClient(app) as client:
        # Create a Slack event payload
        event_data = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U12345",
                "text": "<@BOTID> Hello from e2e test",
                "channel": "C12345",
                "ts": "1234567890.123456",
            },
            "team_id": "T12345",
            "api_app_id": "A12345",
            "event_id": "Ev12345",
            "event_time": 1234567890,
            "token": "fake_token",
            "authorizations": [
                {
                    "enterprise_id": "E12345",
                    "team_id": "T12345",
                    "user_id": "U12345",
                    "is_bot": True,
                    "is_enterprise_install": False,
                }
            ],
        }

        # Add required Slack verification headers
        headers = {
            "X-Slack-Signature": "v0=fake_signature",
            "X-Slack-Request-Timestamp": "1234567890",
            "Content-Type": "application/json",
        }

        # Send the Slack event to the webhook endpoint
        response = client.post("/slack/events", json=event_data, headers=headers)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == {"status": "ok"}

        # Verify that the event was actually published to the real queue
        from abe.backends.message_queue.service.memory import MemoryBackend

        assert isinstance(real_queue_backend, MemoryBackend), f"Expected MemoryBackend, got {type(real_queue_backend)}"

        # Check that at least one message was published to the queue
        assert real_queue_backend._queue.qsize() >= 1, "No messages found in queue after publishing event"

        # Consume and verify the published event
        topic, published_event = await real_queue_backend._queue.get()
        assert topic == "test_slack_events", f"Expected topic 'test_slack_events', got '{topic}'"
        assert published_event["event"]["type"] == "app_mention"
        assert published_event["event"]["user"] == "U12345"
        assert published_event["event"]["text"] == "<@BOTID> Hello from e2e test"
        assert published_event["team_id"] == "T12345"
        assert published_event["event_id"] == "Ev12345"


@pytest.mark.asyncio
async def test_http_integrated_server_webhook_queue_publishing(http_server: Dict[str, Any]) -> None:
    """Test that the webhook endpoints publish events to the queue backend with HTTP transport."""
    app = http_server["app"]
    real_queue_backend = http_server["queue_backend"]

    # Use FastAPI TestClient for non-blocking HTTP testing
    # Note: SLACK_EVENTS_TOPIC is already set to "test_slack_events" in the http_server fixture
    # Patch lifespan to avoid session manager conflicts
    @asynccontextmanager
    async def no_op_lifespan(app):
        yield  # Simple no-op lifespan

    app.router.lifespan_context = no_op_lifespan
    with TestClient(app) as client:
        # Create a Slack event payload
        event_data = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": "U12345",
                "text": "Hello from e2e test",
                "channel": "C12345",
                "ts": "1234567890.123456",
            },
            "team_id": "T12345",
            "api_app_id": "A12345",
            "event_id": "Ev12345",
            "event_time": 1234567890,
            "token": "fake_token",
            "authorizations": [
                {
                    "enterprise_id": "E12345",
                    "team_id": "T12345",
                    "user_id": "U12345",
                    "is_bot": True,
                    "is_enterprise_install": False,
                }
            ],
        }

        # Add required Slack verification headers
        headers = {
            "X-Slack-Signature": "v0=fake_signature",
            "X-Slack-Request-Timestamp": "1234567890",
            "Content-Type": "application/json",
        }

        # Send the Slack event to the webhook endpoint
        response = client.post("/slack/events", json=event_data, headers=headers)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == {"status": "ok"}

        # Verify that the event was actually published to the real queue
        from abe.backends.message_queue.service.memory import MemoryBackend

        assert isinstance(real_queue_backend, MemoryBackend), f"Expected MemoryBackend, got {type(real_queue_backend)}"

        # Check that at least one message was published to the queue
        assert real_queue_backend._queue.qsize() >= 1, "No messages found in queue after publishing event"

        # Consume and verify the published event
        topic, published_event = await real_queue_backend._queue.get()
        assert topic == "test_slack_events", f"Expected topic 'test_slack_events', got '{topic}'"
        assert published_event["event"]["type"] == "message"
        assert published_event["event"]["user"] == "U12345"
        assert published_event["event"]["text"] == "Hello from e2e test"
        assert published_event["team_id"] == "T12345"
        assert published_event["event_id"] == "Ev12345"
