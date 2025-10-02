"""End-to-end tests for the Slack bot event handling features."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from slack_sdk.web.async_client import AsyncWebClient

from slack_mcp.backends.base.protocol import QueueBackend
from slack_mcp.mcp.app import mcp_factory
from slack_mcp.webhook.app import web_factory
from slack_mcp.webhook.server import create_slack_app


class MockQueueBackend(QueueBackend):
    """Mock queue backend for testing."""

    def __init__(self):
        """Initialize the mock queue backend."""
        self.published_events = []
        self.mock_publish = AsyncMock()

    async def publish(self, topic, data):
        """Mock publish method."""
        self.published_events.append((topic, data))
        return await self.mock_publish(topic, data)

    async def consume(self, topic=None, group=None):
        """Mock consume method."""
        for _ in []:
            yield _


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
    with (
        patch("slack_mcp.webhook.server.AsyncWebClient") as mock_client_cls,
        patch("slack_mcp.webhook.server.verify_slack_request", AsyncMock(return_value=True)),
        patch.dict("os.environ", {"SLACK_BOT_TOKEN": "test_token", "SLACK_EVENTS_TOPIC": "slack_events"}),
    ):
        # Create a mock client
        mock_client = AsyncMock()
        mock_client.chat_postMessage.return_value = AsyncMock(data={"ok": True, "ts": "1234567890.123456"})
        mock_client_cls.return_value = mock_client

        # Reset factories for test isolation and create the FastAPI app
        web_factory.reset()
        mcp_factory.reset()
        mcp_factory.create()
        web_factory.create()
        app = create_slack_app()
        client = TestClient(app)

        # Create a mock queue backend and patch the real backend's publish method
        mock_backend = MockQueueBackend()

        # Get the real backend instance and patch its publish method to use our mock
        from slack_mcp.webhook.server import get_queue_backend

        backend = get_queue_backend()

        with patch.object(backend, "publish", mock_backend.publish):
            # Create an app_mention event
            event_data = {
                "type": "event_callback",
                "event": {
                    "type": "app_mention",
                    "user": "U12345678",
                    "text": "<@U87654321> Hello bot!",
                    "ts": "1234567890.123456",
                    "channel": "C12345678",
                },
                "team_id": "T12345",
                "api_app_id": "A12345",
                "event_id": "Ev12345",
                "event_time": 1234567890,
                "token": "test_token",
                "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
            }

            # Send the event to the endpoint
            response = client.post(
                "/slack/events",
                json=event_data,
                headers={"X-Slack-Signature": "valid_sig", "X-Slack-Request-Timestamp": "1234567890"},
            )

            # Verify the response
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

            # Verify event was published to the queue backend
            assert len(mock_backend.published_events) == 1
            topic, published_data = mock_backend.published_events[0]
            assert topic == "slack_events"
            assert published_data["event"]["type"] == "app_mention"
            assert published_data["event"]["text"] == "<@U87654321> Hello bot!"


def test_e2e_reaction_added():
    """Test the end-to-end flow for a reaction_added event."""
    with (
        patch("slack_mcp.webhook.server.AsyncWebClient") as mock_client_cls,
        patch("slack_mcp.webhook.server.verify_slack_request", AsyncMock(return_value=True)),
        patch.dict(
            "os.environ",
            {"SLACK_BOT_TOKEN": "test_token", "SLACK_BOT_ID": "B12345678", "SLACK_EVENTS_TOPIC": "slack_events"},
        ),
    ):
        # Create a mock client
        mock_client = AsyncMock()
        mock_client.chat_postMessage.return_value = AsyncMock(data={"ok": True, "ts": "1234567890.123457"})
        mock_client.conversations_history.return_value = AsyncMock(
            data={"ok": True, "messages": [{"text": "Hello", "bot_id": "B12345678", "ts": "1234567890.123456"}]}
        )
        mock_client_cls.return_value = mock_client

        # Reset factories for test isolation and create the FastAPI app
        web_factory.reset()
        mcp_factory.reset()
        mcp_factory.create()
        web_factory.create()
        app = create_slack_app()
        client = TestClient(app)

        # Create a mock queue backend and patch the real backend's publish method
        mock_backend = MockQueueBackend()

        # Get the real backend instance and patch its publish method to use our mock
        from slack_mcp.webhook.server import get_queue_backend

        backend = get_queue_backend()

        with patch.object(backend, "publish", mock_backend.publish):
            # Create a reaction_added event
            event_data = {
                "type": "event_callback",
                "event": {
                    "type": "reaction_added",
                    "user": "U12345678",
                    "reaction": "thumbsup",
                    "item": {"type": "message", "channel": "C12345678", "ts": "1234567890.123456"},
                },
                "team_id": "T12345",
                "api_app_id": "A12345",
                "event_id": "Ev12345",
                "event_time": 1234567890,
                "token": "test_token",
                "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
            }

            # Send the event to the endpoint
            response = client.post(
                "/slack/events",
                json=event_data,
                headers={"X-Slack-Signature": "valid_sig", "X-Slack-Request-Timestamp": "1234567890"},
            )

            # Verify the response
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

            # Verify event was published to the queue backend
            assert len(mock_backend.published_events) == 1
            topic, published_data = mock_backend.published_events[0]
            assert topic == "slack_events"
            assert published_data["event"]["type"] == "reaction_added"
            assert published_data["event"]["reaction"] == "thumbsup"
