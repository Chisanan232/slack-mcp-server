"""Unit tests for the integrated server functionality."""

from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slack_mcp.integrated_server import create_integrated_app


class _MockMCPServer:
    """Mock MCP server for testing."""

    def __init__(self) -> None:
        """Initialize the mock MCP server."""
        self.sse_app_calls: list[dict[str, Any]] = []
        self.streamable_http_app_calls: list[dict[str, Any]] = []
        self.mock_app = FastAPI()

    def sse_app(self, mount_path: str | None = None) -> FastAPI:
        """Mock the sse_app method."""
        self.sse_app_calls.append({"mount_path": mount_path})
        return self.mock_app

    def streamable_http_app(self) -> FastAPI:
        """Mock the streamable_http_app method."""
        self.streamable_http_app_calls.append({"called": True})
        return self.mock_app


class _MockWebhookApp(FastAPI):
    """Mock webhook FastAPI app for testing."""

    def __init__(self) -> None:
        """Initialize the mock webhook app."""
        super().__init__()
        self.mounted_apps: Dict[str, Any] = {}

    def mount(self, path: str, app: Any, *args: Any, **kwargs: Any) -> None:
        """Mock the mount method."""
        self.mounted_apps[path] = app
        # Call the real mount method with minimal parameters to avoid errors
        super().mount(path, app)


@pytest.fixture
def mock_dependencies(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """Set up mock dependencies for testing."""
    mock_mcp = _MockMCPServer()
    mock_webhook_app = _MockWebhookApp()

    # Mock the server imports
    monkeypatch.setattr("slack_mcp.integrated_server._server_instance", mock_mcp)
    monkeypatch.setattr("slack_mcp.integrated_server.create_slack_app", lambda: mock_webhook_app)
    monkeypatch.setattr("slack_mcp.integrated_server.initialize_slack_client", lambda token=None, retry=3: None)

    return {
        "mock_mcp": mock_mcp,
        "mock_webhook_app": mock_webhook_app,
    }


def test_create_integrated_app_sse(mock_dependencies: Dict[str, Any]) -> None:
    """Test creating an integrated app with SSE transport."""
    mock_mcp = mock_dependencies["mock_mcp"]
    mock_webhook_app = mock_dependencies["mock_webhook_app"]

    mount_path = "/mcp-test"
    app = create_integrated_app(token="test-token", mcp_transport="sse", mcp_mount_path=mount_path)

    # Verify the app instance is the mock webhook app
    assert app is mock_webhook_app

    # Verify sse_app was called with the correct mount path
    assert len(mock_mcp.sse_app_calls) == 1
    assert mock_mcp.sse_app_calls[0]["mount_path"] == mount_path

    # Verify the MCP app was mounted on the webhook app
    assert mount_path in mock_webhook_app.mounted_apps
    assert mock_webhook_app.mounted_apps[mount_path] is mock_mcp.mock_app


def test_create_integrated_app_streamable_http(mock_dependencies: Dict[str, Any]) -> None:
    """Test creating an integrated app with streamable-http transport."""
    mock_mcp = mock_dependencies["mock_mcp"]
    mock_webhook_app = mock_dependencies["mock_webhook_app"]

    # Add a test route to the MCP mock app to verify route merging
    @mock_mcp.mock_app.get("/mcp-test-route")
    def test_route() -> Dict[str, str]:
        return {"message": "test"}

    app = create_integrated_app(token="test-token", mcp_transport="streamable-http")

    # Verify the app instance is the mock webhook app
    assert app is mock_webhook_app

    # Verify streamable_http_app was called
    assert len(mock_mcp.streamable_http_app_calls) == 1

    # Verify no apps were mounted (routes should be added directly)
    assert len(mock_webhook_app.mounted_apps) == 0

    # Create a test client to verify routes were merged
    client = TestClient(app)
    response = client.get("/mcp-test-route")
    assert response.status_code == 200
    assert response.json() == {"message": "test"}


def test_create_integrated_app_with_invalid_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test creating an integrated app with an invalid transport."""
    # Mock create_slack_app to avoid token validation
    monkeypatch.setattr("slack_mcp.integrated_server.create_slack_app", lambda: FastAPI())
    monkeypatch.setattr("slack_mcp.integrated_server.initialize_slack_client", lambda token=None, retry=3: None)

    with pytest.raises(ValueError) as excinfo:
        create_integrated_app(token="test-token", mcp_transport="invalid-transport")

    assert "Invalid transport type" in str(excinfo.value)
    assert "Must be 'sse' or 'streamable-http'" in str(excinfo.value)


def test_create_integrated_app_default_mount_path(mock_dependencies: Dict[str, Any]) -> None:
    """Test creating an integrated app with default mount path."""
    mock_mcp = mock_dependencies["mock_mcp"]
    mock_webhook_app = mock_dependencies["mock_webhook_app"]

    # Test with None mount_path (should use default)
    app = create_integrated_app(token="test-token", mcp_transport="sse", mcp_mount_path=None)

    # Verify default mount path was used
    assert "/mcp" in mock_webhook_app.mounted_apps
    assert mock_webhook_app.mounted_apps["/mcp"] is mock_mcp.mock_app
