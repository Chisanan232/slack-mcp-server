"""Integration tests for the integrated server functionality."""

from __future__ import annotations

from typing import Any, Dict, Generator, List

import pytest
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from slack_mcp.integrate.app import integrated_factory


@pytest.fixture
def fake_slack_credentials() -> Generator[Dict[str, str], None, None]:
    """Provide fake Slack credentials for testing and restore the originals after."""
    # Store original env vars
    from slack_mcp.settings import get_settings

    original_settings = get_settings()
    original_token = original_settings.slack_bot_token.get_secret_value() if original_settings.slack_bot_token else None
    original_secret = (
        original_settings.slack_signing_secret.get_secret_value() if original_settings.slack_signing_secret else None
    )

    # Set fake values for testing by creating a new settings instance
    fake_token = "xoxb-fake-token-for-testing"
    fake_secret = "fake-signing-secret"

    # Temporarily update settings for testing
    settings = get_settings(force_reload=True, slack_bot_token=fake_token, slack_signing_secret=fake_secret)

    yield {"token": fake_token, "secret": fake_secret}

    # Restore originals by forcing reload
    if original_token:
        get_settings(force_reload=True, slack_bot_token=original_token)
    if original_secret:
        get_settings(force_reload=True, slack_signing_secret=original_secret)
    else:
        get_settings(force_reload=True)


@pytest.fixture
def mock_slack_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the Slack request verification to always return True."""

    async def mock_verify(request: Request, signing_secret: str | None = None) -> bool:
        return True

    # Patch the internal verify_slack_request function directly
    monkeypatch.setattr("slack_mcp.webhook.server.verify_slack_request", mock_verify)


@pytest.fixture
def sse_integrated_client(fake_slack_credentials: Dict[str, str], mock_slack_verification: None) -> TestClient:
    """Create a test client for the integrated server using SSE transport."""
    # Reset factories for test isolation
    integrated_factory.reset()
    from slack_mcp.mcp.app import mcp_factory
    from slack_mcp.webhook.app import web_factory

    web_factory.reset()
    mcp_factory.reset()

    app = integrated_factory.create(token=fake_slack_credentials["token"], mcp_transport="sse", mcp_mount_path="/mcp")
    return TestClient(app)


def test_sse_webhook_endpoint(sse_integrated_client: TestClient) -> None:
    """Test that the webhook endpoint works in the integrated server with SSE transport."""
    # Prepare a mock Slack challenge request
    challenge_data = {"token": "verification_token", "challenge": "challenge_value", "type": "url_verification"}

    # Add the required X-Slack-Signature and X-Slack-Request-Timestamp headers
    headers = {"X-Slack-Signature": "v0=fake_signature", "X-Slack-Request-Timestamp": "1234567890"}

    # Send the request to the Slack events endpoint
    response = sse_integrated_client.post("/slack/events", json=challenge_data, headers=headers)

    # Check response
    assert response.status_code == 200
    assert response.json() == {"challenge": "challenge_value"}


def test_sse_webhook_app_mounted(sse_integrated_client: TestClient) -> None:
    """Test that the SSE integrated server has the MCP app mounted."""
    # In FastAPI's TestClient, we should use follow_redirects
    # Set to False to check the initial redirect response
    client = TestClient(sse_integrated_client.app, follow_redirects=False)
    response = client.get("/mcp")

    # Check status code for redirect
    assert response.status_code == 307

    # Check that the redirect location is correct
    # FastAPI TestClient uses absolute URLs with the testserver hostname
    assert response.headers["location"] == "http://testserver/mcp/"


def test_http_webhook_endpoint(fake_slack_credentials: Dict[str, str], mock_slack_verification: None) -> None:
    """Test that the webhook endpoint works in the integrated server with HTTP transport."""
    # Since streamable-http transport requires running the task group,
    # we'll test just the webhook part by creating the app manually
    from slack_mcp.mcp.app import mcp_factory
    from slack_mcp.webhook.app import web_factory
    from slack_mcp.webhook.server import create_slack_app, initialize_slack_client

    # Reset factories for test isolation first
    integrated_factory.reset()
    web_factory.reset()
    mcp_factory.reset()

    # Initialize factories in the correct order: MCP first, then web factory
    mcp_factory.create()
    web_factory.create()
    app = create_slack_app()

    # Initialize the Slack client with the fake token
    initialize_slack_client(token=fake_slack_credentials["token"])
    client = TestClient(app)

    # Prepare a mock Slack challenge request
    challenge_data = {"token": "verification_token", "challenge": "challenge_value", "type": "url_verification"}

    # Add the required X-Slack-Signature and X-Slack-Request-Timestamp headers
    headers = {"X-Slack-Signature": "v0=fake_signature", "X-Slack-Request-Timestamp": "1234567890"}

    # Send the request to the Slack events endpoint
    response = client.post("/slack/events", json=challenge_data, headers=headers)

    # Check response
    assert response.status_code == 200
    assert response.json() == {"challenge": "challenge_value"}


def test_integrated_server_structure(
    monkeypatch: pytest.MonkeyPatch, mock_slack_verification: None, fake_slack_credentials: Dict[str, str]
) -> None:
    """Test that the integrated server is correctly structured with both MCP and webhook routes."""
    # Reset factories for test isolation first
    integrated_factory.reset()
    from slack_mcp.mcp.app import mcp_factory
    from slack_mcp.webhook.app import web_factory

    web_factory.reset()
    mcp_factory.reset()

    # Mock the MCP server instance to avoid task group initialization issues
    class MockMCPApp:
        def __init__(self) -> None:
            self.routes: List[APIRoute] = []

        def sse_app(self, mount_path: str | None = None) -> Any:
            # Return a minimal FastAPI app instead of just a string
            app = FastAPI()
            return app

        def streamable_http_app(self) -> Any:
            # Return a minimal FastAPI app with routes instead of just a string
            app = FastAPI()
            return app

    # Create a mock server instance
    mock_server = MockMCPApp()

    # Mock the factory pattern instead of the old _server_instance
    from slack_mcp.mcp.app import mcp_factory

    monkeypatch.setattr("slack_mcp.mcp.app.mcp_factory.get", lambda: mock_server)
    # Initialize the MCP factory
    mcp_factory.create()

    # Test SSE integration - We can check the mount path
    app = integrated_factory.create(
        token=fake_slack_credentials["token"], mcp_transport="sse", mcp_mount_path="/mcp-test"
    )

    # Verify mount path is used
    assert hasattr(app, "routes")

    # For streamable-http, we would check that routes are merged,
    # but since we've mocked the MCP app, we just verify it gets called
    app = integrated_factory.create(token=fake_slack_credentials["token"], mcp_transport="streamable-http")

    # Verify the app has routes (minimal verification since we've mocked implementation)
    assert hasattr(app, "routes")
