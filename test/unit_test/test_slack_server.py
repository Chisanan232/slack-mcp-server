"""Unit tests for the Slack server module."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from slack_mcp.server import FastMCP
from slack_mcp.slack_server import (
    register_mcp_tools,
    run_slack_server,
)


@pytest.fixture
def mock_mcp():
    """Create a mock FastMCP instance."""
    mcp = MagicMock(spec=FastMCP)
    return mcp


@pytest.fixture
def mock_flask_app():
    """Create a mock Flask app."""
    app = MagicMock()
    return app


def test_register_mcp_tools(mock_mcp):
    """Test registering MCP tools."""
    # Call the function
    register_mcp_tools(mock_mcp)

    # Verify tool and prompt registrations
    assert mock_mcp.tool.call_count == 1
    assert mock_mcp.prompt.call_count == 1

    # Check that the tool decorator was called with the expected name
    mock_mcp.tool.assert_any_call("slack_listen_events")

    # Check that the prompt decorator was called with the expected name
    mock_mcp.prompt.assert_any_call("slack_listen_events_usage")


@pytest.mark.asyncio
async def test_run_slack_server():
    """Test running the Slack server."""
    with (
        patch("slack_mcp.slack_server.create_slack_app") as mock_create_app,
        patch("uvicorn.Server") as mock_server_cls,
        patch("uvicorn.Config") as mock_config_cls,
    ):
        # Setup mocks
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        mock_config = MagicMock()
        mock_config_cls.return_value = mock_config
        
        # Mock the Server instance
        mock_server = MagicMock()
        mock_server_cls.return_value = mock_server
        
        # Mock the serve method to return a completed future
        serve_future = asyncio.Future()
        serve_future.set_result(None)
        mock_server.serve.return_value = serve_future

        # Call the function with test parameters
        await run_slack_server(host="localhost", port=8000, token="test_token")

        # Verify the app was created with the right token
        mock_create_app.assert_called_once_with("test_token")

        # Verify the config was set correctly
        mock_config_cls.assert_called_once_with(app=mock_app, host="localhost", port=8000)
        
        # Verify the server was properly configured and started
        mock_server_cls.assert_called_once_with(mock_config)
        mock_server.serve.assert_called_once()
